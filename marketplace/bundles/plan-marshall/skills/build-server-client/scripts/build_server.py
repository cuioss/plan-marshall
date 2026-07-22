#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""build_server — the marshalld build-server CLIENT (consumption surface).

Notation: ``plan-marshall:build-server-client:build_server``

This is the tiny, deterministic consumption surface a build-dispatching context
uses to talk to ``marshalld``. It owns four verbs and NOTHING else — it never
provisions, starts, registers, or enrols anything (that is the separate
user-invocable ``manage-build-server`` control skill, the anti-laundering wall):

* ``submit`` — S3-verify the daemon (socket-owner uid check + version handshake),
  send a job spec, and on acceptance persist the daemon-assigned ``job_id`` to the
  change-ledger (``kind=job``) so a rebuilt / harness-reaped session can re-attach
  from plan state alone. When the daemon is unreachable or an impostor owns the
  socket, returns ``degraded(reason=…)`` so the caller falls back to an in-process
  build (never a hard failure).
* ``wait`` — one server-side bounded long-poll. Returns a terminal status-TOON, or
  on bound expiry a LIVE ``running`` status (``elapsed`` / ``eta`` /
  ``last_progress``) — NEVER a timeout-shaped empty body. The caller re-issues
  ``wait`` on a ``running`` return; it MUST NOT ``run_in_background`` or ``sleep``
  the wait (a harness-reaped wait costs one re-poll, not the whole build). With no
  ``--job-id`` the verb re-attaches via the latest ``kind=job`` ledger row for the
  plan.
* ``ping`` — the identity handshake alone: report the daemon version/pid, or
  ``down`` + a named reason.
* ``preflight`` — F2, ONE deterministic call returning exactly one of
  ``disabled`` (project not registered — NO daemon round-trip), ``ready`` (daemon
  answered a verified handshake), or ``down`` + a named reason.

The daemon answers one op per connection (it reads one frame, replies, closes), so
the S3 handshake is its own short-lived ``ping`` connection distinct from the
follow-up ``submit`` / ``wait`` connection. The socket lives beside the registry
under the machine-global marshalld state dir; the client resolves it from
:func:`_build_server_registry.registry_dir` rather than importing the daemon.

Usage:
    python3 .plan/execute-script.py plan-marshall:build-server-client:build_server preflight
    python3 .plan/execute-script.py plan-marshall:build-server-client:build_server submit \
        --command '["python3", "/tree/.plan/execute-script.py", "notation", "run"]' \
        --exec-path /tree --project-path /tree --plan-id my-plan
    python3 .plan/execute-script.py plan-marshall:build-server-client:build_server wait --job-id JOB
    python3 .plan/execute-script.py plan-marshall:build-server-client:build_server ping
