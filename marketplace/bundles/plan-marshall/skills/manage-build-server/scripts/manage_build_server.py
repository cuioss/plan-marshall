#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""manage-build-server — the operator control surface for ``marshalld``.

Notation: ``plan-marshall:manage-build-server:manage_build_server``

This is the user-invocable control skill's executor: the deterministic verbs the
operator drives to enrol a project and manage the machine-global build-server
daemon. It is the **operator-interactivity wall** (S1) — ``register`` /
``unregister`` write the machine-global ``registry.json`` and live ONLY here,
never in a dispatch's ``skills[]``, so a plan can never launder itself onto the
served set. The daemon is strictly opt-in: registration IS the enable signal
(there is no config knob and nothing git-tracked).

Verbs:

* ``register`` / ``unregister`` — upsert / drop a project in the machine-global
  registry via the shared :mod:`_build_server_registry` module (each mutation
  appends a registration audit line inside that module).
* ``start`` — launch the daemon detached, pinned to the verified bundle copy of
  :mod:`marshalld` co-located with THIS control skill (S5: the daemon runs from
  the same verified plugin-cache/bundle version that owns the control surface,
  never a project-local executor an attacker could tamper with). Refuses to
  start a second daemon when one is already live.
* ``stop`` — forced stop: ``SIGTERM`` then ``SIGKILL`` after a grace window, then
  clean up the socket / pidfile.
* ``drain`` — graceful stop: request the daemon to shut down (``SIGTERM``) and
  wait for it to exit on its own, without escalating to ``SIGKILL``. In-flight
  jobs are recorded in the journal and replayed as ``killed`` on the next start
  (never silently lost), so a drained-then-restarted daemon reports them
  truthfully rather than resuming them.
* ``status`` — ping the daemon over its ``0600`` socket and report the running
  version, the daemon's in-flight / queued job counts (``unknown`` when the
  daemon did not send them — never ``0``, which would read as idle), and the
  binary the RUNNING process is executing (``running_binary_path``, read from
  the live process)
  alongside the resolve-now path (``resolved_binary_path``); ``binary_diverges``
  flags a stale daemon and an undeterminable running provenance is ``unknown``,
  never the resolved path (S5, D4). Reports ``down`` with a named reason when the
  daemon is unreachable.
* ``install`` — idempotent version-pinned start (a no-op when already running).
* ``upgrade`` — drain the running daemon then start the verified version (S7).
  Reports ``drain_exited`` and ``already_running`` — the two fields that can
  carry a FAILED upgrade — and sets ``status: error`` with a ``reason`` when
  either says the old daemon was never replaced, so a caller never has to read
  success out of the word alone.
* ``logs`` — read-only, project-scoped inspection of the daemon's central
  ``interaction-audit.log`` (the derived per-project view); never mutates it.
  Each row is rendered with an explicit ``kind`` label, and an interaction row
  carries its request-scoped ``request_status`` and the job's ``fate`` as two
  separate columns, so a per-request row can never be misread as a job record.

Every lifecycle verb appends one JSON-lines entry to the append-only lifecycle
audit log (``lifecycle-audit.log`` under the daemon state dir) so the daemon's
operational history stays reconstructable alongside the registration audit.

Usage:
    python3 .plan/execute-script.py plan-marshall:manage-build-server:manage_build_server register
    python3 .plan/execute-script.py plan-marshall:manage-build-server:manage_build_server start
    python3 .plan/execute-script.py plan-marshall:manage-build-server:manage_build_server status
    python3 .plan/execute-script.py plan-marshall:manage-build-server:manage_build_server stop
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import socket
import subprocess
import sys
import time
from argparse import Namespace
from pathlib import Path
from typing import Any

import marshalld
from _build_execute_factory import routable_notations
from _build_server_protocol import FrameError, recv_frame, send_frame
from _build_server_registry import (
    canonicalize_root,
    find_project_for_root,
    get_project,
    read_registry,
    register_project,
    unregister_project,
)
from _marshalld_audit import (
    FATE_UNKNOWN,
    KIND_INTERACTION,
    KIND_JOB_FATE,
    InteractionAudit,
)
from file_ops import now_utc_iso
from marketplace_paths import main_checkout_root
from triage_helpers import ErrorCode, make_error, print_toon, safe_main

_LIFECYCLE_AUDIT_FILENAME = 'lifecycle-audit.log'
_FILE_MODE = 0o600

