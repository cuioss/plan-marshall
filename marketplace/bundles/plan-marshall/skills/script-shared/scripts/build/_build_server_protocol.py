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
  either side re-implementing the result contract.

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

import asyncio
import json
import socket
import struct
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

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

# Map the shared _build_result status vocabulary (success|error|timeout) to the
# wire vocabulary (success|failure|timeout). ``killed`` has no _build_result
# equivalent — the supervisor sets it out of band — so it is not in this table.
_RESULT_STATUS_TO_WIRE = {
    'success': STATUS_SUCCESS,
    'error': STATUS_FAILURE,
    'timeout': STATUS_TIMEOUT,
}
_WIRE_STATUS_TO_RESULT = {wire: res for res, wire in _RESULT_STATUS_TO_WIRE.items()}

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
        plan_id: The submitting plan id (empty string for a plan-less build).
        fingerprint: The idempotent-submit fingerprint; empty until derived via
            :func:`compute_fingerprint` (see :func:`make_job_spec`).
    """

    command: list[str]
    exec_path: str
    project_path: str
    plan_id: str
    fingerprint: str = ''

    def to_dict(self) -> dict[str, Any]:
        """Return the JSON-serialisable wire form of this job spec."""
        return {
            'command': list(self.command),
            'exec_path': self.exec_path,
            'project_path': self.project_path,
            'plan_id': self.plan_id,
            'fingerprint': self.fingerprint,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> JobSpec:
        """Build a :class:`JobSpec` from a decoded wire dict.

        Args:
            data: A decoded frame payload carrying the job-spec fields.

        Returns:
            The reconstructed job spec.

        Raises:
            ValueError: when a required field is missing, or ``command`` is not
                a list of strings.
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
) -> JobSpec:
    """Construct a :class:`JobSpec`, deriving the fingerprint when absent.

    Args:
        command: The exact executor-form argv tokens.
        exec_path: The submitted tree root.
        project_path: The project working directory.
        plan_id: The submitting plan id.
        fingerprint: An explicit fingerprint; when empty it is derived via
            :func:`compute_fingerprint`.

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
    ``timeout``. An already-wire status (or an unknown value) passes through
    unchanged, so this is idempotent on the wire vocabulary.

    Args:
        result_status: A ``_build_result`` status (``success``/``error``/``timeout``).

    Returns:
        The corresponding wire status.
    """
    return _RESULT_STATUS_TO_WIRE.get(result_status, result_status)


def result_status_from_wire(wire_status: str) -> str:
    """Inverse of :func:`wire_status_from_result`.

    ``success`` → ``success``, ``failure`` → ``error``, ``timeout`` →
    ``timeout``. Statuses without a ``_build_result`` equivalent (``killed``,
    ``running``, ``queued``, …) pass through unchanged.

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
            (``success`` / ``error`` / ``timeout`` — the :mod:`_build_result`
            vocabulary, NOT the daemon's wire vocabulary).
        exit_code: The ``exit_code:`` value, or ``None`` when the log carried no
            parseable one.
    """

    status: str
    exit_code: int | None


def _toon_scalar(line: str) -> str:
    """Return the unquoted scalar value of a ``key: value`` TOON line."""
    value = line.split(':', 1)[1].strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
        return value[1:-1]
    return value


def read_log_verdict(log_file: str) -> LogVerdict | None:
    """Read the build wrapper's emitted TOON verdict back from a job log.

    Pure with respect to any daemon/client state — it only reads the log the
    supervisor already streamed. Only the two top-level (column-0) ``status:``
    and ``exit_code:`` keys are parsed; indented TOON rows (e.g. ``errors[]``
    table lines) and every other key are ignored. The LAST occurrence of each key
    wins, because the wrapper emits its result TOON after any progress output it
    already wrote to the same log.

    Args:
        log_file: Path to the job log the supervisor streamed the child into.

    Returns:
        The parsed :class:`LogVerdict`, or ``None`` when the log is missing,
        unreadable, or carries no top-level ``status:`` line at all.
    """
    status: str | None = None
    exit_code: int | None = None
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
    except OSError:
        return None
    if status is None:
        return None
    return LogVerdict(status=status, exit_code=exit_code)
