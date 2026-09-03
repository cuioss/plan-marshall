#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Wire protocol and job/result schema for the marshalld build server.

This module is the ONE contract shared by the ``marshalld`` daemon and the
``build-server-client`` skill: the daemon and the client never re-declare the
frame format or the result shape, they both import from here. It is a pure
deterministic helper library that extends the ``script-shared`` build library
exactly as :mod:`_build_result` / :mod:`_build_queue_slot` do — no
LLM-in-the-loop behaviour, no I/O beyond the socket read/write helpers.

Three concerns live here:

* **Frame codec** — a length-prefixed JSON framing (a 4-byte big-endian
  unsigned length prefix followed by a UTF-8 JSON object). Length-prefixing
  avoids the delimiter-in-payload ambiguity a newline-delimited framing hits on
  multi-line error messages, so nested/multi-line payloads round-trip
  losslessly. Both an :mod:`asyncio` ``StreamReader``/``StreamWriter`` pair (the
  daemon's server side) and a blocking :class:`socket.socket` (the client's
  synchronous submit/wait/ping calls over a short-lived connection) are
  supported by parallel read/write helpers over the SAME on-wire bytes.
* **Job spec** — :class:`JobSpec`, the submit struct (command, exec_path,
  project_path, plan_id, fingerprint). :func:`compute_fingerprint` derives the
  idempotent-submit fingerprint (plan_id + command + tree) the scheduler uses to
  attach an identical concurrent submit to one in-flight job.
* **Status schema** — helpers that map to and from the shared
  :mod:`_build_result` result shape (``errors[N]{file,line,message,category}``,
  ``log_file``, ``duration_seconds``) so a terminal result crosses the wire in
  the daemon's status vocabulary (``success|failure|timeout|killed``) without
  either side re-implementing the result contract. The wire vocabulary is
  four-valued while ``_build_result``'s is five-valued, so the forward
  translation is total but not injective — see
  :data:`_RESULT_STATUS_TO_WIRE`.

Usage:
    from _build_server_protocol import (
        JobSpec, compute_fingerprint, make_job_spec,
        encode_frame, read_frame, write_frame, recv_frame, send_frame,
        status_from_result, normalize_errors,
        LogVerdict, read_log_verdict,
        FrameError, FrameTooLargeError, FrameTruncatedError, FrameDecodeError,
        PROTOCOL_VERSION, MARSHALLD_JOB_ENV,
        STATUS_RUNNING, STATUS_SUCCESS, STATUS_FAILURE, STATUS_TIMEOUT,
        STATUS_KILLED, STATUS_NOT_FOUND, STATUS_REFUSED, STATUS_QUEUED,
        TERMINAL_STATUSES,
    )
"""

from __future__ import annotations

import argparse
import asyncio
import json
import socket
import struct
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

import _build_result

# =============================================================================
# Framing constants
# =============================================================================

PROTOCOL_VERSION = '1'
"""The wire/identity version shared by the daemon and the client.

The daemon reports this string in its ``ping`` response (``marshalld.VERSION``);
the client's S3 identity handshake compares the reported version against this
constant and treats a mismatch as an untrusted peer (fallback), never trusting a
response from a daemon speaking a different protocol version.
"""

MARSHALLD_JOB_ENV = 'MARSHALLD_JOB'
"""Re-entrancy marker set on a marshalld build child's environment.

The build-execute routing seam (D5, ``_build_execute_factory``) routes a build
to marshalld by RE-SUBMITTING the same executor-form command; the daemon's
supervisor then spawns ``python3 {tree}/.plan/execute-script.py {notation} …`` —
which runs the build wrapper's ``cmd_run`` AGAIN inside the daemon child. Without
a guard that second ``cmd_run`` would preflight-``ready`` and route back to the
daemon, recursing without bound. The supervisor stamps this variable on the
child's clean baseline env (:mod:`_marshalld_supervisor`), and the routing seam
skips routing whenever it is present — so a build already running inside a
marshalld job always runs in-process. The value is unspecified beyond
truthiness; ``'1'`` is used.
"""

LENGTH_PREFIX_BYTES = 4
"""Width of the frame length prefix in bytes (4-byte big-endian unsigned)."""

_LENGTH_STRUCT = struct.Struct('>I')
"""Big-endian unsigned 32-bit packer for the length prefix (max 4 GiB)."""

MAX_FRAME_BYTES = 16 * 1024 * 1024
"""Hard cap on a single frame's JSON body (16 MiB).