_STOP_GRACE_SECONDS = 10.0
_DRAIN_GRACE_SECONDS = 30.0
_POLL_INTERVAL_SECONDS = 0.2
_PING_TIMEOUT_SECONDS = 5.0
_SPAWN_REAP_TIMEOUT_SECONDS = 10.0
_PS_TIMEOUT_SECONDS = 5.0
"""Bounded timeout for the ``ps`` provenance fallback on non-``/proc`` platforms."""

_UNKNOWN_PROVENANCE = 'unknown'
"""Sentinel ``status`` reports when the RUNNING daemon's binary cannot be
determined from the live process. It is NEVER the resolved-now path — substituting
that path for an undeterminable running provenance IS the drift-hiding defect."""

_UNKNOWN_COUNT = 'unknown'
"""Sentinel ``status`` reports for an in-flight / queued count the daemon did not
send. A daemon pinned to a copy predating the counts extension omits both keys;
coercing that absence to ``0`` would render it indistinguishable from a genuinely
idle daemon, which is precisely what lets a reconcile drain a live build."""

_DEFAULT_LOGS_LIMIT = 50
"""Default bounded tail size for the read-only ``logs`` audit-inspection verb."""


# ---------------------------------------------------------------------------
# Root resolution
# ---------------------------------------------------------------------------


def _resolve_root(explicit: str | None) -> str:
    """Resolve the project root to register / unregister.

    An explicit ``--root`` wins; otherwise the caller's main checkout root is
    used (registration is an operator action taken from within the project).
    The value is canonicalised (symlink-resolved, absolute) so it matches the
    verifier's canonical key.

    Args:
        explicit: The ``--root`` value, or ``None``.

    Returns:
        The canonical project root string.

    Raises:
        RuntimeError: when no explicit root is given and the caller is not in a
            git repository.
    """
    if explicit:
        return canonicalize_root(explicit)
    return canonicalize_root(main_checkout_root())


# ---------------------------------------------------------------------------
# Lifecycle audit
# ---------------------------------------------------------------------------


def _append_lifecycle_audit(action: str, **detail: Any) -> None:
    """Append one JSON-lines entry to the append-only lifecycle audit log.

    The lifecycle audit is the daemon-operations analogue of the registration
    audit the registry module keeps: every ``start`` / ``stop`` / ``drain`` /
    ``install`` / ``upgrade`` adds exactly one line and no line is rewritten, so
    the daemon's operational history stays reconstructable. Written under the
    ``0700`` daemon state dir with ``0600`` mode.

    Args:
        action: The lifecycle action name.
        **detail: Extra fields to record on the audit line.
    """
    marshalld.ensure_daemon_dir()
    entry: dict[str, Any] = {
        'timestamp': now_utc_iso(),
        'action': action,
    }
    entry.update(detail)
    path = marshalld.daemon_dir() / _LIFECYCLE_AUDIT_FILENAME
    created = not path.exists()
    with open(path, 'a', encoding='utf-8') as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + '\n')
    if created and (path.stat().st_mode & 0o777) != _FILE_MODE:
        os.chmod(path, _FILE_MODE)


# ---------------------------------------------------------------------------
# Injectable OS seams (monkeypatched in tests)
# ---------------------------------------------------------------------------


def _resolve_daemon_command() -> tuple[list[str], dict[str, str], str]:
    """Build the version-pinned daemon launch command, env, and binary path.

    The daemon is pinned to the copy of :mod:`marshalld` co-located with THIS
    control skill (``Path(marshalld.__file__)``) — the same verified bundle /
    plugin-cache version that owns the control surface (S5). The child inherits
    the current process's import path via ``PYTHONPATH`` so the daemon's
    cross-skill imports resolve exactly as they do for this control script.

    Returns:
        A ``(command, env, binary_path)`` triple: the ``argv`` to launch the
        daemon (``run`` without ``--foreground`` so it double-forks), the child
        environment, and the resolved daemon binary path (reported by
        ``status`` / audited by ``start``).
    """
    binary_path = str(Path(marshalld.__file__).resolve())
    command = [sys.executable, binary_path, 'run']
    env = dict(os.environ)
    env['PYTHONPATH'] = os.pathsep.join(p for p in sys.path if p)
    return command, env, binary_path


