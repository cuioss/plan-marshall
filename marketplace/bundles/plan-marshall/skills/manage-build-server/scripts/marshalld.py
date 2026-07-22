#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""marshalld — the plan-marshall build-server daemon.

``marshalld`` is a machine-global, double-forked (ppid=1) asyncio daemon on a
Unix domain socket that owns build-class work for every registered plan-marshall
project on the host. It ties together the four cores:

* the VERIFIER (:mod:`_marshalld_verifier`, S1/S2) — every submit is verified
  positionally against the project's registration before it can run;
* the SCHEDULER (:mod:`_marshalld_scheduler`) — bounded ``max_slots`` admission
  with per-project round-robin fairness and idempotent-submit attach;
* the SUPERVISOR (:mod:`_marshalld_supervisor`) — one clean-env subprocess per
  job with liveness tracking and ``success|failure|timeout|killed`` classification;
* the JOURNAL (:mod:`_marshalld_journal`) — durable specs/results/ETA with
  bounded retention and restart replay.

The daemon answers three ops over length-prefixed JSON frames: ``ping`` (identity
handshake), ``submit`` (verify → schedule → journal), and ``wait`` (server-side
bounded long-poll returning a terminal result OR a live running-status TOON on
bound expiry). The socket is ``0600`` inside a ``0700`` directory; a stale socket
is taken over only after liveness-probing the previous pidfile.

The OS-level helpers (:func:`double_fork`, :func:`pid_alive`,
:func:`stale_socket_takeover`, :func:`rotate_log`) and the request dispatch
(:meth:`Daemon.handle_request`) are separable so they are unit-testable without
standing up the full socket server.

Usage:
    python3 .plan/execute-script.py plan-marshall:manage-build-server:marshalld run
    python3 .plan/execute-script.py plan-marshall:manage-build-server:marshalld run --foreground
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import os
import sys
import time
from pathlib import Path
from typing import Any

from _build_server_protocol import (
    STATUS_NOT_FOUND,
    STATUS_QUEUED,
    STATUS_REFUSED,
    STATUS_RUNNING,
    TERMINAL_STATUSES,
    FrameError,
    JobSpec,
    read_frame,
    status_payload,
    write_frame,
)
from _build_server_registry import canonicalize_root, read_registry
from _marshalld_audit import InteractionAudit
from _marshalld_journal import Journal
from _marshalld_scheduler import Scheduler, resolve_max_slots
from _marshalld_supervisor import JobProgress, run_job
from _marshalld_verifier import git_common_dir_resolver, verify_submit
from file_ops import get_marshal_path, read_json
from marketplace_paths import ensure_home_root, home_root

VERSION = '1'
"""Daemon protocol/identity version reported by ``ping`` and the handshake."""

_DEFAULT_JOB_TIMEOUT = 1800
_DEFAULT_WAIT_BOUND = 300
_POLL_INTERVAL_SECONDS = 0.5
_LOG_MAX_BYTES = 8 * 1024 * 1024
_DIR_MODE = 0o700
_SOCKET_MODE = 0o600


# =============================================================================
# Path resolution
# =============================================================================


def daemon_dir() -> Path:
    """Return the machine-global marshalld state directory."""
    return home_root() / 'marshalld'


def socket_path() -> Path:
    """Return the Unix domain socket path."""
    return daemon_dir() / 'socket'


def pidfile_path() -> Path:
    """Return the daemon pidfile path."""
    return daemon_dir() / 'daemon.pid'


def log_path() -> Path:
    """Return the daemon log path."""
    return daemon_dir() / 'daemon.log'


def job_log_dir() -> Path:
    """Return the per-job build-log directory."""
    return daemon_dir() / 'job-logs'