A declared length above this is rejected BEFORE the body is read, so a
malformed or hostile length prefix cannot force an unbounded allocation or an
unbounded read. Build results — even with large captured error lists — stay
comfortably under this bound; the daemon truncates oversized captures upstream.
"""


# =============================================================================
# Status vocabulary (wire schema)
# =============================================================================
# The daemon's terminal classification is success|failure|timeout|killed — note
# ``failure`` (not ``error``): the ``killed`` state is its own terminal status
# rendered "externally killed — not flaky, do not blind-retry", never folded
# into ``failure``. Non-terminal and control statuses complete the vocabulary.

STATUS_QUEUED = 'queued'
"""Job accepted, waiting for a scheduler slot (not yet running)."""

STATUS_RUNNING = 'running'
"""Job's child process is executing; a bound-expiry wait returns this."""

STATUS_SUCCESS = 'success'
"""Terminal: child exited 0."""

STATUS_FAILURE = 'failure'
"""Terminal: child exited non-zero (maps from _build_result ``error``)."""

STATUS_TIMEOUT = 'timeout'
"""Terminal: child exceeded its timeout and was terminated."""

STATUS_KILLED = 'killed'
"""Terminal: child died externally (harness reap / daemon restart).

Its own state — "externally killed — not flaky, do not blind-retry" — never
folded into ``failure``.
"""

STATUS_NOT_FOUND = 'not_found'
"""No job for the requested id (unknown, or its result expired the journal)."""

STATUS_REFUSED = 'refused'
"""Submit rejected by the verifier (S1/S2); carries a ``reason``."""

TERMINAL_STATUSES = frozenset(
    {STATUS_SUCCESS, STATUS_FAILURE, STATUS_TIMEOUT, STATUS_KILLED}
)
"""The four terminal job statuses — a wait resolves once one of these is seen."""

_RESULT_STATUSES: frozenset[str] = frozenset(
    value
    for name, value in vars(_build_result).items()
    if name.startswith('STATUS_') and isinstance(value, str)
)
"""Every ``_build_result`` status value, DERIVED from that module's namespace.

Derived rather than restated so the totality guard in
:func:`wire_status_from_result` cannot be checking a stale copy of the
vocabulary. A hand-maintained list here would go quietly out of date the moment a
sixth ``STATUS_*`` is added to :mod:`_build_result` — which is precisely the
event the guard exists to catch, so the guard would fail exactly when it was
needed. ``_build_result`` imports no ``STATUS_``-prefixed name from anywhere
else, so this scan sees its own constants and nothing borrowed.
"""

# Map the shared _build_result status vocabulary
# (success|error|timeout|killed|indeterminate) to the wire vocabulary
# (success|failure|timeout|killed).
#
# The table is TOTAL over :data:`_RESULT_STATUSES` — every result status has a
# row, and :func:`wire_status_from_result` raises rather than passing through if
# one ever does not. It is not total by accident: ``indeterminate`` previously had
# no row and fell through the pass-through fallback, so the daemon published the
# literal string ``indeterminate`` — a value absent from
# :data:`TERMINAL_STATUSES` — and a waiting client re-polled forever.
#
# ``killed`` is listed EXPLICITLY rather than left to that fallback. The two
# spellings coincide, so the fallback produced the right answer — but only by
# accident of naming, and a table that silently omits a status it must translate
# is one rename away from mapping a kill onto nothing.
#
# ``indeterminate`` maps onto ``failure``, and that is a deliberate
# TERMINALITY-OVER-FIDELITY trade rather than the folding :mod:`_build_result`
# forbids. The wire vocabulary is four-valued and adding a fifth wire status is
# explicitly not taken here, so the only alternative to a terminal row is the
# non-terminal string that hung the client. A waiting client must be able to
# stop; what it loses is the distinction between "ran and failed" and "could not
# be established", which the log the result points at still carries. The
# direction is one-way: see :data:`_WIRE_STATUS_TO_RESULT`.
_RESULT_STATUS_TO_WIRE = {
    _build_result.STATUS_SUCCESS: STATUS_SUCCESS,
    _build_result.STATUS_ERROR: STATUS_FAILURE,
    _build_result.STATUS_TIMEOUT: STATUS_TIMEOUT,
    _build_result.STATUS_KILLED: STATUS_KILLED,
    _build_result.STATUS_INDETERMINATE: STATUS_FAILURE,
}

# The inverse is an EXPLICIT table, NOT an inversion of the one above. Two result
# statuses now map onto ``failure``, so a dict comprehension over
# ``_RESULT_STATUS_TO_WIRE.items()`` would silently rebind ``failure`` to
# whichever row came last — making ``result_status_from_wire('failure')`` return
# ``indeterminate`` instead of ``error``, a break with no error and no test
# touching the forward direction. Stating the four wire rows here makes the
# forward table's non-injectivity harmless.
_WIRE_STATUS_TO_RESULT = {
    STATUS_SUCCESS: _build_result.STATUS_SUCCESS,
    STATUS_FAILURE: _build_result.STATUS_ERROR,
    STATUS_TIMEOUT: _build_result.STATUS_TIMEOUT,
    STATUS_KILLED: _build_result.STATUS_KILLED,
}