def _spawn_detached(command: list[str], env: dict[str, str]) -> None:
    """Launch the daemon detached and reap the double-fork intermediate.

    :mod:`marshalld`'s ``run`` double-forks (the launched process forks, the
    intermediate ``setsid``+forks and exits, and the grandchild re-parents to
    PID 1), so the process this spawns exits almost immediately once the daemon
    has detached. The bounded ``wait`` reaps that intermediate rather than
    leaving a zombie; the daemon itself outlives this call under PID 1.

    Args:
        command: The daemon launch ``argv``.
        env: The child environment (carries ``PYTHONPATH``).
    """
    devnull = subprocess.DEVNULL
    proc = subprocess.Popen(
        command,
        env=env,
        stdin=devnull,
        stdout=devnull,
        stderr=devnull,
        start_new_session=True,
    )
    try:
        proc.wait(timeout=_SPAWN_REAP_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        # The intermediate did not exit in time — it is harmless (it will exit
        # after its own double-fork); do not block the control verb on it.
        pass


def _signal(pid: int, sig: int) -> None:
    """Send ``sig`` to ``pid``, tolerating an already-exited process."""
    try:
        os.kill(pid, sig)
    except ProcessLookupError:
        pass


def _ping(timeout: float = _PING_TIMEOUT_SECONDS) -> dict[str, Any] | None:
    """Ping the daemon over its socket, returning the response or ``None``.

    Opens a short-lived blocking connection to the ``0600`` socket, sends a
    ``ping`` request, and returns the decoded response payload. Any failure —
    the socket is absent, the connection is refused, the peer closes early, or a
    frame decode fails — returns ``None`` so the caller renders ``down``.

    Args:
        timeout: Socket connect / I/O timeout in seconds.

    Returns:
        The decoded ping response, or ``None`` when the daemon is unreachable.
        A current daemon answers with five keys — ``status`` (``'ok'``), ``pid``
        (``int``), ``version`` (``str``), ``in_flight`` (``int``) and ``queued``
        (``int``). ``in_flight`` and ``queued`` are NOT guaranteed: a daemon
        pinned to a copy predating the counts extension answers without them,
        and the running daemon's version is the only thing that decides which
        shape arrives. Callers MUST treat an absent count as *unreported*
        (see :func:`_reported_count`) rather than as zero — the two are
        different facts, and conflating them reports a busy daemon as idle.
    """
    sock_path = marshalld.socket_path()
    if not sock_path.exists():
        return None
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect(str(sock_path))
        send_frame(sock, {'op': 'ping'})
        return recv_frame(sock)
    except (OSError, FrameError):
        return None
    finally:
        sock.close()


def _reported_count(response: dict[str, Any], key: str) -> int | str:
    """Return a daemon-reported job count, or the ``unknown`` sentinel.

    Reports the count ONLY when the ping response actually carries it. A daemon
    older than the counts extension omits the key entirely, and that absence is
    reported as :data:`_UNKNOWN_COUNT` rather than coerced to ``0`` — so "the
    daemon did not tell us" stays distinguishable from "the daemon told us it is
    idle". The two were once the same value, and a reconcile read the resulting
    zero as idleness and drained a live build.

    Args:
        response: The decoded ping response.
        key: The count key to read (``in_flight`` or ``queued``).

    Returns:
        The count as an ``int``, or :data:`_UNKNOWN_COUNT` when the key is
        absent or its value is not an integer.
    """
    if key not in response:
        return _UNKNOWN_COUNT
    try:
        return int(response[key])
    except (TypeError, ValueError):
        return _UNKNOWN_COUNT


def _wait_for_exit(pid: int, grace: float) -> bool:
    """Poll until ``pid`` is gone or ``grace`` seconds elapse.

    Args:
        pid: The process to wait for.
        grace: Maximum seconds to wait.

    Returns:
        ``True`` when the process exited within the grace window, else ``False``.
    """
    deadline = time.monotonic() + grace
    while time.monotonic() < deadline:
        if not marshalld.pid_alive(pid):
            return True
        time.sleep(_POLL_INTERVAL_SECONDS)
    return not marshalld.pid_alive(pid)


def _running_pid() -> int | None:
    """Return the live daemon pid from the pidfile, or ``None`` when down."""
    pid = marshalld.read_pid(marshalld.pidfile_path())
    if pid is not None and marshalld.pid_alive(pid):
        return pid
    return None


def _cleanup_stale_state() -> None:
    """Remove the socket and pidfile after the daemon has exited."""
    marshalld.socket_path().unlink(missing_ok=True)
    marshalld.pidfile_path().unlink(missing_ok=True)


def _read_process_argv(pid: int) -> list[str] | None:
    """Return a live process's argv, or ``None`` when it cannot be read.

    The RUNNING daemon's provenance is read from the process itself — its own
    launch ``argv`` — never re-resolved at call time. The Linux fast path reads
    the exact NUL-separated ``argv`` from ``/proc/{pid}/cmdline``; on a platform
    without ``/proc`` (macOS) it falls back to ``ps -ww -p {pid} -o args=`` and
    whitespace-splits the reported command line.

    Args:
        pid: The live daemon pid (read back from the verified ``ping``).

    Returns:
        The process argv as a list of tokens, or ``None`` when neither source
        yields one (an empty read, a missing process, a ``ps`` failure) — which
        the caller renders as :data:`_UNKNOWN_PROVENANCE`.
    """
    proc_cmdline = Path('/proc') / str(pid) / 'cmdline'
    try:
        raw = proc_cmdline.read_bytes()
    except OSError:
        raw = b''
    if raw:
        parts = [chunk.decode('utf-8', 'replace') for chunk in raw.split(b'\x00') if chunk]
        if parts:
            return parts

    try:
        completed = subprocess.run(
            ['ps', '-ww', '-p', str(pid), '-o', 'args='],
            capture_output=True,
            text=True,
            timeout=_PS_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    line = completed.stdout.strip()
    if completed.returncode != 0 or not line:
        return None
    return line.split()


def _running_binary_path(pid: int) -> str | None:
    """Return the ``marshalld`` binary the live process ``pid`` is executing.

    Reads the RUNNING process's own argv (:func:`_read_process_argv`) and returns
    the single entry whose basename matches the daemon binary's filename — the
    binary the daemon is ACTUALLY executing, which after a plugin-cache bump is
    the older pinned copy, not the version a fresh import would resolve today.

    Fail closed: returns ``None`` (→ the caller renders
    :data:`_UNKNOWN_PROVENANCE`) when the argv cannot be read, or does not carry
    exactly one unambiguous ``marshalld`` entry, so an undeterminable provenance
    is NEVER silently replaced by the resolved-now path.

    Args:
        pid: The live daemon pid.

    Returns:
        The running daemon binary path, or ``None`` when it cannot be determined.
    """
    argv = _read_process_argv(pid)
    if not argv:
        return None
    target_name = Path(marshalld.__file__).name
    matches = [token for token in argv if token and Path(token).name == target_name]
    if len(matches) != 1:
        return None
    return matches[0]


# ---------------------------------------------------------------------------
# Registration verbs
# ---------------------------------------------------------------------------


def _default_worktree_containers(root: str) -> list[str]:
    """Return the default worktree container for ``root``.

    The canonical, platform-neutral worktree location every plan uses:
    ``<root>/.plan/local/worktrees``.

    Args:
        root: The canonical project root.

    Returns:
        A single-element list holding the canonical worktree container path.
    """
    return [str(Path(root) / '.plan' / 'local' / 'worktrees')]


def _effective_scope_value(
    explicit: list[str] | None,
    existing: dict[str, Any] | None,
    field: str,
    default: list[str],
) -> list[str]:
    """Resolve a scope field by precedence: explicit CLI > existing non-empty > default.

    The backfill/preserve policy that makes re-``register`` a safe repair path:
    an explicit CLI value always wins; otherwise a non-empty stored value is
    preserved (never wiped); otherwise the computed default backfills an empty or
    absent entry.

    Args:
        explicit: The repeatable CLI value (``--container`` / ``--notation``), or
            ``None`` when the operator supplied none.
        existing: The stored project record, or ``None`` when unregistered.
        field: The record field name to read the stored value from.
        default: The computed default to backfill when nothing else applies.

    Returns:
        The effective scope list.
    """
    if explicit:
        return list(explicit)
    if existing:
        stored = existing.get(field) or []
        if stored and isinstance(stored, list):
            return list(stored)
    return list(default)


def run_register(args: Namespace) -> dict[str, Any]:
    """Register (or update) a project in the machine-global registry.

    Upserts the project keyed by its canonical root via the shared registry
    module, which appends a registration audit line. This verb is the sole
    registration entry point — it lives only in this user-invocable control
    skill, never in a dispatch's ``skills[]`` (the S1 operator-interactivity
    wall).

    When the operator omits ``--container`` / ``--notation``, the scope fields
    are populated from canonical defaults — the routable build notations and the
    canonical worktree container (``<root>/.plan/local/worktrees``) — so a plain
    ``register`` yields a routable project rather than an inert empty-scope entry.
    Re-running ``register`` is the repair path: it backfills empty fields while
    preserving any non-empty stored values (precedence:
    explicit CLI value > existing non-empty stored value > computed default).
    """
    try:
        root = _resolve_root(args.root)
    except RuntimeError as exc:
        return make_error(str(exc), code=ErrorCode.NOT_FOUND)
    existing = get_project(read_registry(), root)
    worktree_containers = _effective_scope_value(
        args.container, existing, 'worktree_containers', _default_worktree_containers(root)
    )
    # The default allowlist is the routable build notations — the single source
    # of truth shared with the D5 routing seam, so a newly-added build tool
    # becomes routable AND default-allowlisted from one edit, with no drift.
    notation_allowlist = _effective_scope_value(
        args.notation, existing, 'notation_allowlist', list(routable_notations())
    )
    record = register_project(
        root,
        worktree_containers=worktree_containers,
        notation_allowlist=notation_allowlist,
    )
    return {
        'status': 'success',
        'action': 'register',
        'canonical_root': record['canonical_root'],
        'worktree_containers': record['worktree_containers'],
        'notation_allowlist': record['notation_allowlist'],
        'registered_at': record['registered_at'],
        'updated_at': record['updated_at'],
    }


def run_unregister(args: Namespace) -> dict[str, Any]:
    """Unregister a project from the machine-global registry.

    Removes the project keyed by its canonical root (appending an audit line
    when a record was present). Unregistering a project that was not registered
    is an idempotent no-op success (``removed: false``).
    """
    try:
        root = _resolve_root(args.root)
    except RuntimeError as exc:
        return make_error(str(exc), code=ErrorCode.NOT_FOUND)
    removed = unregister_project(root)
    return {
        'status': 'success',
        'action': 'unregister',
        'canonical_root': root,
        'removed': removed,
    }


# ---------------------------------------------------------------------------
# Lifecycle verbs
# ---------------------------------------------------------------------------


def _start_daemon() -> dict[str, Any]:
    """Start the version-pinned daemon, or report it already running.

    Shared by ``start`` and ``install``: refuses to launch a second daemon when
    one is already live (idempotent), otherwise cleans any stale socket/pidfile,
    spawns the verified daemon detached, and audits the start with the pinned
    binary path + version.
    """
    existing = _running_pid()
    if existing is not None:
        return {
            'status': 'success',
            'action': 'start',
            'running': True,
            'already_running': True,
            'pid': existing,
            'version': marshalld.VERSION,
        }
    _cleanup_stale_state()
    command, env, binary_path = _resolve_daemon_command()
    _spawn_detached(command, env)
    _append_lifecycle_audit('start', binary_path=binary_path, version=marshalld.VERSION)
    return {
        'status': 'success',
        'action': 'start',
        'running': True,
        'already_running': False,
        'binary_path': binary_path,
        'version': marshalld.VERSION,
    }


def run_start(_args: Namespace) -> dict[str, Any]:
    """Start the daemon detached, pinned to the verified bundle version (S5)."""
    return _start_daemon()


def run_install(_args: Namespace) -> dict[str, Any]:
    """Idempotent version-pinned start — a no-op when the daemon is already up."""
    result = _start_daemon()
    result['action'] = 'install'
    return result


def run_stop(_args: Namespace) -> dict[str, Any]:
    """Force-stop the daemon: ``SIGTERM`` then ``SIGKILL`` after a grace window.

    Sends ``SIGTERM``; if the daemon has not exited within
    :data:`_STOP_GRACE_SECONDS`, escalates to ``SIGKILL``. Cleans the socket and
    pidfile afterwards and audits the stop. Stopping an already-down daemon is an
    idempotent no-op success (``was_running: false``).
    """
    pid = _running_pid()
    if pid is None:
        _cleanup_stale_state()
        return {'status': 'success', 'action': 'stop', 'was_running': False}

    _signal(pid, signal.SIGTERM)
    forced = False
    if not _wait_for_exit(pid, _STOP_GRACE_SECONDS):
        _signal(pid, signal.SIGKILL)
        _wait_for_exit(pid, _STOP_GRACE_SECONDS)
        forced = True
    _cleanup_stale_state()
    _append_lifecycle_audit('stop', pid=pid, forced=forced)
    return {
        'status': 'success',
        'action': 'stop',
        'was_running': True,
        'pid': pid,
        'forced': forced,
    }


def run_drain(_args: Namespace) -> dict[str, Any]:
    """Gracefully stop the daemon (``SIGTERM`` + patient wait, no ``SIGKILL``).

    Requests a graceful shutdown and waits up to :data:`_DRAIN_GRACE_SECONDS`
    for the daemon to exit on its own, never escalating to ``SIGKILL``. Any job
    still in flight is recorded in the journal and replayed as ``killed`` on the
    next start (never silently lost). Draining an already-down daemon is an
    idempotent no-op success (``was_running: false``).
    """
    pid = _running_pid()
    if pid is None:
        _cleanup_stale_state()
        return {'status': 'success', 'action': 'drain', 'was_running': False}

    _signal(pid, signal.SIGTERM)
    exited = _wait_for_exit(pid, _DRAIN_GRACE_SECONDS)
    if exited:
        _cleanup_stale_state()
    _append_lifecycle_audit('drain', pid=pid, exited=exited)
    return {
        'status': 'success',
        'action': 'drain',
        'was_running': True,
        'pid': pid,
        'exited': exited,
    }


def run_upgrade(_args: Namespace) -> dict[str, Any]:
    """Drain the running daemon then start the verified version (S7).

    A version-pinned in-place upgrade: gracefully drain the current daemon, then
    launch the verified bundle copy. When no daemon is running the drain is a
    no-op and this reduces to a plain start.

    Reports two fields that can carry a FAILED upgrade, so a caller never has to
    infer success from the word ``success`` alone:

    * ``drain_exited`` — whether the old daemon actually exited within the drain
      grace window. ``False`` means the process the upgrade meant to replace is
      still alive. An upgrade with nothing to drain reports ``True``: there was
      no process that failed to exit.
    * ``already_running`` — whether the start half found a daemon still up. For
      an upgrade this is a failure signal, not an idempotent no-op: the drain was
      supposed to have removed it, so a live daemon here means the old one was
      never replaced.

    Either signal sets ``status: error`` with a ``reason``. Without them the verb
    reported ``success`` unconditionally and its caller cleared a reconcile-owed
    marker on that word alone.
    """
    drain_result = run_drain(_args)
    start_result = _start_daemon()
    # Absent `exited` means the drain had no daemon to wait for, which is not a
    # failure — nothing was left running.
    drain_exited = bool(drain_result.get('exited', True))
    already_running = bool(start_result.get('already_running', False))
    _append_lifecycle_audit(
        'upgrade',
        drained=drain_result.get('was_running', False),
        version=marshalld.VERSION,
    )
    result: dict[str, Any] = {
        'status': 'success',
        'action': 'upgrade',
        'drained': drain_result.get('was_running', False),
        'drain_exited': drain_exited,
        'already_running': already_running,
        'running': start_result.get('running', False),
        'binary_path': start_result.get('binary_path'),
        'version': marshalld.VERSION,
    }
    if not drain_exited:
        result['status'] = 'error'
        result['reason'] = 'drain_did_not_exit'
    elif already_running:
        result['status'] = 'error'
        result['reason'] = 'already_running_after_drain'
    return result


def run_status(_args: Namespace) -> dict[str, Any]:
    """Report the daemon's running state, RUNNING provenance, and idleness (S5, D4).

    Pings the daemon over its ``0600`` socket. On a successful handshake reports
    ``running: true`` with the daemon-reported version + pid, the daemon's
    in-flight / queued job counts — reported as ``unknown`` when the daemon did
    not send them, so a daemon predating the counts extension is never rendered
    as an idle one — and — this is the D4 truthfulness fix — the
    binary the RUNNING process is actually executing (``running_binary_path``,
    sourced from the live process, not a call-time re-resolution) ALONGSIDE the
    resolved-now path a fresh start would use (``resolved_binary_path``). When the
    two differ the daemon is stale; ``binary_diverges`` says so explicitly and a
    ``note`` spells the divergence out, rather than showing one path as if it were
    the other. When the running provenance cannot be determined it is reported as
    ``unknown`` — NEVER the resolved-now path, which is the exact substitution that
    once rendered nineteen versions of drift as a clean status line.

    When the daemon is unreachable reports ``running: false`` with a named reason
    (``no_pidfile`` when nothing claims to run, ``unreachable`` when a pid is
    recorded but the socket does not answer). Also reports whether the caller's
    project is registered, so the operator sees enrolment and liveness in one call.
    """
    _, _, resolved_binary_path = _resolve_daemon_command()
    registry = read_registry()
    try:
        caller_root = canonicalize_root(main_checkout_root())
        registered = find_project_for_root(registry, caller_root) is not None
    except RuntimeError:
        caller_root = ''
        registered = False

    response = _ping()
    if response is not None and response.get('status') == 'ok':
        pid = response.get('pid')
        running_binary_path = _running_binary_path(pid) if isinstance(pid, int) else None
        diverges = running_binary_path is not None and running_binary_path != resolved_binary_path
        result: dict[str, Any] = {
            'status': 'success',
            'action': 'status',
            'running': True,
            'version': response.get('version', ''),
            'pid': pid,
            # The RUNNING daemon's provenance, from the live process. `unknown`
            # (never the resolved path) when it cannot be read — fail-closed.
            'running_binary_path': running_binary_path
            if running_binary_path is not None
            else _UNKNOWN_PROVENANCE,
            # The resolve-now path: which binary a fresh start would launch today.
            'resolved_binary_path': resolved_binary_path,
            'binary_diverges': diverges,
            # Reported only when the daemon actually sent them; an absent count
            # is `unknown`, NEVER 0 — see `_reported_count`.
            'in_flight': _reported_count(response, 'in_flight'),
            'queued': _reported_count(response, 'queued'),
            'socket_path': str(marshalld.socket_path()),
            'caller_root': caller_root,
            'registered': registered,
        }
        if diverges:
            result['note'] = (
                f'running daemon is STALE: it is executing {running_binary_path}, but a fresh '
                f'start would resolve {resolved_binary_path}'
            )
        elif running_binary_path is None:
            result['note'] = (
                'running daemon provenance is unknown (could not read the live process argv); '
                'the resolved-now path is NOT substituted for it'
            )
        return result

    reason = 'no_pidfile' if _running_pid() is None else 'unreachable'
    return {
        'status': 'success',
        'action': 'status',
        'running': False,
        'reason': reason,
        # No running process to read provenance from — report only the resolve-now
        # path, explicitly named so it is never misread as the running binary.
        'resolved_binary_path': resolved_binary_path,
        'socket_path': str(marshalld.socket_path()),
        'caller_root': caller_root,
        'registered': registered,
    }


# ---------------------------------------------------------------------------
# Audit-inspection verb (read-only)
# ---------------------------------------------------------------------------


def _render_audit_record(record: dict[str, Any], fates: dict[str, str]) -> dict[str, Any]:
    """Render one stored audit row into the explicit operator-view shape.

    Every rendered row leads with an explicit ``kind`` label, so an interaction
    row can never be read as a job record. An interaction row presents its
    request-scoped ``request_status`` (how the REQUEST was answered) and the
    job's ``fate`` as two separate columns — the fate is joined by ``job_id``
    from the job-fate rows in the same 7-day store.

    Fail-closed (ADR-009): a row written by an older daemon that predates these
    field names, or a job with no fate record yet, renders an explicit
    ``unknown`` rather than a silently missing field. ``unknown`` is never a
    terminal status and never the request-scoped ``queued``.

    Args:
        record: One stored audit row.
        fates: The ``job_id`` → ``fate`` map derived from the job-fate rows.

    Returns:
        The rendered row.
    """
    job_id = str(record.get('job_id', ''))
    if record.get('kind') == KIND_JOB_FATE:
        return {
            'kind': KIND_JOB_FATE,
            'job_id': job_id,
            'project_root': record.get('project_root', ''),
            'plan_id': record.get('plan_id', ''),
            'fate': record.get('fate', FATE_UNKNOWN),
            'timestamp': record.get('timestamp', ''),
        }
    rendered = {
        'kind': KIND_INTERACTION,
        'op': record.get('op', ''),
        'job_id': job_id,
        'project_root': record.get('project_root', ''),
        'plan_id': record.get('plan_id', ''),
        'request_status': record.get('request_status', FATE_UNKNOWN),
        'fate': fates.get(job_id, FATE_UNKNOWN),
        'timestamp': record.get('timestamp', ''),
    }
    reason = record.get('reason')
    if reason is not None:
        rendered['reason'] = reason
    return rendered


def run_logs(args: Namespace) -> dict[str, Any]:
    """Show the caller project's interaction-audit records (read-only, derived view).

    Resolves the caller's canonical root (``--root`` override, else the main
    checkout), reads the central ``interaction-audit.log`` through the
    :class:`InteractionAudit` reader, and returns the records whose
    ``project_root`` matches the caller — the derived project-scoped view,
    rendered through :func:`_render_audit_record` so each row's kind, its
    request-scoped status, and the job's fate are three distinct columns. The
    verb NEVER mutates the log.

    Fail-closed (ADR-9): when the log is absent or unreadable the verb returns an
    explicit empty ``records`` list with a named ``reason`` (``log_absent`` /
    ``log_unreadable``), never a fabricated success that hides a read failure. A
    present log with no matching records is a legitimate empty view (no reason).

    Args:
        args: Parsed args carrying ``--root`` and ``--limit``.

    Returns:
        The TOON result with the project-scoped ``records`` tail.
    """
    try:
        root = _resolve_root(args.root)
    except RuntimeError as exc:
        return make_error(str(exc), code=ErrorCode.NOT_FOUND)

    limit = args.limit if args.limit is not None else _DEFAULT_LOGS_LIMIT
    audit = InteractionAudit()

    if not audit.path.exists():
        return {
            'status': 'success',
            'action': 'logs',
            'caller_root': root,
            'count': 0,
            'records': [],
            'reason': 'log_absent',
        }
    # read_records_or_none() is the single read+parse choke point: it returns None
    # when the log is present but unreadable/corrupt (OSError OR UnicodeDecodeError,
    # the latter not an OSError subclass), distinct from an empty [] for a
    # present-but-empty log. A corrupt log therefore fails closed to an explicit
    # log_unreadable reason here — never a crash, never a fabricated success that
    # hides the read failure (ADR-9). gc()/read_all() collapse the same None to []
    # so daemon startup stays crash-safe.
    all_records = audit.read_records_or_none()
    if all_records is None:
        return {
            'status': 'success',
            'action': 'logs',
            'caller_root': root,
            'count': 0,
            'records': [],
            'reason': 'log_unreadable',
        }

    scoped = [record for record in all_records if record.get('project_root') == root]
    # Build the job_id -> fate map from EVERY project-scoped row, not just the
    # tail: a job's fate row can fall outside the --limit window while the
    # interaction row it belongs to is still rendered.
    fates = {
        str(record.get('job_id', '')): str(record.get('fate', FATE_UNKNOWN))
        for record in scoped
        if record.get('kind') == KIND_JOB_FATE and record.get('job_id')
    }
    tail = scoped[-limit:] if limit > 0 else scoped
    return {
        'status': 'success',
        'action': 'logs',
        'caller_root': root,
        'count': len(tail),
        'total_matched': len(scoped),
        'records': [_render_audit_record(record, fates) for record in tail],
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_arg_parser() -> argparse.ArgumentParser:
    """Build the control-skill argparse surface."""
    parser = argparse.ArgumentParser(
        prog='manage_build_server',
        description='Operator control surface for the marshalld build server.',
        allow_abbrev=False,
    )
    sub = parser.add_subparsers(dest='command', required=True)

    register = sub.add_parser('register', help='Enrol a project (the enable signal).', allow_abbrev=False)
    register.add_argument('--root', help='Project root (default: caller main checkout).')
    register.add_argument(
        '--container',
        action='append',
        help='Worktree container directory (repeatable).',
    )
    register.add_argument(
        '--notation',
        action='append',
        help='Allowed executor notation (repeatable).',
    )
    register.set_defaults(func=run_register)

    unregister = sub.add_parser('unregister', help='Drop a project from the registry.', allow_abbrev=False)
    unregister.add_argument('--root', help='Project root (default: caller main checkout).')
    unregister.set_defaults(func=run_unregister)

    sub.add_parser('start', help='Start the daemon detached (version-pinned).', allow_abbrev=False).set_defaults(
        func=run_start
    )
    sub.add_parser('stop', help='Force-stop the daemon (SIGTERM then SIGKILL).', allow_abbrev=False).set_defaults(
        func=run_stop
    )
    sub.add_parser('drain', help='Gracefully stop the daemon (no SIGKILL).', allow_abbrev=False).set_defaults(
        func=run_drain
    )
    sub.add_parser(
        'status',
        help=(
            'Report running version, in-flight/queued counts (unknown when the daemon did not '
            'send them, never 0), and running-vs-resolved binary provenance (divergence flagged; '
            'unknown never the resolved path).'
        ),
        allow_abbrev=False,
    ).set_defaults(func=run_status)
    sub.add_parser('install', help='Idempotent version-pinned start.', allow_abbrev=False).set_defaults(
        func=run_install
    )
    sub.add_parser('upgrade', help='Drain then start the verified version.', allow_abbrev=False).set_defaults(
        func=run_upgrade
    )

    logs = sub.add_parser(
        'logs',
        help="Show this project's interaction-audit records (read-only).",
        allow_abbrev=False,
    )
    logs.add_argument('--root', help='Project root (default: caller main checkout).')
    logs.add_argument(
        '--limit',
        type=int,
        help=(
            'Return the N most recent records (records are ordered oldest-first '
            f'within the returned window). Default: {_DEFAULT_LOGS_LIMIT}.'
        ),
    )
    logs.set_defaults(func=run_logs)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point — dispatch a control verb and print its TOON result."""
    args = _build_arg_parser().parse_args(argv)
    return print_toon(args.func(args))


if __name__ == '__main__':
    safe_main(main)()