def ensure_daemon_dir() -> Path:
    """Create the marshalld state dir (and job-log subdir) ``0o700``."""
    ensure_home_root()
    directory = daemon_dir()
    directory.mkdir(mode=_DIR_MODE, parents=True, exist_ok=True)
    if (directory.stat().st_mode & 0o777) != _DIR_MODE:
        os.chmod(directory, _DIR_MODE)
    logs = job_log_dir()
    logs.mkdir(mode=_DIR_MODE, parents=True, exist_ok=True)
    return directory


# =============================================================================
# Pidfile / liveness / stale-socket takeover
# =============================================================================


class DaemonAlreadyRunning(RuntimeError):
    """Raised when a live daemon already owns the socket."""

    def __init__(self, pid: int) -> None:
        self.pid = pid
        super().__init__(f'marshalld already running (pid {pid})')


def read_pid(pidfile: Path) -> int | None:
    """Read a pid from a pidfile, or ``None`` when absent / malformed."""
    try:
        text = pidfile.read_text(encoding='utf-8').strip()
    except OSError:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def write_pid(pidfile: Path, pid: int) -> None:
    """Write ``pid`` to ``pidfile``."""
    pidfile.write_text(f'{pid}\n', encoding='utf-8')


def pid_alive(pid: int) -> bool:
    """Return whether a process with ``pid`` is alive (probe via signal 0)."""
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        # The process exists but is owned by another user — treat as alive.
        return True
    return True


def stale_socket_takeover(sock_path: Path, pidfile: Path) -> None:
    """Take over a stale socket, or refuse when a live daemon owns it.

    When the socket already exists, the previous pidfile is liveness-probed: a
    live owner means another daemon is running (:class:`DaemonAlreadyRunning`);
    a dead / missing owner means the socket is stale and is unlinked so this
    daemon can bind. The socket is NEVER unlinked before the liveness probe.

    Args:
        sock_path: The socket path.
        pidfile: The pidfile path.

    Raises:
        DaemonAlreadyRunning: when a live daemon still owns the socket.
    """
    if not sock_path.exists():
        return
    owner = read_pid(pidfile)
    if owner is not None and pid_alive(owner):
        raise DaemonAlreadyRunning(owner)
    sock_path.unlink(missing_ok=True)


# =============================================================================
# Daemonization / log rotation
# =============================================================================


def rotate_log(path: Path, max_bytes: int = _LOG_MAX_BYTES) -> None:
    """Rotate ``path`` to ``{path}.1`` when it exceeds ``max_bytes`` (single gen)."""
    try:
        if path.exists() and path.stat().st_size > max_bytes:
            backup = path.with_name(path.name + '.1')
            backup.unlink(missing_ok=True)
            path.rename(backup)
    except OSError:
        # Rotation is best-effort — a failure must not abort daemon start.
        pass


def double_fork() -> None:
    """Detach into a daemon via the classic double fork (re-parents to ppid=1).

    The first fork + ``setsid`` divorces the process from the controlling
    terminal and makes it a session leader; the second fork ensures the daemon
    is NOT a session leader (so it can never reacquire a controlling terminal)
    and, once the intermediate leader exits, the daemon is re-parented to PID 1.
    stdio is redirected to ``/dev/null`` and cwd is moved to ``/`` so the daemon
    holds no working-directory or terminal references.
    """
    if os.fork() > 0:
        os._exit(0)
    os.setsid()
    if os.fork() > 0:
        os._exit(0)
    os.chdir('/')
    os.umask(0o077)
    devnull = os.open(os.devnull, os.O_RDWR)
    for fd in (0, 1, 2):
        os.dup2(devnull, fd)
    if devnull > 2:
        os.close(devnull)


# =============================================================================
# Daemon core
# =============================================================================