ERROR_FIELDS = ('file', 'line', 'message', 'category')
"""Canonical field order for a single ``errors[]`` entry on the wire."""


# =============================================================================
# Frame errors
# =============================================================================


class FrameError(Exception):
    """Base class for every framing / decoding failure raised by this module."""


class FrameTooLargeError(FrameError):
    """A frame's declared or encoded body exceeds :data:`MAX_FRAME_BYTES`.

    Raised on encode when the JSON body is too large to send, and on decode
    when the declared length prefix exceeds the cap — in the decode case BEFORE
    the oversized body is read, so no unbounded allocation occurs.
    """

    def __init__(self, declared_bytes: int, limit_bytes: int) -> None:
        self.declared_bytes = declared_bytes
        self.limit_bytes = limit_bytes
        super().__init__(
            f'frame body of {declared_bytes} bytes exceeds the '
            f'{limit_bytes}-byte limit'
        )


class FrameTruncatedError(FrameError):
    """The connection ended before a full frame (prefix or body) was read.

    Signals a truncated frame — the peer closed the socket mid-frame or a
    partial write was flushed. The caller treats the connection as unusable.
    """


class FrameDecodeError(FrameError):
    """A fully-read frame body was not a UTF-8 JSON object.

    Raised when the body is not valid UTF-8, not valid JSON, or valid JSON that
    is not a top-level object (the frame payload contract is a JSON object).
    """


# =============================================================================
# Frame codec — shared byte layout
# =============================================================================


def encode_frame(payload: dict[str, Any]) -> bytes:
    """Encode a payload dict into a length-prefixed JSON frame.

    Args:
        payload: The JSON-serialisable object to frame.

    Returns:
        The 4-byte big-endian length prefix followed by the UTF-8 JSON body.

    Raises:
        FrameTooLargeError: when the encoded body exceeds
            :data:`MAX_FRAME_BYTES`.
        TypeError: when ``payload`` is not JSON-serialisable.
    """
    body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    if len(body) > MAX_FRAME_BYTES:
        raise FrameTooLargeError(len(body), MAX_FRAME_BYTES)
    return _LENGTH_STRUCT.pack(len(body)) + body


