#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""manage-build-server — the operator control surface for ``marshalld``.

Notation: ``plan-marshall:manage-build-server:manage_build_server``

This is the user-invocable control skill's executor: the deterministic verbs the
operator drives to enrol a project and manage the machine-global build-server
daemon. It is the **operator-interactivity wall** (S1) — ``register`` /
``unregister`` write the machine-global ``registry.json`` and live ONLY here,
never in a dispatch's ``skills[]``, so a plan can never launder itself onto the
served set. The daemon is strictly opt-in: registration IS the enable signal —
there is no config knob that turns the daemon on and nothing git-tracked that
does. That statement is about the ENABLE signal specifically; the build-slot cap
does have a machine-wide setting, reached through the ``config`` verbs below and
stored in the machine-global ``machine-config.json`` (host state, still nothing
git-tracked).

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
  daemon did not send them — never ``0``, which would read as idle), the
  build-slot cap the RUNNING daemon is applying with its ``max_slots_source``
  (``unknown`` for a daemon predating the cap fields; an ``invalid`` or
  ``unreadable`` source also gets a ``max_slots_warning`` line), and the
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
* ``config get`` — report the machine-global build-slot cap with its source and
  path, plus the caller project's per-repo ``build.queue.max_slots``: ``absent``,
  or its value together with ``in_effect: false``. Read-only.
* ``config set --max-slots N`` — set the machine-global cap. The unconditional
  writer, and therefore the only verb that can repair an invalid or unreadable
  machine-config value. A running daemon applies it on its next submit.
* ``config migrate`` — move the caller repository's ``build.queue.max_slots`` to
  its machine-global home in one step. It copies the value ONLY when nothing is
  set machine-wide, then removes the per-repo key; when the two values differ it
  changes NEITHER file and reports both. It never picks a winner — a per-caller
  cap over one shared queue is a disagreement to surface, not to silently
  resolve.

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
from _machine_config import (
    SOURCE_DEFAULT,
    SOURCE_INVALID,
    SOURCE_MACHINE_CONFIG,
    SOURCE_UNREADABLE,
    CapResolution,
    MachineConfigPostCommitError,
    read_per_repo_max_slots,
    report_safe,
    resolve_max_slots,
    write_max_slots,
    write_max_slots_if_unset,
)
from _marshalld_audit import (
    FATE_UNKNOWN,
    KIND_INTERACTION,
    KIND_JOB_FATE,
    InteractionAudit,
)
from file_ops import get_marshal_path, now_utc_iso
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

_UNREPORTED = 'unknown'
"""Sentinel ``status`` reports for any field the RUNNING daemon did not send.

A daemon pinned to an older copy answers ``ping`` with fewer keys than the
current one does, and the running daemon's version is the only thing that decides
which shape arrives. Every such absence renders as this sentinel rather than as a
plausible substitute value, because the substitute is always indistinguishable
from a real reading:

* ``in_flight`` / ``queued`` — coercing an absent count to ``0`` makes a daemon
  that said nothing indistinguishable from one that said it is idle, which is
  precisely what once let a reconcile drain a live build.
* ``max_slots`` / ``max_slots_source`` — filling these in from a local resolve
  would report what a FRESH daemon would apply as though it were what the running
  one is applying, the same substitution ``running_binary_path`` refuses to make
  for provenance."""

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
        A current daemon answers with ``status`` (``'ok'``), ``pid`` (``int``),
        ``version`` (``str``), ``in_flight`` (``int``), ``queued`` (``int``),
        ``max_slots`` (``int``) and ``max_slots_source`` (``str``), plus
        ``max_slots_detail`` when that source is not ``machine_config``.

        Only ``status``, ``pid`` and ``version`` are guaranteed: a daemon pinned
        to a copy predating the counts extension answers without the counts, and
        one predating the cap-reporting extension answers without the cap fields.
        The RUNNING daemon's version is the only thing that decides which shape
        arrives. Callers MUST treat every absent field as *unreported* (see
        :func:`_reported_int` / :func:`_reported_text`) rather than substituting a
        plausible value — an absent count is not zero, and an absent cap is not
        whatever a local resolve would return now.
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


def _reported_int(response: dict[str, Any], key: str) -> int | str:
    """Return a daemon-reported integer field, or the ``unknown`` sentinel.

    Reports the number ONLY when the ping response actually carries it. A daemon
    older than the extension that added the key omits it entirely, and that
    absence is reported as :data:`_UNREPORTED` rather than coerced to ``0`` — so
    "the daemon did not tell us" stays distinguishable from "the daemon told us
    zero". For the job counts the two were once the same value, and a reconcile
    read the resulting zero as idleness and drained a live build; for the slot cap
    a zero would read as a daemon that can admit nothing at all.

    Args:
        response: The decoded ping response.
        key: The integer key to read (``in_flight``, ``queued``, ``max_slots``).

    Returns:
        The value as an ``int``, or :data:`_UNREPORTED` when the key is absent or
        its value is not an integer.
    """
    if key not in response:
        return _UNREPORTED
    try:
        return int(response[key])
    except (TypeError, ValueError):
        return _UNREPORTED