"""

from __future__ import annotations

import argparse
import json
import os
import re
import socket
from argparse import Namespace
from pathlib import Path
from typing import Any

from _build_server_protocol import (
    PROTOCOL_VERSION,
    STATUS_KILLED,
    STATUS_QUEUED,
    STATUS_REFUSED,
    FrameError,
    make_job_spec,
    recv_frame,
    send_frame,
)
from _build_server_registry import (
    canonicalize_root,
    find_project_for_root,
    read_registry,
    registry_dir,
)
from _ledger_core import KIND_JOB, append_entry, job_record, read_entries
from marketplace_paths import main_checkout_root
from plan_logging import log_entry
from triage_helpers import ErrorCode, make_error, print_toon, safe_main
from worktree_sha import compute_worktree_sha

# The socket filename mirrors marshalld.socket_path() — the daemon binds
# `<home_root>/marshalld/socket`, and registry_dir() resolves that same
# `<home_root>/marshalld` directory, so the client reaches the socket without
# importing (or coupling to) the daemon module.
_SOCKET_FILENAME = 'socket'

_DEFAULT_WAIT_BOUND = 300
"""Default wait long-poll bound in seconds (matches the daemon default)."""

_CONNECT_TIMEOUT_SECONDS = 5.0
"""Socket connect / short-op (ping, submit) I/O timeout."""

_WAIT_TIMEOUT_MARGIN_SECONDS = 30
"""Extra socket-read budget over the wait bound (the daemon holds up to `bound`)."""

# Degraded (fallback) reasons — the caller reads `reason` and falls back to an
# in-process build; NONE of these is a hard failure.
REASON_SOCKET_ABSENT = 'socket_absent'
REASON_IMPOSTOR_SOCKET = 'impostor_socket'
REASON_UNREACHABLE = 'unreachable'
REASON_VERSION_MISMATCH = 'version_mismatch'
REASON_HANDSHAKE_FAILED = 'handshake_failed'

_KILLED_MESSAGE = 'externally killed — not flaky, do not blind-retry'

# Fields passed through from a daemon status payload to the client-facing TOON.
_PASSTHROUGH_STATUS_FIELDS = (
    'job_id',
    'elapsed',
    'eta',
    'last_progress',
    'exit_code',
    'duration_seconds',
    'log_file',
)


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------


def _socket_path() -> Path:
    """Return the machine-global marshalld socket path (beside the registry)."""
    return registry_dir() / _SOCKET_FILENAME


def _resolve_project_root(explicit: str | None) -> str:
    """Resolve the project root for a registry lookup, canonicalised.

    An explicit ``--project-path`` wins; otherwise the caller's main checkout
    root is used, falling back to the current working directory when the caller
    is not inside a git repository.

    Args:
        explicit: The ``--project-path`` value, or ``None``.

    Returns:
        The canonical (symlink-resolved, absolute) project root string.
    """
    if explicit:
        return canonicalize_root(explicit)
    try:
        return canonicalize_root(main_checkout_root())
    except RuntimeError:
        return canonicalize_root(os.getcwd())


# ---------------------------------------------------------------------------
# S3 identity: socket-owner check + version handshake
# ---------------------------------------------------------------------------


def _socket_owner_reason(sock_path: Path) -> str | None:
    """Return a degraded reason when the socket is absent or owned by another uid.

    S3: the client trusts a daemon response only when the socket is owned by the
    client's own uid — an impostor socket planted by another user is treated as
    unreachable (fallback), never trusted. A missing socket means the daemon is
    down.

    Args:
        sock_path: The daemon socket path.

    Returns:
        :data:`REASON_SOCKET_ABSENT`, :data:`REASON_IMPOSTOR_SOCKET`, or ``None``
        when the socket exists and is owned by this uid.
    """
    if not sock_path.exists():
        return REASON_SOCKET_ABSENT
    try:
        stat_result = os.stat(sock_path)
    except OSError:
        return REASON_SOCKET_ABSENT
    if stat_result.st_uid != os.getuid():
        return REASON_IMPOSTOR_SOCKET
    return None


def _call_daemon(request: dict[str, Any], *, timeout: float) -> dict[str, Any]:
    """Open a short-lived connection, send one request frame, return the response.

    The daemon serves exactly one op per connection, so each call gets a fresh
    connection. The socket is closed unconditionally.

    Args:
        request: The request payload (carries the ``op`` discriminator).
        timeout: Socket connect / I/O timeout in seconds.

    Returns:
        The decoded response payload.

    Raises:
        OSError: on connect / I/O failure.
        FrameError: on a truncated or malformed response frame.
    """
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect(str(_socket_path()))
        send_frame(sock, request)
        return recv_frame(sock)
    finally:
        sock.close()


def _handshake(sock_path: Path) -> tuple[dict[str, Any] | None, str | None]:
    """Perform the S3 identity handshake: owner check + verified ``ping``.

    Returns the ping response when the socket is owned by this uid AND the daemon
    answers ``status: ok`` with the expected :data:`PROTOCOL_VERSION`; otherwise
    returns a named degraded reason and no response.

    Args:
        sock_path: The daemon socket path.

    Returns:
        A ``(response, reason)`` pair — exactly one is non-``None``.
    """
    reason = _socket_owner_reason(sock_path)
    if reason is not None:
        return None, reason
    try:
        response = _call_daemon({'op': 'ping'}, timeout=_CONNECT_TIMEOUT_SECONDS)
    except (OSError, FrameError):
        return None, REASON_UNREACHABLE
    if response.get('status') != 'ok':
        return None, REASON_HANDSHAKE_FAILED
    if str(response.get('version', '')) != PROTOCOL_VERSION:
        return None, REASON_VERSION_MISMATCH
    return response, None


# ---------------------------------------------------------------------------
# Result rendering
# ---------------------------------------------------------------------------


def _audit_log(plan_id: str, level: str, message: str) -> None:
    """Write one captured work-log entry for a build-server interaction outcome.

    No-ops for a plan-less build (empty ``plan_id``) — there is no per-plan work
    log to write to. Otherwise it delegates to the same ``plan_logging``
    substrate the ``manage-logging`` work verb writes through, so no interaction
    outcome is emitted only at an uncaptured Python log level and silently lost.

    Secrets discipline: callers pass ONLY non-secret correlation fields
    (``job_id`` / ``job_status`` / ``reason`` / ``notation`` / ``attached`` /
    ``elapsed`` / ``eta``) — NEVER the raw ``--command`` argv, ``exec_path`` /
    ``project_path``, env, or any spec field that may carry secrets.

    Args:
        plan_id: Submitting plan id; empty for a plan-less build (no-op).
        level: Captured log level — ``INFO`` for a normal outcome, ``WARNING``
            for a fallback / refusal.
        message: The pre-formatted, secret-free outcome message.
    """
    if not plan_id:
        return
    log_entry('work', plan_id, level, message)


def _degraded(reason: str) -> dict[str, Any]:
    """Render a degraded (fallback) result the caller acts on by building locally."""
    return {
        'status': 'degraded',
        'reason': reason,
        'fallback': 'in_process',
        'message': f'build server unavailable ({reason}); fall back to in-process build',
    }


def _render_job_status(response: dict[str, Any]) -> dict[str, Any]:
    """Map a daemon status payload to the client-facing TOON.

    The daemon's ``status`` becomes ``job_status`` (so the client-call ``status``
    stays free to report the CLIENT outcome); the running / terminal detail
    fields pass through. A ``killed`` job carries the no-blind-retry message so a
    harness reap is never mistaken for a flaky build.

    Args:
        response: The decoded daemon status payload.

    Returns:
        The client-facing result dict.
    """
    job_status = str(response.get('status', ''))
    out: dict[str, Any] = {'status': 'success', 'job_status': job_status}
    for key in _PASSTHROUGH_STATUS_FIELDS:
        if key in response:
            out[key] = response[key]
    if 'errors' in response:
        out['errors'] = response['errors']
    if job_status == STATUS_KILLED:
        out['message'] = _KILLED_MESSAGE
    return out


# ---------------------------------------------------------------------------
# Re-attach via the change-ledger
# ---------------------------------------------------------------------------


def _record_job(job_id: str, plan_id: str, fingerprint: str, notation: str, project_path: str) -> None:
    """Persist a ``kind=job`` re-attach row to the change-ledger at submit time."""
    append_entry(
        job_record(
            job_id=job_id,
            plan_id=plan_id or None,
            fingerprint=fingerprint,
            notation=notation,
            worktree_sha=compute_worktree_sha(project_path),
        )
    )


def _latest_job_id_for_plan(plan_id: str) -> str | None:
    """Return the most recent ledger ``kind=job`` ``job_id`` for ``plan_id``.

    The re-attach path: a session that lost its ``job_id`` (rebuilt context, a
    harness-reaped wait) recovers the in-flight build's id from the durable
    ledger rather than losing the running build.

    Args:
        plan_id: The plan whose latest submission to recover.

    Returns:
        The latest recorded ``job_id`` for the plan, or ``None`` when none exists.
    """
    matches = [
        entry.get('job_id')
        for entry in read_entries()
        if entry.get('kind') == KIND_JOB
        and entry.get('plan_id') == (plan_id or None)
        and entry.get('job_id')
    ]
    return str(matches[-1]) if matches else None


_CONTROL_CHAR_PATTERN = re.compile(r'[\x00-\x1f\x7f]')
"""C0 control characters (incl. ``\\n`` / ``\\r``) plus DEL, stripped from the
notation before it is interpolated into a free-text ``_audit_log`` message.