def decode_payload(body: bytes) -> dict[str, Any]:
    """Decode a frame body (the bytes AFTER the length prefix) into a dict.

    Args:
        body: The raw UTF-8 JSON body bytes.

    Returns:
        The decoded payload object.

    Raises:
        FrameDecodeError: when the body is not UTF-8, not JSON, or not a
            top-level JSON object.
    """
    try:
        obj = json.loads(body.decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FrameDecodeError(f'frame body is not UTF-8 JSON: {exc}') from exc
    if not isinstance(obj, dict):
        raise FrameDecodeError(
            f'frame payload must be a JSON object, got {type(obj).__name__}'
        )
    return obj


def _decode_length(header: bytes) -> int:
    """Unpack and bounds-check a 4-byte length prefix.

    Raises:
        FrameTooLargeError: when the declared length exceeds the cap.
    """
    length = int(_LENGTH_STRUCT.unpack(header)[0])
    if length > MAX_FRAME_BYTES:
        raise FrameTooLargeError(length, MAX_FRAME_BYTES)
    return length


# =============================================================================
# Frame codec — asyncio StreamReader / StreamWriter (daemon server side)
# =============================================================================


async def read_frame(reader: asyncio.StreamReader) -> dict[str, Any]:
    """Read one length-prefixed JSON frame from an asyncio stream.

    Args:
        reader: The stream to read the next frame from.

    Returns:
        The decoded payload object.

    Raises:
        FrameTruncatedError: when EOF is reached before a full prefix or body.
        FrameTooLargeError: when the declared length exceeds the cap.
        FrameDecodeError: when the body is not a UTF-8 JSON object.
    """
    try:
        header = await reader.readexactly(LENGTH_PREFIX_BYTES)
    except asyncio.IncompleteReadError as exc:
        raise FrameTruncatedError(
            f'stream closed before length prefix (read {len(exc.partial)} of '
            f'{LENGTH_PREFIX_BYTES} bytes)'
        ) from exc
    length = _decode_length(header)
    try:
        body = await reader.readexactly(length)
    except asyncio.IncompleteReadError as exc:
        raise FrameTruncatedError(
            f'stream closed before frame body (read {len(exc.partial)} of '
            f'{length} bytes)'
        ) from exc
    return decode_payload(body)


async def write_frame(writer: asyncio.StreamWriter, payload: dict[str, Any]) -> None:
    """Encode and write one frame to an asyncio stream, then drain.

    Args:
        writer: The stream to write the frame to.
        payload: The JSON-serialisable object to frame.

    Raises:
        FrameTooLargeError: when the encoded body exceeds the cap.
    """
    writer.write(encode_frame(payload))
    await writer.drain()


# =============================================================================
# Frame codec — blocking socket (client synchronous calls)
# =============================================================================


def _recv_exactly(sock: socket.socket, count: int) -> bytes:
    """Read exactly ``count`` bytes from a blocking socket.

    Args:
        sock: The connected blocking socket.
        count: The exact number of bytes to read.

    Returns:
        Exactly ``count`` bytes.

    Raises:
        FrameTruncatedError: when the peer closes before ``count`` bytes arrive.
    """
    chunks: list[bytes] = []
    remaining = count
    while remaining > 0:
        chunk = sock.recv(remaining)
        if not chunk:
            raise FrameTruncatedError(
                f'socket closed before frame complete (read '
                f'{count - remaining} of {count} bytes)'
            )
        chunks.append(chunk)
        remaining -= len(chunk)
    return b''.join(chunks)


def recv_frame(sock: socket.socket) -> dict[str, Any]:
    """Read one length-prefixed JSON frame from a blocking socket.

    Args:
        sock: The connected blocking socket.

    Returns:
        The decoded payload object.

    Raises:
        FrameTruncatedError: when the peer closes before a full frame.
        FrameTooLargeError: when the declared length exceeds the cap.
        FrameDecodeError: when the body is not a UTF-8 JSON object.
    """
    header = _recv_exactly(sock, LENGTH_PREFIX_BYTES)
    length = _decode_length(header)
    body = _recv_exactly(sock, length)
    return decode_payload(body)


def send_frame(sock: socket.socket, payload: dict[str, Any]) -> None:
    """Encode and send one frame over a blocking socket.

    Args:
        sock: The connected blocking socket.
        payload: The JSON-serialisable object to frame.

    Raises:
        FrameTooLargeError: when the encoded body exceeds the cap.
    """
    sock.sendall(encode_frame(payload))


# =============================================================================
# Job spec
# =============================================================================

_JOB_SPEC_REQUIRED = ('command', 'exec_path', 'project_path', 'plan_id')
"""Fields a wire job spec MUST carry. ``timeout`` is deliberately NOT here — it
is optional, so a client that never sets it (and an older client that does not
know the field) still submits a valid spec."""


_ABSENT = object()
"""Sentinel distinguishing "the wire payload has no ``timeout`` key" from a key
that is present and carries ``null``. ``dict.get``'s default cannot be ``None``
here without collapsing the two, which is exactly the case
:func:`_coerce_wire_timeout` must tell apart."""


def positive_timeout_seconds(raw: str) -> int:
    """argparse ``type`` for a ``--timeout`` value: a strictly positive integer.

    Shared deliberately by BOTH ``--timeout`` parsers — the build wrapper's
    ``run`` and the build-server client's ``submit`` — so the two cannot drift
    into accepting different value sets. A bare ``type=int`` admits ``0`` and
    negatives at both, and neither is meaningful under either reading of the
    bound. The two paths fail differently and both badly: on the wire the daemon
    refuses a non-positive value as ``invalid_job`` (see
    :func:`_coerce_wire_timeout`), while on the in-process path the value is
    clamped to the engine's minimum and can silently REPLACE a larger learned
    timeout. Rejecting at the parser turns both into one argparse error the
    caller reads before anything runs.

    This validates the value's SHAPE only. It says nothing about how the bound is
    applied: a request can only RAISE the daemon's supervisory bound (see
    ``marshalld._resolve_job_timeout``), and that is deliberate.

    Args:
        raw: The raw command-line token.

    Returns:
        The parsed positive integer.

    Raises:
        argparse.ArgumentTypeError: when the token is not an integer, or is not
            strictly positive.
    """
    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise argparse.ArgumentTypeError(
            f'--timeout must be an integer number of seconds, got {raw!r}'
        ) from None
    if value <= 0:
        raise argparse.ArgumentTypeError(
            f'--timeout must be a positive number of seconds, got {value}'
        )
    return value


def _coerce_wire_timeout(raw: Any) -> int | None:
    """Coerce the optional wire ``timeout`` to a positive int, or ``None``.

    ABSENCE is signalled by the :data:`_ABSENT` sentinel — never by ``None``.
    That distinction is the whole point of the sentinel: a frame carrying
    ``"timeout": null`` decodes to the same ``None`` an omitted key yields, so a
    function that read absence off the VALUE would apply the daemon default to a
    spec that explicitly named a null bound. That is the silent degrade this
    field exists to prevent, arriving by a different route — so a PRESENT
    ``null`` is refused as malformed rather than quietly treated as unset.

    A present value is validated rather than best-effort coerced: the daemon
    feeds it straight into the supervisor's wall-clock bound, so a string, a
    float, a bool, ``null``, or a non-positive number is a malformed spec and the
    submit is refused with ``invalid_job``.

    ``to_dict`` omits the key entirely when the bound is unset, so our own client
    never emits a present ``null``; this guards a hand-crafted or third-party
    frame.

    Args:
        raw: The decoded ``timeout`` value, or :data:`_ABSENT` when the key is
            not in the payload at all.

    Returns:
        The positive integer bound in seconds, or ``None`` when absent.

    Raises:
        ValueError: when the key is present but not a positive integer.
    """
    if raw is _ABSENT:
        return None
    # bool is an int subclass — `True` would otherwise coerce to a 1-second bound.
    if raw is None or isinstance(raw, bool) or not isinstance(raw, int) or raw <= 0:
        raise ValueError(f'job spec timeout must be a positive integer, got {raw!r}')
    return raw


@dataclass
class JobSpec:
    """A build-job submission struct shared by the client and the daemon.

    Attributes:
        command: The exact executor-form argv tokens to run (e.g.
            ``['python3', '{tree}/.plan/execute-script.py', '{notation}', ...]``).
            Carried as a list so the verifier can check it positionally.
        exec_path: The submitted tree root the executor lives under —
            ``{exec_path}/.plan/execute-script.py`` is ``command[1]``.
        project_path: The project working directory the build runs in.
        plan_id: The submitting plan id — the ``NO_PLAN`` sentinel for a
            plan-less build (the client resolves it before constructing the
            spec, so the wire value is never the empty string).
        fingerprint: The idempotent-submit fingerprint; empty until derived via
            :func:`compute_fingerprint` (see :func:`make_job_spec`).
        timeout: The client's EXPLICIT wall-clock bound (seconds) for this job,
            or ``None`` when the submit stated none. Optional by construction —
            the daemon falls back to its own default when it is absent — because
            an explicit ``--timeout`` that cannot cross the socket is an
            override the routed leg silently drops.
    """

    command: list[str]
    exec_path: str
    project_path: str
    plan_id: str
    fingerprint: str = ''
    timeout: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return the JSON-serialisable wire form of this job spec.

        ``timeout`` is emitted only when the submit carried one, so a spec that
        stated no bound has the exact wire shape it always had.
        """
        payload: dict[str, Any] = {
            'command': list(self.command),
            'exec_path': self.exec_path,
            'project_path': self.project_path,
            'plan_id': self.plan_id,
            'fingerprint': self.fingerprint,
        }
        if self.timeout is not None:
            payload['timeout'] = self.timeout
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> JobSpec:
        """Build a :class:`JobSpec` from a decoded wire dict.

        Args:
            data: A decoded frame payload carrying the job-spec fields.

        Returns:
            The reconstructed job spec.

        Raises:
            ValueError: when a required field is missing, ``command`` is not a
                list of strings, or a PRESENT ``timeout`` is not a positive
                integer — ``"timeout": null`` is present, and is refused. An
                ABSENT ``timeout`` is valid and reads as ``None``.
        """
        missing = [key for key in _JOB_SPEC_REQUIRED if key not in data]
        if missing:
            raise ValueError(
                f'job spec is missing required field(s): {", ".join(missing)}'
            )
        command = data['command']
        if not isinstance(command, list) or not all(
            isinstance(token, str) for token in command
        ):
            raise ValueError('job spec command must be a list of strings')
        return cls(
            command=list(command),
            exec_path=str(data['exec_path']),
            project_path=str(data['project_path']),
            plan_id=str(data['plan_id']),
            fingerprint=str(data.get('fingerprint', '')),
            # `data.get('timeout')` would map a present `null` onto the same
            # `None` an omitted key yields; the sentinel keeps them distinct.
            timeout=_coerce_wire_timeout(data.get('timeout', _ABSENT)),
        )


def compute_fingerprint(
    plan_id: str, command: list[str], exec_path: str, project_path: str
) -> str:
    """Derive the deterministic idempotent-submit fingerprint for a job.

    Two submits with the same plan, command (notation + args), and tree
    (exec_path + project_path) produce the SAME fingerprint, so the scheduler
    attaches an identical concurrent submit to one in-flight job rather than
    double-running it. The digest is order-stable (``sort_keys``) and
    independent of dict insertion order.

    ``JobSpec.timeout`` is deliberately NOT part of the material. On the ROUTING
    leg that costs nothing: the routing client reconstructs ``command`` from its
    own argv tail, so an explicit ``--timeout N`` is already a token INSIDE
    ``command`` and two submits with different bounds already digest differently.
    Adding the field would re-hash the same distinction a second time while
    changing every existing fingerprint.

    On the DIRECT surface (``submit --command X --timeout N``) the claim does not
    hold, and the qualification is stated here rather than left to be discovered:
    ``command`` is the JSON array passed via ``--command`` and ``--timeout`` is
    not among its tokens, so two submits differing only in bound digest
    identically and :meth:`Scheduler.submit` attaches the second to the first.
    The consequence is bounded by the floor rather than by this function: a
    request can only RAISE the daemon's supervisory bound, so two below-default
    requests resolve to the identical bound anyway and lose nothing by sharing a
    job. The field is still not added to the material — that would change every
    existing fingerprint for a narrow bounded case.

    Args:
        plan_id: The submitting plan id.
        command: The exact executor-form argv tokens.
        exec_path: The submitted tree root.
        project_path: The project working directory.

    Returns:
        A hex SHA-256 digest of the canonical job material.
    """
    material = json.dumps(
        {
            'plan_id': plan_id,
            'command': list(command),
            'exec_path': exec_path,
            'project_path': project_path,
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return sha256(material.encode('utf-8')).hexdigest()


def make_job_spec(
    command: list[str],
    exec_path: str,
    project_path: str,
    plan_id: str,
    fingerprint: str = '',
    timeout: int | None = None,
) -> JobSpec:
    """Construct a :class:`JobSpec`, deriving the fingerprint when absent.

    Args:
        command: The exact executor-form argv tokens.
        exec_path: The submitted tree root.
        project_path: The project working directory.
        plan_id: The submitting plan id.
        fingerprint: An explicit fingerprint; when empty it is derived via
            :func:`compute_fingerprint`.
        timeout: The submit's explicit wall-clock bound in seconds, or ``None``
            when it stated none (see :class:`JobSpec`). Not part of the
            fingerprint material — see :func:`compute_fingerprint`.

    Returns:
        A fully-populated job spec with a non-empty fingerprint.
    """
    resolved = fingerprint or compute_fingerprint(
        plan_id, command, exec_path, project_path
    )
    return JobSpec(
        command=list(command),
        exec_path=exec_path,
        project_path=project_path,
        plan_id=plan_id,
        fingerprint=resolved,
        timeout=timeout,
    )


# =============================================================================
# Status schema — mapping to/from the shared _build_result shape
# =============================================================================


def normalize_error(raw: dict[str, Any]) -> dict[str, Any]:
    """Coerce one error entry to the canonical ``{file,line,message,category}``.

    Missing keys default (``file``/``message``/``category`` → empty string,
    ``line`` → ``None``); extra keys are dropped so the wire shape is stable.

    Args:
        raw: A loosely-shaped error dict from a build-log parser.

    Returns:
        A dict with exactly the :data:`ERROR_FIELDS` keys.
    """
    return {
        'file': raw.get('file', ''),
        'line': raw.get('line'),
        'message': raw.get('message', ''),
        'category': raw.get('category', ''),
    }


def normalize_errors(raw_errors: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Normalise a list of error entries to the canonical error shape.

    Args:
        raw_errors: The parser's error list, or ``None``.

    Returns:
        A list of canonical error dicts (empty when input is falsy).
    """
    return [normalize_error(entry) for entry in (raw_errors or [])]


def wire_status_from_result(result_status: str) -> str:
    """Map a :mod:`_build_result` status to the wire status vocabulary.

    ``success`` → ``success``, ``error`` → ``failure``, ``timeout`` →
    ``timeout``, ``killed`` → ``killed``, ``indeterminate`` → ``failure``. Every
    one of the five lands on a member of :data:`TERMINAL_STATUSES`, which is the
    property a waiting client depends on to stop polling.

    An already-wire status (so the function is idempotent on the wire
    vocabulary), the empty string (:func:`status_from_result`'s default for a
    result carrying no status), and any value from outside both vocabularies pass
    through unchanged.

    Raises rather than passing through for exactly one input class: a value that
    IS a :mod:`_build_result` status (a member of :data:`_RESULT_STATUSES`) yet
    has no row in :data:`_RESULT_STATUS_TO_WIRE`. That is the drift this guard
    exists for — a sixth ``STATUS_*`` added to :mod:`_build_result` without a
    translation here — and passing it through is what published a non-terminal
    string onto the wire. The guard is UNREACHABLE while the table stays total,
    which is the intended steady state; a test proves it fires by REMOVING a row
    (simulating the real drift), never by inventing a status the vocabulary does
    not contain, because such a value legitimately passes through.

    Args:
        result_status: A ``_build_result`` status (``success`` / ``error`` /
            ``timeout`` / ``killed`` / ``indeterminate``), an already-wire
            status, or the empty string.

    Returns:
        The corresponding wire status, or the input unchanged when it belongs to
        neither vocabulary.

    Raises:
        ValueError: when ``result_status`` is a ``_build_result`` status with no
            row in the translation table.
    """
    mapped = _RESULT_STATUS_TO_WIRE.get(result_status)
    if mapped is not None:
        return mapped
    if result_status in _RESULT_STATUSES:
        raise ValueError(
            f'_build_result status {result_status!r} has no wire translation; '
            f'_RESULT_STATUS_TO_WIRE must be total over the {len(_RESULT_STATUSES)} '
            f'_build_result STATUS_* values. Passing it through would publish a '
            f'status outside the terminal wire vocabulary and hang a waiting client.'
        )
    return result_status


def result_status_from_wire(wire_status: str) -> str:
    """Map a wire status back to the :mod:`_build_result` vocabulary.

    ``success`` → ``success``, ``failure`` → ``error``, ``timeout`` →
    ``timeout``, ``killed`` → ``killed``. Statuses without a ``_build_result``
    equivalent (``running``, ``queued``, ``not_found``, ``refused``) pass through
    unchanged.

    **Not a true inverse of :func:`wire_status_from_result`**, and deliberately
    named without claiming to be. That function is non-injective — both ``error``
    and ``indeterminate`` map onto ``failure`` — so ``indeterminate`` has no wire
    representation to come back from. ``failure`` resolves to ``error``, the
    reading that was true before ``indeterminate`` gained a row and the one every
    caller already depends on; the ``indeterminate`` origin is not recoverable
    from the wire status alone and must be read from the job log if it is needed.

    Args:
        wire_status: A wire status value.

    Returns:
        The corresponding ``_build_result`` status, or the input unchanged.
    """
    return _WIRE_STATUS_TO_RESULT.get(wire_status, wire_status)


def status_payload(
    status: str,
    *,
    duration_seconds: int | None = None,
    log_file: str | None = None,
    exit_code: int | None = None,
    errors: list[dict[str, Any]] | None = None,
    **extra: Any,
) -> dict[str, Any]:
    """Build a wire status payload, omitting absent optional fields.

    Args:
        status: The wire status (one of the ``STATUS_*`` constants).
        duration_seconds: Wall-clock duration, when known.
        log_file: Path to the captured build log, when present.
        exit_code: The child process exit code, when terminal.
        errors: Parser findings; normalised to the canonical error shape.
        **extra: Additional status-specific fields (e.g. ``reason`` for
            ``refused``, ``eta`` / ``last_progress`` for ``running``).

    Returns:
        The status payload dict ready to frame.
    """
    payload: dict[str, Any] = {'status': status}
    if duration_seconds is not None:
        payload['duration_seconds'] = duration_seconds
    if log_file is not None:
        payload['log_file'] = log_file
    if exit_code is not None:
        payload['exit_code'] = exit_code
    if errors is not None:
        payload['errors'] = normalize_errors(errors)
    payload.update(extra)
    return payload


def status_from_result(
    result: dict[str, Any], *, killed: bool = False, **extra: Any
) -> dict[str, Any]:
    """Map a shared :mod:`_build_result` result dict to a wire status payload.

    The ``log_file`` / ``duration_seconds`` / ``exit_code`` / ``errors`` fields
    carry over from the result shape unchanged; only the status token is
    translated to the wire vocabulary. ``killed=True`` forces
    :data:`STATUS_KILLED` regardless of the result's own status — the supervisor
    marks an externally-killed job out of band and it must never be folded into
    ``failure``.

    Args:
        result: A ``DirectCommandResult``-shaped dict.
        killed: When ``True``, force the ``killed`` terminal status.
        **extra: Additional status fields to merge in.

    Returns:
        The wire status payload dict.
    """
    status = (
        STATUS_KILLED if killed else wire_status_from_result(result.get('status', ''))
    )
    return status_payload(
        status,
        duration_seconds=result.get('duration_seconds'),
        log_file=result.get('log_file'),
        exit_code=result.get('exit_code'),
        errors=result.get('errors'),
        **extra,
    )


# =============================================================================
# Log-verdict reader — the single shared routed-build verdict authority
# =============================================================================
# The daemon's child is normally a build wrapper, and the wrapper exits 0 even
# when the build failed — it reports its real verdict in the build-result TOON it
# emits (``status:`` / ``exit_code:``), not in its process exit code. Both the
# daemon (:mod:`_marshalld_supervisor`'s ``run_job`` exit-0-necessary-not-
# sufficient narrowing) and the client (:mod:`_build_execute_factory`'s
# ``_daemon_result_to_direct`` cross-check) read that emitted verdict back through
# THIS one reader, so a routed false-green is caught the same way on both sides.


@dataclass(frozen=True)
class LogVerdict:
    """The build wrapper's own verdict, read back from a job log.

    Attributes:
        status: The ``status:`` value the emitted build TOON carried
            (``success`` / ``error`` / ``timeout`` / ``killed`` /
            ``indeterminate`` — the five-valued :mod:`_build_result` vocabulary,
            NOT the daemon's four-valued wire vocabulary).
            **Both readers must preserve WHICH of these it is.** ``timeout`` and
            ``killed`` are NON-FINISHES and ``indeterminate`` is an unestablished
            outcome: in none of the three did the wrapper report a verdict, so
            collapsing any of them into a failure at the cross-check reinstates
            the very false signal this shared reader exists to catch, one layer
            in.

            The field is a value READ OFF A LOG, so it is not guaranteed to be a
            member of that vocabulary at all — a truncated or foreign log can
            yield anything. A consumer that must translate it therefore treats an
            unrecognised value fail-closed as ``indeterminate`` (ADR-009) rather
            than passing it on or raising; see
            :mod:`_marshalld_supervisor`'s use of this reader.
        exit_code: The ``exit_code:`` value, or ``None`` when the log carried no
            parseable one.
        tests_run: The ``tests_run:`` value — the EXECUTED-test count the INNER
            wrapper measured and published (``passed + failed``, never the
            collected total). ``None`` when the log carried no parseable one,
            which means UNKNOWN and never zero: the routed client reconstructs its
            own count from this field, and a zero substituted for an absent one is
            what made a 2750-test run announce that it had tested nothing. Only a
            green run publishes the key at all, so ``None`` is the normal value on
            every non-green verdict.
    """

    status: str
    exit_code: int | None
    tests_run: int | None = None


def _toon_scalar(line: str) -> str:
    """Return the unquoted scalar value of a ``key: value`` TOON line."""
    value = line.split(':', 1)[1].strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
        return value[1:-1]
    return value


def read_log_verdict(log_file: str) -> LogVerdict | None:
    """Read the build wrapper's emitted TOON verdict back from a job log.

    Pure with respect to any daemon/client state — it only reads the log the
    supervisor already streamed. Only the three top-level (column-0) ``status:``,
    ``exit_code:`` and ``tests_run:`` keys are parsed; indented TOON rows (e.g.
    ``errors[]`` table lines) and every other key are ignored. The LAST occurrence
    of each key wins, because the wrapper emits its result TOON after any progress
    output it already wrote to the same log.

    ``status:`` is what makes a verdict exist; the other two are enrichment.
    ``tests_run`` is read here rather than re-derived by the client because the
    client's own parser sees only THIS log — the wrapper's emitted TOON — and not
    the raw test-runner output the inner build parsed. Re-parsing therefore yields
    no test summary, and reporting that as a zero is a false could-not-look over a
    fully-examined population. The inner wrapper already measured the count; the
    reader's job is to carry it, not to recompute it.

    A log with a ``status:`` but no ``tests_run:`` therefore yields a verdict whose
    ``tests_run`` is ``None`` — the honest "the log stated no count", which a
    caller must not collapse into ``0``. A ``tests_run:`` that is unparseable OR
    NEGATIVE yields that same ``None``: an executed-test count below zero is not a
    count, and reporting it as one would launder a nonsense value into a
    measurement. ``tests_run: 0`` is kept, because "executed no tests" is a real
    fact and a different one from "stated no count".

    Args:
        log_file: Path to the job log the supervisor streamed the child into.

    Returns:
        The parsed :class:`LogVerdict`, or ``None`` when the log is missing,
        unreadable, or carries no top-level ``status:`` line at all.
    """
    status: str | None = None
    exit_code: int | None = None
    tests_run: int | None = None
    try:
        with open(log_file, encoding='utf-8', errors='replace') as handle:
            for line in handle:
                if line.startswith('status:'):
                    status = _toon_scalar(line)
                elif line.startswith('exit_code:'):
                    try:
                        exit_code = int(_toon_scalar(line))
                    except ValueError:
                        exit_code = None
                elif line.startswith('tests_run:'):
                    try:
                        parsed_count = int(_toon_scalar(line))
                    except ValueError:
                        # An unparseable count is UNKNOWN, not zero — the whole
                        # point of carrying the field is that the two differ.
                        tests_run = None
                    else:
                        # ``int`` accepts ``-1`` happily, so the ValueError guard
                        # alone lets a negative through as a real non-``None``
                        # count. A negative executed-test count is meaningless;
                        # publishing it launders nonsense into a measurement.
                        # ``None`` is the honest "the log stated no usable count".
                        # The bound is ``>= 0``, not ``> 0``: zero is a genuine
                        # "this run executed no tests", a different fact from
                        # "the log stated no count".
                        tests_run = parsed_count if parsed_count >= 0 else None
    except OSError:
        return None
    if status is None:
        return None
    return LogVerdict(status=status, exit_code=exit_code, tests_run=tests_run)