class Daemon:
    """Wires the verifier, scheduler, supervisor, and journal behind the socket."""

    def __init__(
        self,
        *,
        scheduler: Scheduler,
        journal: Journal,
        interaction_audit: InteractionAudit | None = None,
        baseline_interpreter: str | None = None,
        common_dir_resolver: Any = None,
        job_timeout: int = _DEFAULT_JOB_TIMEOUT,
        log_dir: Path | None = None,
        poll_interval: float = _POLL_INTERVAL_SECONDS,
    ) -> None:
        """Initialise the daemon.

        Args:
            scheduler: The admission scheduler.
            journal: The durable journal.
            interaction_audit: The central interaction-audit log (injectable for
                tests, like ``journal``); defaults to a fresh
                :class:`InteractionAudit` resolving the machine-global home.
            baseline_interpreter: The registered baseline interpreter for the
                verifier (defaults to this daemon's own ``sys.executable``).
            common_dir_resolver: Worktree-liveness resolver for the verifier
                (defaults to the git-backed resolver).
            job_timeout: Per-job wall-clock timeout in seconds.
            log_dir: Per-job build-log directory.
            poll_interval: Wait long-poll interval in seconds.
        """
        self._scheduler = scheduler
        self._journal = journal
        self._interaction_audit = interaction_audit or InteractionAudit()
        self._baseline_interpreter = baseline_interpreter or sys.executable
        self._common_dir_resolver = common_dir_resolver or git_common_dir_resolver
        self._job_timeout = job_timeout
        self._log_dir = log_dir or job_log_dir()
        self._poll_interval = poll_interval
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._progress: dict[str, JobProgress] = {}

    # -- request dispatch --------------------------------------------------

    async def handle_request(self, request: dict[str, Any]) -> dict[str, Any]:
        """Dispatch one decoded request frame to its handler.

        Args:
            request: The decoded request payload with an ``op`` discriminator.

        Returns:
            The response payload to frame back to the client.
        """
        op = request.get('op')
        if op == 'ping':
            response = self._ping()
        elif op == 'submit':
            response = await self._submit(request)
        elif op == 'wait':
            response = await self._wait(request)
        else:
            response = {'status': 'error', 'error': 'unknown_op', 'op': op}
        self._audit_interaction(op, request, response)
        return response

    def _ping(self) -> dict[str, Any]:
        return {'status': 'ok', 'pid': os.getpid(), 'version': VERSION}

    # -- interaction audit -------------------------------------------------

    def _audit_interaction(self, op: Any, request: dict[str, Any], response: dict[str, Any]) -> None:
        """Append exactly one attributed interaction record for this request.

        Attribution (``project_root`` / ``plan_id`` / ``job_id``) is derived from
        the request/job spec where present and left empty when absent (e.g. a
        ``ping`` carries none); ``outcome`` is the response ``status``. Audit
        writing is best-effort — a disk failure must never abort request
        handling. Secrets discipline lives in :meth:`InteractionAudit.record`:
        only ``op`` / ``project_root`` / ``plan_id`` / ``job_id`` / ``outcome`` /
        ``timestamp`` (plus a non-secret ``reason``) are ever written.
        """
        try:
            # Attribution derivation is inside the guard too: canonicalize_root()
            # resolves the project path (Path.resolve()) and can raise OSError on a
            # symlink loop / resolution failure. Deriving it outside the try would
            # let that raise propagate out of handle_request and abort an otherwise
            # successful request — the exact contract this best-effort guard exists
            # to uphold ("a disk failure must never abort request handling").
            project_root, plan_id = self._audit_attribution(op, request)
            job_id = self._audit_job_id(op, request, response)
            # Failure responses are not uniform: status_payload(STATUS_REFUSED)
            # sets `reason`, but unknown_op / invalid_job / missing_job set
            # `error`. Fall back to `error` so those failure paths keep their
            # detail in the audit trail instead of recording reason=None.
            reason = response.get('reason') or response.get('error')
            self._interaction_audit.record(
                op=str(op or ''),
                project_root=project_root,
                plan_id=plan_id,
                job_id=job_id,
                outcome=str(response.get('status', '')),
                reason=str(reason) if reason else None,
            )
        except Exception:  # noqa: BLE001 — audit is best-effort, never abort request handling
            pass

    @staticmethod
    def _audit_attribution(op: Any, request: dict[str, Any]) -> tuple[str, str]:
        """Return the ``(project_root, plan_id)`` attribution for a request.

        Only a ``submit`` carries a job spec; ``ping`` / ``wait`` carry no spec,
        so both fields are empty for them. ``project_root`` is canonicalised so
        it matches the caller-canonical root the operator ``logs`` verb filters on.
        """
        if op == 'submit':
            job_raw = request.get('job')
            if isinstance(job_raw, dict):
                project_path = str(job_raw.get('project_path', ''))
                project_root = canonicalize_root(project_path) if project_path else ''
                return project_root, str(job_raw.get('plan_id', ''))
        return '', ''

    @staticmethod
    def _audit_job_id(op: Any, request: dict[str, Any], response: dict[str, Any]) -> str:
        """Return the ``job_id`` attribution: from the response on ``submit``, the request on ``wait``."""
        if op == 'submit':
            return str(response.get('job_id', ''))
        if op == 'wait':
            return str(request.get('job_id', ''))
        return ''

    async def _submit(self, request: dict[str, Any]) -> dict[str, Any]:
        job_raw = request.get('job')
        if not isinstance(job_raw, dict):
            return {'status': 'error', 'error': 'missing_job'}
        try:
            spec = JobSpec.from_dict(job_raw)
        except ValueError as exc:
            return {'status': 'error', 'error': 'invalid_job', 'message': str(exc)}

        registry = read_registry()
        outcome = verify_submit(
            spec,
            registry,
            baseline_interpreter=self._baseline_interpreter,
            common_dir_resolver=self._common_dir_resolver,
        )
        if not outcome.accepted:
            return status_payload(STATUS_REFUSED, reason=outcome.reason)

        assert outcome.record is not None  # accepted implies a matched record
        result = self._scheduler.submit(spec, outcome.record.get('canonical_root', ''))
        if not result.attached:
            self._journal.record_spec(result.job_id, spec.to_dict())
        self._admit_ready()
        return {'status': STATUS_QUEUED, 'job_id': result.job_id, 'attached': result.attached}

    async def _wait(self, request: dict[str, Any]) -> dict[str, Any]:
        job_id = request.get('job_id', '')
        bound = int(request.get('bound', _DEFAULT_WAIT_BOUND))
        deadline = time.monotonic() + bound

        while time.monotonic() < deadline:
            entry = self._journal.get(job_id)
            if entry is None:
                return status_payload(STATUS_NOT_FOUND, job_id=job_id)
            status = entry.get('status', '')
            if status in TERMINAL_STATUSES:
                result = entry.get('result')
                return result if isinstance(result, dict) else status_payload(status, job_id=job_id)
            await asyncio.sleep(self._poll_interval)

        # Bound expired without a terminal result — return a LIVE running-status
        # TOON (never a timeout-shaped body).
        return self._running_status(job_id)

    def _running_status(self, job_id: str) -> dict[str, Any]:
        entry = self._journal.get(job_id)
        if entry is None:
            return status_payload(STATUS_NOT_FOUND, job_id=job_id)
        progress = self._progress.get(job_id)
        elapsed = int(progress.elapsed()) if progress else 0
        idle = int(progress.idle_seconds()) if progress else 0
        eta = self._journal.estimate_eta(_command_key(entry.get('spec', {})))
        return status_payload(
            STATUS_RUNNING,
            job_id=job_id,
            elapsed=elapsed,
            last_progress=idle,
            eta=eta,
        )

    # -- admission / execution --------------------------------------------

    def _admit_ready(self) -> None:
        while self._scheduler.available_slots() > 0:
            entry = self._scheduler.admit_next()
            if entry is None:
                return
            self._journal.record_status(entry.job_id, STATUS_RUNNING)
            self._progress[entry.job_id] = JobProgress()
            self._tasks[entry.job_id] = asyncio.create_task(self._execute(entry.job_id, entry.spec))

    async def _execute(self, job_id: str, spec_dict: dict[str, Any]) -> None:
        try:
            spec = JobSpec.from_dict(spec_dict)
            self._log_dir.mkdir(mode=_DIR_MODE, parents=True, exist_ok=True)
            log_file = str(self._log_dir / f'{job_id}.log')
            payload = await run_job(
                spec.command,
                spec.project_path,
                timeout=self._job_timeout,
                log_file=log_file,
                progress=self._progress.get(job_id),
            )
        except Exception as exc:  # noqa: BLE001 -- any failure becomes a terminal result
            payload = status_payload('failure', error=str(exc))
        self._journal.record_result(job_id, payload)
        self._journal.record_duration(
            _command_key(spec_dict), float(payload.get('duration_seconds', 0) or 0)
        )
        self._scheduler.complete(job_id)
        self._progress.pop(job_id, None)
        self._tasks.pop(job_id, None)
        self._admit_ready()

    # -- socket server -----------------------------------------------------

    async def serve(self) -> None:
        """Bind the Unix socket and serve requests until cancelled."""
        ensure_daemon_dir()
        rotate_log(log_path())
        stale_socket_takeover(socket_path(), pidfile_path())
        try:
            self._journal.replay_on_restart()
        except OSError:
            # Journal replay is best-effort — it reads and rewrites the on-disk
            # journal, either of which can raise OSError. A replay failure must
            # never abort daemon startup; the unreplayed records are simply
            # carried to the next start's replay.
            pass
        try:
            self._interaction_audit.gc()
        except OSError:
            # Retention GC is best-effort — its prune path rewrites the log via
            # atomic_write_file()/chmod(), either of which can raise OSError. A
            # cleanup failure must never abort daemon startup; the stale records
            # are simply carried to the next start's GC.
            pass

        server = await asyncio.start_unix_server(self._on_client, path=str(socket_path()))
        os.chmod(socket_path(), _SOCKET_MODE)
        write_pid(pidfile_path(), os.getpid())
        async with server:
            await server.serve_forever()

    async def _on_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            request = await read_frame(reader)
            response = await self.handle_request(request)
            await write_frame(writer, response)
        except FrameError:
            pass
        finally:
            writer.close()
            with contextlib.suppress(Exception):
                await writer.wait_closed()