def _reported_text(response: dict[str, Any], key: str) -> str:
    """Return a daemon-reported string field, or the ``unknown`` sentinel.

    The string counterpart of :func:`_reported_int`, for ``max_slots_source``.
    The source is the field that makes the cap auditable — it is what separates a
    configured cap from one that degraded to the default — so a daemon that did
    not send it must render as :data:`_UNREPORTED` and never as a guessed source.
    An empty string is treated as unreported too: a source is a named member of a
    closed set, and the empty string is not one of them.

    Args:
        response: The decoded ping response.
        key: The string key to read.

    Returns:
        The reported value, or :data:`_UNREPORTED` when the key is absent, not a
        string, or empty.
    """
    value = response.get(key)
    if not isinstance(value, str) or not value:
        return _UNREPORTED
    return value


def _cap_source_warning(response: dict[str, Any]) -> str | None:
    """Return a ``WARNING`` line for a degraded cap source, else ``None``.

    The running daemon is admitting against :data:`_machine_config.DEFAULT_MAX_SLOTS`
    while a cap it could not use sits in the machine-global config — either
    mistyped (:data:`SOURCE_INVALID`) or unreachable (:data:`SOURCE_UNREADABLE`).
    Reporting the value and the source is what makes that state VISIBLE, but an
    operator scanning a status block reads a line that says WARNING long before
    they read a source field, so the degradation gets one.

    Only those two sources warn. :data:`SOURCE_MACHINE_CONFIG` is nominal, and
    ``default`` is a legitimate unconfigured state, not a fault — warning on it
    would train the operator to ignore the line. An unreported source warns
    nothing either: nothing is known about it, and a warning would be a claim.

    Args:
        response: The decoded ping response.

    Returns:
        The warning line, carrying the daemon's ``max_slots_detail`` when it sent
        one, or ``None`` when the source is nominal, absent, or unreported.
    """
    source = _reported_text(response, 'max_slots_source')
    if source not in (SOURCE_INVALID, SOURCE_UNREADABLE):
        return None
    detail = response.get('max_slots_detail')
    applied = _reported_int(response, 'max_slots')
    suffix = f' ({detail})' if detail else ''
    return (
        f'WARNING: the running daemon could not use the configured build-slot cap '
        f'(max_slots_source={source}){suffix}. It is admitting against the fallback '
        f'{applied}. Repair it with `config set --max-slots N`.'
    )


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

    Either signal sets ``status: error``. Without them the verb reported
    ``success`` unconditionally and its caller cleared a reconcile-owed marker on
    that word alone.

    The failure payload carries the full shared error shape — ``error`` (the
    machine-readable code) and ``message`` (a human-readable sentence naming what
    failed) from ``ref-workflow-architecture/standards/manage-contract.md``,
    alongside the ``reason`` this verb has always reported. ``reason`` is kept
    because ``reconcile_daemon._reconcile_failure`` and the operator surface in
    ``SKILL.md`` read it; ``error`` and ``message`` are added because a payload
    that survives to a contract-aware consumer (``print_toon`` exits 0, so
    ``_invoke_executor`` hands the whole dict on) must be decodable by one. Both
    error branches set the three fields from a single place, so the code can
    never drift from the reason.
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

    def _fail(code: str, message: str) -> None:
        """Stamp the full error shape from ONE place, so ``error`` cannot drift."""
        result['status'] = 'error'
        result['reason'] = code
        result['error'] = code
        result['message'] = message

    if not drain_exited:
        _fail(
            'drain_did_not_exit',
            f'The running daemon (pid {drain_result.get("pid")}) did not exit within the '
            f'{_DRAIN_GRACE_SECONDS}s drain window; the process this upgrade meant to '
            f'replace is still alive, so version {marshalld.VERSION} did not take over.',
        )
    elif already_running:
        _fail(
            'already_running_after_drain',
            'A daemon was already running when the upgrade tried to start version '
            f'{marshalld.VERSION}; the drain reported a clean exit, so the old daemon '
            'was never actually replaced.',
        )
    return result