The plan-scoped work log (``plan_logging.format_log_entry``) is a plain-text,
line-oriented format parsed back by a per-line header regex — it is NOT
JSON-escaped. ``command[2]`` is a client-supplied string (from ``--command``,
validated only as "a JSON array of strings"), so an unsanitized embedded
newline could forge a fake ``[timestamp] [LEVEL] [hash]`` header line into the
work log (CWE-117 log injection). Stripping control characters here closes
that vector while leaving a well-formed notation (e.g.
``plan-marshall:build-pyproject:pyproject_build``) byte-identical."""


def _sanitize_for_log(value: str) -> str:
    """Strip control characters so ``value`` is safe to interpolate into a message.

    The plan-scoped work log is a line-oriented plain-text format parsed back by a
    per-line header regex (see :data:`_CONTROL_CHAR_PATTERN`). Any client-supplied
    string interpolated into an ``_audit_log`` message — the executor notation OR a
    ``--job-id`` — could otherwise forge a fake header line (CWE-117 log injection).
    This is the single sanitization seam for every such value.
    """
    return _CONTROL_CHAR_PATTERN.sub('', value)


def _notation_from_command(command: list[str]) -> str:
    """Derive the executor notation (``command[2]``) from an executor-form argv.

    Control characters are stripped (see :func:`_sanitize_for_log`) so the
    returned value is always safe to interpolate into a free-text log message
    or ledger field. This sanitized value is used ONLY for correlation/logging
    (``_audit_log`` messages, the ledger ``kind=job`` row) — the original,
    unmodified ``command`` list is still what is submitted to the daemon, so
    the S1.4 notation-allowlist check the verifier performs is unaffected.
    """
    if len(command) < 3:
        return ''
    return _sanitize_for_log(command[2])


# ---------------------------------------------------------------------------
# Verbs
# ---------------------------------------------------------------------------


def run_submit(args: Namespace) -> dict[str, Any]:
    """Verify the daemon, submit a job, and record the ``job_id`` for re-attach."""
    try:
        command = json.loads(args.command)
    except json.JSONDecodeError as exc:
        return make_error(
            f'--command must be a JSON array of argv tokens: {exc}',
            code=ErrorCode.INVALID_INPUT,
        )
    if not isinstance(command, list) or not all(isinstance(token, str) for token in command):
        return make_error(
            '--command must be a JSON array of strings',
            code=ErrorCode.INVALID_INPUT,
        )

    project_path = args.project_path or os.getcwd()
    exec_path = args.exec_path or project_path
    plan_id = args.plan_id or ''
    notation = _notation_from_command(command)
    spec = make_job_spec(
        command=command,
        exec_path=exec_path,
        project_path=project_path,
        plan_id=plan_id,
    )

    _, reason = _handshake(_socket_path())
    if reason is not None:
        _audit_log(plan_id, 'WARNING', f'build-server submit degraded: reason={reason} notation={notation}')
        return _degraded(reason)

    try:
        response = _call_daemon({'op': 'submit', 'job': spec.to_dict()}, timeout=_CONNECT_TIMEOUT_SECONDS)
    except (OSError, FrameError):
        _audit_log(plan_id, 'WARNING', f'build-server submit degraded: reason={REASON_UNREACHABLE} notation={notation}')
        return _degraded(REASON_UNREACHABLE)

    status = str(response.get('status', ''))
    if status == STATUS_REFUSED:
        refused_reason = str(response.get('reason', ''))
        _audit_log(
            plan_id,
            'WARNING',
            f'build-server submit refused: reason={_sanitize_for_log(refused_reason)} notation={notation}',
        )
        return {
            'status': 'refused',
            'reason': refused_reason,
            'message': f'submit refused by verifier: {refused_reason}',
        }
    if status != STATUS_QUEUED:
        _audit_log(plan_id, 'WARNING', f'build-server submit degraded: reason={REASON_UNREACHABLE} notation={notation}')
        return _degraded(REASON_UNREACHABLE)

    job_id = str(response.get('job_id', ''))
    attached = bool(response.get('attached', False))
    _record_job(job_id, plan_id, spec.fingerprint, notation, project_path)
    _audit_log(
        plan_id,
        'INFO',
        f'build-server submit queued: job_id={_sanitize_for_log(job_id)} job_status={STATUS_QUEUED} '
        f'attached={attached} notation={notation}',
    )
    return {
        'status': 'success',
        'job_status': STATUS_QUEUED,
        'job_id': job_id,
        'attached': attached,
    }


def run_wait(args: Namespace) -> dict[str, Any]:
    """Do one bounded long-poll, re-attaching via the ledger when no id is given."""
    plan_id = args.plan_id or ''
    job_id = args.job_id or _latest_job_id_for_plan(plan_id)
    if not job_id:
        return make_error(
            'no --job-id given and no kind=job ledger row to re-attach to'
            + (f' for plan {args.plan_id}' if args.plan_id else ''),
            code=ErrorCode.NOT_FOUND,
        )

    bound = args.bound if args.bound is not None else _DEFAULT_WAIT_BOUND
    _, reason = _handshake(_socket_path())
    if reason is not None:
        _audit_log(plan_id, 'WARNING', f'build-server wait degraded: reason={reason}')
        return _degraded(reason)

    try:
        response = _call_daemon(
            {'op': 'wait', 'job_id': job_id, 'bound': bound},
            timeout=float(bound) + _WAIT_TIMEOUT_MARGIN_SECONDS,
        )
    except (OSError, FrameError):
        _audit_log(plan_id, 'WARNING', f'build-server wait degraded: reason={REASON_UNREACHABLE}')
        return _degraded(REASON_UNREACHABLE)

    result = _render_job_status(response)
    # job_id may be a client-supplied `--job-id`, and job_status/elapsed/eta come
    # back from the daemon response; sanitize every one before interpolating it
    # into the line-oriented work log (CWE-117), exactly as notation is sanitized.
    _audit_log(
        plan_id,
        'INFO',
        f'build-server wait result: job_id={_sanitize_for_log(job_id)} '
        f'job_status={_sanitize_for_log(str(result.get("job_status", "")))} '
        f'elapsed={_sanitize_for_log(str(result.get("elapsed", "")))} '
        f'eta={_sanitize_for_log(str(result.get("eta", "")))}',
    )
    return result


def run_ping(_args: Namespace) -> dict[str, Any]:
    """Report the daemon identity (version + pid), or ``down`` + a named reason."""
    response, reason = _handshake(_socket_path())
    if response is not None:
        return {
            'status': 'success',
            'daemon': 'up',
            'version': str(response.get('version', '')),
            'pid': response.get('pid'),
            'socket_path': str(_socket_path()),
        }
    return {
        'status': 'success',
        'daemon': 'down',
        'reason': reason,
        'socket_path': str(_socket_path()),
    }


def run_preflight(args: Namespace) -> dict[str, Any]:
    """F2 — ONE deterministic call: ``disabled`` | ``ready`` | ``down`` + reason.

    ``disabled`` when the project is not registered (NO daemon round-trip —
    an unregistered project must never touch the socket); otherwise a verified
    handshake decides ``ready`` (daemon answered) or ``down`` (+ named reason).
    """
    project_root = _resolve_project_root(args.project_path)
    registry = read_registry()
    if find_project_for_root(registry, project_root) is None:
        return {
            'status': 'success',
            'preflight': 'disabled',
            'registered': False,
            'project_root': project_root,
            'message': 'project not registered — build server disabled (no daemon probe)',
        }

    response, reason = _handshake(_socket_path())
    if response is not None:
        return {
            'status': 'success',
            'preflight': 'ready',
            'registered': True,
            'project_root': project_root,
            'version': str(response.get('version', '')),
        }
    return {
        'status': 'success',
        'preflight': 'down',
        'registered': True,
        'project_root': project_root,
        'reason': reason,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_arg_parser() -> argparse.ArgumentParser:
    """Build the client argparse surface (submit / wait / ping / preflight)."""
    parser = argparse.ArgumentParser(
        prog='build_server',
        description='marshalld build-server client (submit / wait / ping / preflight).',
        allow_abbrev=False,
    )
    sub = parser.add_subparsers(dest='command', required=True)

    submit = sub.add_parser('submit', help='Verify the daemon and submit a build job.', allow_abbrev=False)
    submit.add_argument(
        '--command',
        required=True,
        help='The executor-form argv as a JSON array of strings.',
    )
    submit.add_argument('--exec-path', help='Submitted tree root (default: --project-path).')
    submit.add_argument('--project-path', help='Build working directory (default: cwd).')
    submit.add_argument('--plan-id', help='Submitting plan id (empty for a plan-less build).')
    submit.set_defaults(func=run_submit)

    wait = sub.add_parser('wait', help='One bounded long-poll for a job result.', allow_abbrev=False)
    wait.add_argument('--job-id', help='Job id to wait on (default: re-attach via ledger).')
    wait.add_argument('--plan-id', help='Plan id used to re-attach when --job-id is omitted.')
    wait.add_argument(
        '--bound',
        type=int,
        help=f'Long-poll bound in seconds (default: {_DEFAULT_WAIT_BOUND}).',
    )
    wait.set_defaults(func=run_wait)

    ping = sub.add_parser('ping', help='Report the daemon identity, or down + reason.', allow_abbrev=False)
    ping.set_defaults(func=run_ping)

    preflight = sub.add_parser(
        'preflight',
        help='One call: disabled | ready | down + reason.',
        allow_abbrev=False,
    )
    preflight.add_argument('--project-path', help='Project root (default: caller main checkout).')
    preflight.set_defaults(func=run_preflight)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point — dispatch a client verb and print its TOON result."""
    args = _build_arg_parser().parse_args(argv)
    return print_toon(args.func(args))


if __name__ == '__main__':
    safe_main(main)()