def _command_key(spec_dict: dict[str, Any]) -> str:
    """Derive an ETA-history key from a job spec (the executor notation)."""
    command = spec_dict.get('command', [])
    if isinstance(command, list) and len(command) >= 3:
        return str(command[2])
    return 'default'


# =============================================================================
# Entry point
# =============================================================================


def build_daemon() -> Daemon:
    """Construct a :class:`Daemon` with config-resolved slots, a journal, and an interaction audit."""
    config = read_json(get_marshal_path(), default={})
    scheduler = Scheduler(max_slots=resolve_max_slots(config))
    journal = Journal()
    interaction_audit = InteractionAudit()
    return Daemon(scheduler=scheduler, journal=journal, interaction_audit=interaction_audit)


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog='marshalld', allow_abbrev=False)
    sub = parser.add_subparsers(dest='command', required=True)
    run = sub.add_parser('run', help='Run the daemon (double-forks unless --foreground).', allow_abbrev=False)
    run.add_argument(
        '--foreground',
        action='store_true',
        help='Run in the foreground without daemonizing (for supervision / tests).',
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point: ``run`` starts the daemon."""
    args = _build_arg_parser().parse_args(argv)
    if args.command == 'run':
        if not args.foreground:
            double_fork()
        daemon = build_daemon()
        try:
            asyncio.run(daemon.serve())
        except DaemonAlreadyRunning as exc:
            print(f'marshalld: {exc}', file=sys.stderr)
            return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