def run_status(_args: Namespace) -> dict[str, Any]:
    """Report the daemon's running state, RUNNING provenance, and idleness (S5, D4).

    Pings the daemon over its ``0600`` socket. On a successful handshake reports
    ``running: true`` with the daemon-reported version + pid, the daemon's
    in-flight / queued job counts — reported as ``unknown`` when the daemon did
    not send them, so a daemon predating the counts extension is never rendered
    as an idle one — the build-slot cap the RUNNING daemon is applying together
    with ``max_slots_source``, the provenance that separates a configured cap from
    one that degraded to the default (both ``unknown`` when the daemon predates
    the cap-reporting extension, and a degraded source additionally gets a
    ``max_slots_warning`` line) — and — this is the D4 truthfulness fix — the
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
            'running_binary_path': running_binary_path if running_binary_path is not None else _UNKNOWN_PROVENANCE,
            # The resolve-now path: which binary a fresh start would launch today.
            'resolved_binary_path': resolved_binary_path,
            'binary_diverges': diverges,
            # Reported only when the daemon actually sent them; an absent count
            # is `unknown`, NEVER 0 — see `_reported_int`.
            'in_flight': _reported_int(response, 'in_flight'),
            'queued': _reported_int(response, 'queued'),
            # The cap the RUNNING daemon is applying, and where it came from.
            # Both from the ping — never re-resolved here, because a local
            # resolve answers "what would a fresh daemon apply", a different
            # question. An older daemon sends neither and both read `unknown`.
            'max_slots': _reported_int(response, 'max_slots'),
            'max_slots_source': _reported_text(response, 'max_slots_source'),
            'socket_path': str(marshalld.socket_path()),
            'caller_root': caller_root,
            'registered': registered,
        }
        cap_warning = _cap_source_warning(response)
        if cap_warning is not None:
            result['max_slots_warning'] = cap_warning
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
# Machine-global build-slot cap (config get / set / migrate)
# ---------------------------------------------------------------------------


def _cap_report(cap: CapResolution) -> dict[str, Any]:
    """Render a :class:`CapResolution` as the machine-global cap report fields.

    ``max_slots_source`` and ``max_slots_detail`` ride along unconditionally,
    including a ``None`` detail on a nominal resolution: the operator surface is
    a report, and a key that appears only sometimes is one a reader learns to
    stop looking for. The VALUE alone can never distinguish a configured 5 from
    a fallback 5, which is why the source is not optional here.
    """
    return {
        'max_slots': cap.value,
        'max_slots_source': cap.source,
        'max_slots_detail': cap.detail,
        'path': cap.path,
    }


def _per_repo_report() -> dict[str, Any]:
    """Report the caller project's per-repo cap key, which never takes effect.

    Reads the CALLER's own ``marshal.json`` through the cwd-relative
    :func:`file_ops.get_marshal_path` — the same "the caller's repo" question
    ``config migrate`` asks, and deliberately NOT the cwd-independent resolver
    the cap itself uses.

    The reported ``value`` passes through :func:`_machine_config.report_safe`
    first. The read is raw by contract — the report must echo what is actually
    written — but the EMISSION is a single-line TOON field, and a newline in a
    config this process did not write would land at column zero where a consumer
    parses it as a sibling key of this very envelope.

    Returns:
        ``{'per_repo_max_slots': 'absent', ...}`` when no key is present, else
        the ``value`` together with ``in_effect: False`` — stated explicitly
        rather than implied, so a reader of the report cannot mistake a reported
        value for an operative one.
    """
    marshal_path = get_marshal_path()
    raw = read_per_repo_max_slots(marshal_path)
    if raw is None:
        return {'per_repo_max_slots': 'absent', 'marshal_json_path': str(marshal_path)}
    return {
        'per_repo_max_slots': {'value': report_safe(raw), 'in_effect': False},
        'marshal_json_path': str(marshal_path),
    }


def run_config_get(_args: Namespace) -> dict[str, Any]:
    """Report the machine-global build-slot cap and the caller's demoted key.

    Read-only: it writes neither file. The two halves are reported together
    because that pairing IS the operator's question — "what cap am I running
    under, and is the key in my repository doing anything?" — and answering only
    one half is what leaves an operator editing an inert key.
    """
    return {
        'status': 'success',
        'action': 'config get',
        **_cap_report(resolve_max_slots()),
        **_per_repo_report(),
    }


def run_config_set(args: Namespace) -> dict[str, Any]:
    """Set the machine-global build-slot cap to ``--max-slots N``.

    Rejects anything that cannot be a cap — a non-positive int, a non-int, and a
    ``bool`` (argparse ``type=int`` already excludes the latter two from the CLI,
    but the validation lives in the writer so an in-process caller is held to the
    same contract). This is the UNCONDITIONAL writer: it replaces whatever is
    there, which is also what makes it the only verb that can repair an invalid
    or unreadable machine-config value.

    The reported resolution is re-read from disk after the write, so the operator
    sees what was actually persisted rather than what was requested.
    """
    try:
        cap = write_max_slots(args.max_slots)
    except ValueError as exc:
        return make_error(str(exc), code=ErrorCode.INVALID_INPUT, action='config set')
    except TimeoutError as exc:
        return make_error(str(exc), code=ErrorCode.TIMEOUT, action='config set')
    except OSError as exc:
        # The write touches the filesystem at four points — the ``0o700`` state-dir
        # mkdir, the ``O_EXCL`` guard, the atomic temp-file replace, and the
        # ``chmod`` — so a read-only home root, a permission change under the
        # state dir, or a full disk surfaces HERE rather than as one of the two
        # arms above. Callers read the outcome from the payload ``status``, never
        # from the exit code, so letting this propagate as a traceback would break
        # the TOON envelope contract every verb on this surface is held to; a
        # louder failure is not the same thing as a reported one.
        #
        # No ``ErrorCode`` member names "the write itself failed" and borrowing
        # one that means something else would misroute it, so the named ``reason``
        # is the routing key — the same choice :func:`_remove_per_repo_max_slots`
        # makes for its guard refusal, and the same ``reason`` value the migrate
        # path already reports for a failed machine-global write.
        #
        # Ordered AFTER ``TimeoutError``, which is an ``OSError`` subclass: the
        # specific arm must be reachable, or every guard timeout would be
        # reclassified as a write failure and lose its ``TIMEOUT`` code.
        return make_error(str(exc), action='config set', reason='machine_config_write_failed')
    return {
        'status': 'success',
        'action': 'config set',
        **_cap_report(cap),
        'note': (
            'A running daemon applies the new cap on its next submit — it re-resolves '
            'the cap per submit, so no restart is required.'
        ),
    }


def _remove_per_repo_max_slots() -> dict[str, Any]:
    """Delete ONLY ``build.queue.max_slots`` from the caller's ``marshal.json``.

    Writes through :mod:`_config_core`'s own :func:`load_config` /
    :func:`save_config` — the writer ``manage-providers`` and ``marshall-steward
    upgrade`` already use from outside ``manage-config`` — so the canonical
    top-level key order and the concurrent-modification fingerprint guard both
    apply and NO second ``marshal.json`` writer is introduced.

    The import is deliberately deferred into this function: ``_config_core``
    binds ``MARSHAL_PATH`` at import time, so importing it at module scope would
    make every OTHER verb in this script depend on a resolvable ``marshal.json``
    — and ``register`` / ``start`` / ``status`` must keep working in a checkout
    that has none.

    ``max_retries`` and every other key in the ``build.queue`` block survive, as
    does the block itself: the demotion is of ONE key, not of the queue's config.

    Returns:
        ``{'status': 'success'}`` on a committed removal, else an error payload
        naming ``concurrent_modification`` — the guard refusing to clobber a
        concurrent writer, which is recoverable by re-running, not a crash.
    """
    from _config_core import (
        ConcurrentConfigModificationError,
        load_config,
        save_config,
    )

    config = load_config()
    queue = config.get('build', {}).get('queue')
    if isinstance(queue, dict):
        queue.pop('max_slots', None)
    try:
        save_config(config)
    except ConcurrentConfigModificationError as exc:
        # No ErrorCode member names "a guard declined to clobber a concurrent
        # writer", and borrowing a member that means something else would route
        # this to the wrong handler. The named `reason` IS the routing key here.
        return make_error(str(exc), reason='concurrent_modification')
    return {'status': 'success'}


def _migrate_refused(reason: str, message: str, **extra: Any) -> dict[str, Any]:
    """Build a ``refused`` payload — nothing was mutated on either side.

    Every refusal is reported with BOTH files untouched, which is the verb's
    central guarantee: a migration that cannot pick a winner must not leave the
    operator half-migrated, so it declines rather than choosing.
    """
    # No `code=`: a refusal is a well-typed outcome of this verb, not a generic
    # failure, and the `outcome` / `reason` pair is what a caller branches on.
    # Borrowing an ErrorCode member that means something else would misroute it.
    return make_error(
        message,
        action='config migrate',
        outcome='refused',
        reason=reason,
        machine_config_modified=False,
        marshal_json_modified=False,
        **extra,
    )


def _migrate_committed_report(
    exc: BaseException, per_repo_value: int, marshal_path: str, post: CapResolution
) -> dict[str, Any]:
    """Report the COMMITTED-then-failed write as ``partial``, on the marker's evidence.

    Reached only with :class:`MachineConfigPostCommitError` in hand, so
    ``machine_config_modified=True`` is a claim about THIS invocation backed by
    the writer's own marker — not by a post-state that any other writer could
    have produced. The per-repo key was not removed, which is exactly the
    recoverable half-state a re-run completes through the equal-values
    ``removed_duplicate`` branch.

    The detail — not the outcome — is what branches on the re-read, because the
    marker settles authorship while only the re-read can say what the machine
    side holds NOW: the guard was released before this report ran, so a
    concurrent writer may have replaced the just-committed value. Naming this
    repository's value over such a state would be a second untrue claim riding
    on a true one.
    """
    if post.source == SOURCE_MACHINE_CONFIG and post.value == per_repo_value:
        detail = (
            f'the machine-global write LANDED — {post.path} holds build.queue.max_slots={post.value} — but the '
            f'call then failed, so build.queue.max_slots is STILL present in {marshal_path} and was NOT '
            'removed. Re-run config migrate to complete the migration through the removed_duplicate branch.'
        )
    else:
        detail = (
            f'the machine-global write LANDED — this invocation committed build.queue.max_slots={per_repo_value} '
            f'to {post.path} — but the call then failed, and the machine side no longer reads back as that value '
            f'(source={post.source}, value={post.value}), so another writer has changed it since. '
            f'build.queue.max_slots is STILL present in {marshal_path} and was NOT removed. Inspect {post.path}, '
            'then re-run config migrate.'
        )
    return make_error(
        str(exc),
        action='config migrate',
        outcome='partial',
        reason='machine_config_write_failed_after_commit',
        machine_config_modified=True,
        marshal_json_modified=False,
        detail=detail,
        **_cap_report(post),
        marshal_json_path=marshal_path,
    )


def _migrate_uncommitted_report(
    exc: BaseException, per_repo_value: int, marshal_path: str, post: CapResolution
) -> dict[str, Any]:
    """Report a write that raised with NO commit evidence — ``refused`` or ``undetermined``.

    Reached when the raising write carried no
    :class:`MachineConfigPostCommitError`, so every pre-replace failure point
    lands here: the state-dir ``mkdir``, the ``O_EXCL`` guard's timeout, and the
    temp-file write inside ``atomic_write_file``. None of them committed
    anything, and this invocation therefore has nothing to claim authorship of.

    * The machine side is still unset (:data:`SOURCE_DEFAULT`) ⇒ ``refused``,
      verbatim and with both modification fields ``False``. Nothing committed and
      nothing is there, so the refusal is TRUE here and must not be weakened.
    * Any other post-state ⇒ ``undetermined`` — **including a
      :data:`SOURCE_MACHINE_CONFIG` that equals this repository's value.** That
      equality is not authorship: the guard is released in
      :func:`write_max_slots_if_unset`'s ``finally`` before the exception reaches
      the caller, so between the raise and this re-read another writer may have
      installed the same value (a concurrent ``config migrate``, or the
      ``config set --max-slots`` the not-in-effect warning prescribes). Claiming
      ``partial`` on it reported a commit this invocation never made.
    * ``undetermined`` OMITS ``machine_config_modified`` and
      ``marshal_json_modified`` entirely — a ``false`` there would read as the
      ``refused`` both-files-untouched guarantee and a ``true`` as ``partial``,
      so the absence of the keys is the report, exactly as the absent
      ``residual_count`` is on an unmeasurable scope-creep guard.
    """
    if post.source == SOURCE_DEFAULT:
        return _migrate_refused(
            'machine_config_write_failed',
            f'refusing to migrate: the machine-global write did not happen ({exc}). Neither file was changed.',
            marshal_json_path=marshal_path,
            per_repo_max_slots=per_repo_value,
        )

    if post.source == SOURCE_MACHINE_CONFIG and post.value == per_repo_value:
        detail = (
            f'the machine-global write raised without committing, so this invocation has NO evidence that it wrote '
            f"anything — yet {post.path} now holds build.queue.max_slots={post.value}, this repository's own "
            f'value. Another writer may have installed it (a concurrent config migrate, or the '
            f'`config set --max-slots` the not-in-effect warning prescribes), so this report claims NEITHER that '
            f'this migration landed NOR that both files are untouched. build.queue.max_slots is still present in '
            f'{marshal_path} — re-run config migrate, which converges through the removed_duplicate branch.'
        )
    else:
        detail = (
            f'the machine-global write failed and the machine-global state at {post.path} could not be established '
            f'afterwards (source={post.source}, detail={post.detail}). It is therefore UNKNOWN whether the cap was '
            f'written: this report claims neither that the migration partly landed nor that both files are '
            f'untouched. Inspect {post.path}, then re-run config migrate — build.queue.max_slots is still present '
            f'in {marshal_path}.'
        )

    return make_error(
        str(exc),
        action='config migrate',
        outcome='undetermined',
        reason='machine_config_state_undetermined',
        detail=detail,
        **_cap_report(post),
        marshal_json_path=marshal_path,
        per_repo_max_slots=per_repo_value,
    )


def _migrate_write_failure_report(
    exc: BaseException, per_repo_value: int, marshal_path: str, *, committed: bool
) -> dict[str, Any]:
    """Report a raising machine-global write from the writer's own commit evidence.

    The write is NOT all-or-nothing from this caller's point of view.
    :func:`_machine_config._write_cap_unguarded` commits the atomic replace and
    THEN stats and chmods the committed file, so an ``OSError`` from either of
    those two post-replace calls arrives with the migrated cap **already on
    disk**. Reporting that as ``refused`` asserted "Neither file was changed"
    over an already-migrated machine config — a false refusal, which is the same
    untrue-signal class as a false success and worse than a bare traceback,
    because it states a condition that does not hold.

    Whether the value landed is decided by ``committed`` — the caller's test for
    :class:`MachineConfigPostCommitError`, which
    :func:`_machine_config._write_cap_unguarded` raises if and only if the
    atomic replace already returned. It is emphatically NOT decided by the
    re-read: the write guard is released in
    :func:`write_max_slots_if_unset`'s ``finally`` BEFORE the exception reaches
    the caller's ``except`` arm, so between the raise and the re-read any other
    writer may install the same value and make an equal post-state that this
    invocation did not produce. Gating ``partial`` on that equality claimed
    authorship of a commit that never happened — the inverse of the false
    refusal above, in the same function.

    The two halves live in :func:`_migrate_committed_report` (marker present ⇒
    ``partial``) and :func:`_migrate_uncommitted_report` (marker absent ⇒
    ``refused`` / ``undetermined``); each documents the branch it owns. The
    re-read is still performed, and it is still what shapes every branch's
    detail — what the machine side holds now is the operator's next question
    either way — but it no longer decides the outcome.

    Args:
        exc: The exception the guarded write raised, quoted into every branch's
            detail so the operator sees the originating failure.
        per_repo_value: The repository's validated cap — the value this
            invocation attempted to commit.
        marshal_path: The repository config the per-repo key is still in.
        committed: Whether the raising write carried the post-replace commit
            marker. Keyword-only, because a positional bool at a call site
            reads as nothing at all and this one decides an authorship claim.

    Returns:
        The ``partial`` / ``refused`` / ``undetermined`` payload for the state
        the marker and the re-read together establish.
    """
    post = resolve_max_slots()
    if committed:
        return _migrate_committed_report(exc, per_repo_value, marshal_path, post)
    return _migrate_uncommitted_report(exc, per_repo_value, marshal_path, post)


def _classify_machine_side(cap: CapResolution, per_repo_value: int, marshal_path: str) -> dict[str, Any] | None:
    """Refuse when the machine-global side is not safely writable, else ``None``.

    The three refusals share one shape and one reason: something IS on the
    machine-global side, so copying over it would destroy it.

    * :data:`SOURCE_UNREADABLE` / :data:`SOURCE_INVALID` — the file exists and
      holds something. It is emphatically NOT "unset": a cap may well be
      configured there and merely unreachable or mistyped, and overwriting it
      would silently discard an operator's setting. ``config set`` is the verb
      that repairs those; migrate is not.
    * :data:`SOURCE_MACHINE_CONFIG` with a DIFFERENT value — the disagreement
      deliverable 4 reports at the queue is the same disagreement here, and
      picking a winner is precisely what this verb declines to do.

    :data:`SOURCE_MACHINE_CONFIG` with an EQUAL value is not a refusal (it is
    ``removed_duplicate``), and :data:`SOURCE_DEFAULT` is the migratable state;
    both return ``None``.
    """
    if cap.source == SOURCE_UNREADABLE:
        return _migrate_refused(
            'machine_config_unreadable',
            (
                f'refusing to migrate: the machine-global config at {cap.path} exists but cannot be read '
                f'({cap.detail}). It is not unset, so copying build.queue.max_slots={per_repo_value!r} over it '
                f'could discard a configured cap. Repair or remove {cap.path}, then re-run config migrate.'
            ),
            machine_config_path=cap.path,
            marshal_json_path=marshal_path,
            per_repo_max_slots=per_repo_value,
        )
    if cap.source == SOURCE_INVALID:
        return _migrate_refused(
            'machine_config_invalid',
            (
                f'refusing to migrate: the machine-global config at {cap.path} holds an invalid '
                f'build.queue.max_slots ({cap.detail}). It is not unset, so copying '
                f'build.queue.max_slots={per_repo_value!r} over it could discard a configured cap. '
                f'Fix it with `config set --max-slots N`, then re-run config migrate.'
            ),
            machine_config_path=cap.path,
            marshal_json_path=marshal_path,
            per_repo_max_slots=per_repo_value,
        )
    if cap.source == SOURCE_MACHINE_CONFIG and cap.value != per_repo_value:
        return _migrate_refused(
            'values_differ',
            (
                f'refusing to migrate: {marshal_path} sets build.queue.max_slots={per_repo_value!r} while the '
                f'machine-global cap at {cap.path} is {cap.value}. Neither file was changed. Either accept the '
                f'repository value machine-wide with `config set --max-slots {per_repo_value}` and re-run '
                f'config migrate, or accept the machine-global {cap.value} by deleting '
                f'build.queue.max_slots from {marshal_path}.'
            ),
            machine_config_path=cap.path,
            marshal_json_path=marshal_path,
            per_repo_max_slots=per_repo_value,
            machine_max_slots=cap.value,
        )
    return None


def run_config_migrate(_args: Namespace) -> dict[str, Any]:
    """Move this repository's build-slot cap to its machine-global home, in one step.

    The whole verb is defined by what it refuses to do: it copies the repository
    value machine-wide ONLY when nothing is configured there, and when the two
    sides disagree it changes NEITHER file and reports both values. Picking a
    winner is not a convenience here — a per-caller cap over one shared queue is
    the disagreement the queue itself reports, so silently resolving it would
    install a cap the operator never chose.

    Outcomes:

    * ``nothing_to_migrate`` — no per-repo key (or no ``marshal.json``). Nothing
      written.
    * ``migrated`` — the machine-global side is unset; the value is copied there
      and the per-repo key removed.
    * ``removed_duplicate`` — the machine-global side already holds the SAME
      value; only the per-repo key is removed and ``machine-config.json`` is left
      byte-identical.
    * ``refused`` (``status: error``) — one of the ``reason`` values the
      ``config migrate`` table in ``manage-build-server/SKILL.md`` enumerates,
      which is the single authority for that set. Both files byte-identical on
      every one of them. The set is deliberately NOT restated here: a
      restatement drifts from the code the moment a refusal path is added, and
      this docstring had already drifted to four members while the function
      raised six.
    * ``partial`` (``status: error``) — the machine-global side is settled but
      the ``marshal.json`` edit did not commit. Re-running converges via
      ``removed_duplicate``. When it is reached from a RAISING machine-global
      write, the settled half is asserted only on the writer's own
      post-replace commit marker
      (:class:`_machine_config.MachineConfigPostCommitError`) — never on a
      re-read that merely finds this repository's value there, which any other
      writer could have put there once the write guard was released.
    * ``undetermined`` (``status: error``) — the machine-global write raised
      WITHOUT that commit marker and the state it left is not this invocation's
      to claim, so the report claims NEITHER that the migration partly landed
      NOR that both files are untouched. This covers an equal-valued
      machine-global cap as well as an unreadable or foreign one: with no
      marker, equality is a coincidence the report must not read as authorship.
      It deliberately omits ``machine_config_modified`` /
      ``marshal_json_modified`` rather than sending either a ``false`` (which
      reads as the ``refused`` guarantee) or a ``true`` (which reads as
      ``partial``): the absence IS the report. See
      :func:`_migrate_write_failure_report`.

    The machine-global write happens FIRST and is ordered that way deliberately:
    if the repository edit then fails, the recoverable state is "value is
    machine-wide, key still present", which a re-run completes. The reverse order
    would delete the operator's only record of the value before it was stored
    anywhere.
    """
    marshal_path = str(get_marshal_path())
    per_repo_raw = read_per_repo_max_slots(marshal_path)
    if per_repo_raw is None:
        return {
            'status': 'success',
            'action': 'config migrate',
            'outcome': 'nothing_to_migrate',
            'detail': (
                f'{marshal_path} carries no build.queue.max_slots (the file may not exist) — '
                'there is nothing to migrate.'
            ),
            'machine_config_modified': False,
            'marshal_json_modified': False,
            'marshal_json_path': marshal_path,
        }

    # Validate BEFORE consulting the machine side: copying a value that could
    # never be a cap would install a broken cap machine-wide, and reporting the
    # repository's own bad value is more useful than reporting a comparison
    # against it.
    #
    # This is the ONE branch a non-int value reaches, so it is also the one
    # branch that echoes arbitrary foreign text back into the refusal payload.
    # The reported field goes through `report_safe`: a newline in the
    # repository's value would otherwise land at column zero of this refusal's
    # own TOON, where a consumer reparses it as an envelope key — turning
    # `status: error` / `outcome: refused` (with both files deliberately
    # untouched) into a reported `status: success` / `outcome: migrated`. The
    # message keeps its `!r`, which escapes the same characters. Every LATER
    # refusal is reached only after this positive-int check, so their reported
    # value is an int by construction.
    if isinstance(per_repo_raw, bool) or not isinstance(per_repo_raw, int) or per_repo_raw <= 0:
        return _migrate_refused(
            'per_repo_value_invalid',
            (
                f'refusing to migrate: {marshal_path} sets build.queue.max_slots={per_repo_raw!r}, which is not a '
                'positive integer and could not be a valid cap. Correct or delete the key, then re-run '
                'config migrate.'
            ),
            marshal_json_path=marshal_path,
            per_repo_max_slots=report_safe(per_repo_raw),
        )

    cap = resolve_max_slots()
    refusal = _classify_machine_side(cap, per_repo_raw, marshal_path)
    if refusal is not None:
        return refusal

    if cap.source == SOURCE_MACHINE_CONFIG:
        # Equal values — the machine side is already correct, so ONLY the
        # redundant per-repo key goes and machine-config.json is not touched.
        removal = _remove_per_repo_max_slots()
        if removal.get('status') != 'success':
            return {
                **removal,
                'action': 'config migrate',
                'outcome': 'partial',
                'machine_config_modified': False,
                'marshal_json_modified': False,
                'detail': (
                    f'the machine-global cap at {cap.path} already holds {cap.value}, but removing '
                    f'build.queue.max_slots from {marshal_path} did not commit. Nothing was changed on either '
                    'side; re-run config migrate to complete it.'
                ),
                'machine_config_path': cap.path,
                'marshal_json_path': marshal_path,
            }
        return {
            'status': 'success',
            'action': 'config migrate',
            'outcome': 'removed_duplicate',
            'machine_config_modified': False,
            'marshal_json_modified': True,
            'detail': (
                f'the machine-global cap at {cap.path} already held {cap.value}; removed the redundant '
                f'build.queue.max_slots from {marshal_path} and left machine-config.json untouched. '
                'marshal.json is git-tracked — commit the edit.'
            ),
            **_cap_report(cap),
            'marshal_json_path': marshal_path,
        }

    # The machine side is unset. Copy the value there under the write guard, which
    # re-resolves INSIDE the guard — so a concurrent set/migrate that landed since
    # the resolve above is observed and preserved rather than overwritten.
    # ``OSError`` covers the write's filesystem points (the state-dir mkdir, the
    # ``O_EXCL`` guard, the atomic replace, the chmod). Without it a read-only
    # home root or a permission change propagated out as a traceback instead of
    # a structured envelope. ``TimeoutError`` is an ``OSError`` subclass and so is
    # now redundant in the tuple; it is kept named because the guard timeout is a
    # distinct, expected failure and a reader should not have to know the
    # exception hierarchy to see it handled.
    #
    # The envelope's CONTENT cannot be a flat refusal, because these failure
    # points do not all fall on the same side of the atomic replace: the chmod
    # runs AFTER it, so its ``OSError`` arrives with the migrated cap already
    # committed. Which side the failure fell on is carried by the exception TYPE
    # — ``MachineConfigPostCommitError`` is raised if and only if the replace
    # committed — and is forwarded as the ``committed`` marker rather than
    # re-derived from a post-read the guard no longer protects. See
    # :func:`_migrate_write_failure_report`.
    #
    # The marker arm is FIRST because the type is an ``OSError`` subclass: the
    # generic arm placed ahead of it would swallow every committed-then-failed
    # write and report it as having no commit evidence — the exact false
    # refusal this pair of arms exists to prevent.
    try:
        post, wrote = write_max_slots_if_unset(per_repo_raw)
    except MachineConfigPostCommitError as exc:
        return _migrate_write_failure_report(exc, per_repo_raw, marshal_path, committed=True)
    except (ValueError, TimeoutError, OSError) as exc:
        return _migrate_write_failure_report(exc, per_repo_raw, marshal_path, committed=False)

    if not wrote:
        # A concurrent writer won the race. Re-classify from the POST state — the
        # repository's key is never removed on the strength of a stale "unset".
        refusal = _classify_machine_side(post, per_repo_raw, marshal_path)
        if refusal is not None:
            return refusal
        if post.source != SOURCE_MACHINE_CONFIG:
            return _migrate_refused(
                'machine_config_unresolved',
                (
                    f'refusing to migrate: the machine-global write was skipped but {post.path} did not resolve '
                    f'to a configured cap (source={post.source}). Neither file was changed.'
                ),
                machine_config_path=post.path,
                marshal_json_path=marshal_path,
                per_repo_max_slots=per_repo_raw,
            )
        # Equal value landed concurrently — this is removed_duplicate, reached by
        # the race path rather than by the check above.
        removal = _remove_per_repo_max_slots()
        if removal.get('status') != 'success':
            return {
                **removal,
                'action': 'config migrate',
                'outcome': 'partial',
                'machine_config_modified': False,
                'marshal_json_modified': False,
                'detail': (
                    f'a concurrent writer set the machine-global cap at {post.path} to {post.value}, matching this '
                    f'repository, but removing build.queue.max_slots from {marshal_path} did not commit. '
                    'Re-run config migrate to complete it.'
                ),
                'machine_config_path': post.path,
                'marshal_json_path': marshal_path,
            }
        return {
            'status': 'success',
            'action': 'config migrate',
            'outcome': 'removed_duplicate',
            'machine_config_modified': False,
            'marshal_json_modified': True,
            'detail': (
                f'a concurrent writer had already set the machine-global cap at {post.path} to {post.value}, '
                f'matching this repository; removed the redundant build.queue.max_slots from {marshal_path}. '
                'marshal.json is git-tracked — commit the edit.'
            ),
            **_cap_report(post),
            'marshal_json_path': marshal_path,
        }

    removal = _remove_per_repo_max_slots()
    if removal.get('status') != 'success':
        return {
            **removal,
            'action': 'config migrate',
            'outcome': 'partial',
            'machine_config_modified': True,
            'marshal_json_modified': False,
            'detail': (
                f'the machine-global cap at {post.path} was written as {post.value}, but build.queue.max_slots is '
                f'STILL present in {marshal_path} — its removal did not commit. Re-run config migrate to '
                'complete the migration through the removed_duplicate branch.'
            ),
            **_cap_report(post),
            'marshal_json_path': marshal_path,
        }

    return {
        'status': 'success',
        'action': 'config migrate',
        'outcome': 'migrated',
        'machine_config_modified': True,
        'marshal_json_modified': True,
        'detail': (
            f'moved build.queue.max_slots={per_repo_raw} from {marshal_path} to the machine-global '
            f'{post.path}. marshal.json is git-tracked — commit the edit.'
        ),
        **_cap_report(post),
        'marshal_json_path': marshal_path,
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
            'send them, never 0), the applied build-slot cap with its source (unknown for a daemon '
            'predating the fields; a degraded source is warned about), and running-vs-resolved '
            'binary provenance (divergence flagged; unknown never the resolved path).'
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

    config = sub.add_parser(
        'config',
        help='Read, set, or migrate the machine-global build-slot cap.',
        allow_abbrev=False,
    )
    config_sub = config.add_subparsers(dest='config_command', required=True)
    config_sub.add_parser(
        'get',
        help=(
            'Report the machine-global max_slots with its source and path, plus this '
            "project's per-repo key (absent, or its value with in_effect: false)."
        ),
        allow_abbrev=False,
    ).set_defaults(func=run_config_get)
    config_set = config_sub.add_parser(
        'set',
        help='Set the machine-global max_slots (a running daemon applies it on its next submit).',
        allow_abbrev=False,
    )
    config_set.add_argument(
        '--max-slots',
        type=int,
        required=True,
        help='The machine-global build-slot cap — a positive integer.',
    )
    config_set.set_defaults(func=run_config_set)
    config_sub.add_parser(
        'migrate',
        help=(
            "Move this repository's build.queue.max_slots machine-wide in one step: copied only "
            'when nothing is set machine-wide, per-repo key removed, and refused with neither file '
            'changed when the two values differ.'
        ),
        allow_abbrev=False,
    ).set_defaults(func=run_config_migrate)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point — dispatch a control verb and print its TOON result."""
    args = _build_arg_parser().parse_args(argv)
    return print_toon(args.func(args))


if __name__ == '__main__':
    safe_main(main)()
