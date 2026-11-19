#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Subprocess supervisor for the marshalld build server (clean env, classify).

The supervisor runs one build child per admitted job and owns four
responsibilities:

* **Clean server-side baseline env (S2)** — the child's environment is built
  from a fixed server-side whitelist, NEVER forwarded from the client and NEVER
  carrying provider secrets. A submit cannot smuggle credentials or override
  ``PATH`` into the build.
* **Stream capture** — the child's combined stdout/stderr is streamed to a log
  file INSIDE the submitting project's tree as it is produced, so a long build's
  output is durable even if the wait is reaped — and the log's life follows that
  tree (:func:`job_log_dir`). A tree that cannot hold the log fails the job as a
  LAUNCH fault (:func:`log_file_failure_payload`) instead of falling back to the
  machine-global directory.
* **Liveness tracking** — every output chunk marks progress, so the daemon can
  answer a bound-expiry ``wait`` with a live running-status TOON
  (``elapsed`` / ``idle_seconds``) rather than a timeout-shaped body.
* **Terminal classification** — the child's exit is classified into
  ``success | failure | timeout | killed``, reusing the shared
  :mod:`_build_result` shape. ``killed`` (the child died by a signal the
  supervisor did NOT send) is its own terminal state — "externally killed — not
  flaky, do not blind-retry" — and is NEVER folded into ``failure``.

**Exit 0 is necessary but not sufficient for ``success``.** The daemon's child is
normally a build wrapper, and the wrapper exits 0 even when the build failed — it
reports its real verdict in the build-result TOON it emits (``status:`` /
``exit_code:``), not in its process exit code. Classifying purely on
``returncode == 0`` therefore renders a false ``success`` for every failing routed
build. The shared :func:`_build_server_protocol.read_log_verdict` reads that
emitted verdict back from the job log — the single reader both this supervisor and
the client-side ``_build_execute_factory`` cross-check consume — and
:func:`run_job` downgrades a ``success`` classification (carrying the TOON's
``exit_code``) whenever the verdict does not affirmatively agree.

**The downgrade preserves WHICH non-green the verdict reported.** The wrapper's
vocabulary has four non-green values and three of them are not a build that ran
and failed — ``timeout`` (its own bound fired) and ``killed`` (its build child
was signalled while it survived: the INNER kill) are NON-FINISHES it observed
first-hand, and ``indeterminate`` is an outcome it could not establish at all.
The narrowed status is therefore the verdict's own status translated through
:func:`_build_server_protocol.wire_status_from_result`, never a hard-coded
``failure``; flattening them here would re-collapse at the daemon precisely what
the wrapper distinguished, and a routed timeout or kill would reach every
downstream gate as a red build.

The one place fidelity is knowingly given up is at the wire boundary itself: the
wire vocabulary is four-valued, so ``indeterminate`` translates onto ``failure``
because every published status must be terminal or a waiting client never stops.
That trade is the protocol module's, documented at
:data:`_build_server_protocol._RESULT_STATUS_TO_WIRE`, and it is a translation —
not this supervisor deciding a non-finish was a failure. Because the verdict
status here is read off a LOG rather than produced by this tree, the translation
goes through :func:`_wire_status_from_log_verdict`, which is fail-closed: a
status this daemon's protocol module cannot translate becomes ``indeterminate``
rather than aborting the job.

This supervisor's OWN ``timeout`` and ``killed`` legs are not subject to the
narrowing at all — a supervisor timeout and an external kill of the child always
outrank log content — and a job log carrying no parseable TOON status keeps
today's exit-code verdict, so a non-wrapper command run through the daemon is
unaffected.

**A supervisor timeout stops the child's process group, not only the child.** The
build child is the first link of a chain (executor, build wrapper, ``./pw``,
``uv``, pytest, xdist workers), so signalling only that pid leaves the rest
running and a re-run stacks a second suite on the first. On POSIX the child is
therefore launched as the leader of its own session, and on expiry the supervisor
signals the child's process GROUP: ``SIGTERM``, a grace period of
:data:`_JOB_KILL_GRACE_SECONDS`, then ``SIGKILL``. The build wrapper runs its own
build in a separate process group and forwards ``SIGTERM`` to it, so the grace
period is what lets that forwarded stop complete before the group ``SIGKILL``
lands; it must stay strictly greater than the wrapper's own forward grace.
``timed_out`` remains the classification input, so a signal exit the supervisor
caused is ``timeout``, never ``killed``.

**Windows keeps the single-process kill.** Process groups and ``os.killpg`` are
POSIX-only, so on Windows the child is launched without a session argument and a
timeout calls ``proc.kill()`` on the child alone, exactly as before.

The classification and env helpers are pure and unit-testable without spawning a
process; :func:`run_job` drives a real ``asyncio`` subprocess and is exercised
against trivial commands.

Usage:
    from _marshalld_supervisor import run_job, JobProgress, build_baseline_env

    progress = JobProgress()
    payload = await run_job(command, cwd, timeout=300, log_file=log, progress=progress)
"""

from __future__ import annotations

import asyncio
import contextlib
import os
import signal
import stat
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import IO, Any

from _build_result import (
    ERROR_BUILD_FAILED,
    ERROR_LOG_FILE_FAILED,
    error_result,
    success_result,
    timeout_result,
)
from _build_result import STATUS_INDETERMINATE as RESULT_STATUS_INDETERMINATE
from _build_result import STATUS_SUCCESS as RESULT_STATUS_SUCCESS
from _build_server_protocol import (
    MARSHALLD_JOB_ENV,
    STATUS_FAILURE,
    STATUS_KILLED,
    read_log_verdict,
    status_from_result,
    status_payload,
    wire_status_from_result,
)

# The fixed server-side env whitelist. Everything not listed here is dropped, so
# no client-forwarded variable and no provider secret reaches the build child.
BASELINE_ENV_KEYS = (
    'PATH',
    'HOME',
    'LANG',
    'LC_ALL',
    'LC_CTYPE',
    'TERM',
    'TMPDIR',
    'USER',
    'SHELL',
    'PLAN_MARSHALL_HOME',
)

_READ_CHUNK = 4096

_IS_WINDOWS = os.name == 'nt'

# Seconds between the group SIGTERM and the group SIGKILL on a supervisor
# timeout. The build wrapper forwards SIGTERM to its own build group and then
# waits its own forward grace before escalating, so this value MUST stay strictly
# greater than that wrapper grace (``_build_execute._GROUP_KILL_GRACE_SECONDS``):
# with an equal or smaller value the group SIGKILL here would end the wrapper
# before its forwarded stop completed, leaving the build group running.
_JOB_KILL_GRACE_SECONDS = 10

# Seconds between two checks of whether the signalled job group is empty.
_GROUP_POLL_SECONDS = 0.05


def build_baseline_env(source: dict[str, str] | None = None) -> dict[str, str]:
    """Build a clean build-child environment from the server-side whitelist.

    Args:
        source: The environment to filter (defaults to ``os.environ``).

    Returns:
        A new dict containing only the whitelisted keys that are present in the
        source — no client env, no provider secrets.
    """
    src = dict(os.environ) if source is None else source
    return {key: src[key] for key in BASELINE_ENV_KEYS if key in src}


def classify_terminal(returncode: int | None, *, timed_out: bool) -> str:
    """Classify a finished child into a terminal wire status.

    Args:
        returncode: The child's exit code (negative ``-N`` when killed by signal
            ``N``); may be ``None`` only for a never-started child.
        timed_out: ``True`` when the supervisor terminated the child for
            exceeding its timeout.

    Returns:
        One of ``timeout`` / ``killed`` / ``success`` / ``failure``. A timeout
        outranks the signal exit (the supervisor sent that signal); a negative
        exit the supervisor did NOT cause is ``killed`` — never ``failure``.
    """
    if timed_out:
        return 'timeout'
    if returncode is None:
        return STATUS_KILLED
    if returncode < 0:
        return STATUS_KILLED
    return 'success' if returncode == 0 else 'failure'


@dataclass
class JobProgress:
    """Liveness tracker for a running job.

    Attributes:
        start: Monotonic start timestamp.
        last_activity: Monotonic timestamp of the last output chunk.
    """

    start: float = field(default_factory=time.monotonic)
    last_activity: float = field(default_factory=time.monotonic)

    def mark(self) -> None:
        """Record output activity (resets the idle timer)."""
        self.last_activity = time.monotonic()

    def elapsed(self) -> float:
        """Return seconds since the job started."""
        return time.monotonic() - self.start

    def idle_seconds(self) -> float:
        """Return seconds since the last output chunk (``last_progress``)."""
        return time.monotonic() - self.last_activity


async def _pump(stream: asyncio.StreamReader | None, sink: IO[bytes], progress: JobProgress | None) -> None:
    """Stream a child pipe to the log sink, marking progress on each chunk."""
    if stream is None:
        return
    while True:
        chunk = await stream.read(_READ_CHUNK)
        if not chunk:
            return
        sink.write(chunk)
        if progress is not None:
            progress.mark()


def _terminal_payload(
    status: str,
    *,
    returncode: int | None,
    duration: int,
    log_file: str,
    command_str: str,
    applied_bound: int | None,
    bound_source: str | None,
) -> dict[str, Any]:
    """Render a terminal status payload reusing the _build_result shape.

    ``status`` is a WIRE status: either :func:`classify_terminal`'s own verdict
    or, when the narrowing fired, a log verdict translated by
    :func:`wire_status_from_result`. Every terminal wire status therefore has an
    explicit arm here, and ``failure`` is one of them rather than the fallback —
    a status this function does not recognise must not be rendered as a build
    that ran and failed, which is the fold-into-a-neighbour the whole
    non-finish separation exists to prevent.

    ``applied_bound`` / ``bound_source`` name the bound the two NON-FINISH arms
    report as ``timeout_used_seconds`` / ``timeout_source``. The caller decides
    whose bound that is — the supervisor's own for its own timeout or kill, the
    INNER wrapper's for a payload narrowed from the job log — and passes ``None``
    when it does not know one. An unknown bound emits neither field; the elapsed
    ``duration`` is never substituted for it. A source is emitted only beside a
    bound, because a source with no number names nothing.
    """
    bound: dict[str, Any] = {}
    if applied_bound is not None:
        bound['timeout_used_seconds'] = applied_bound
        if bound_source:
            bound['timeout_source'] = bound_source
    if status == 'timeout':
        source = {name: value for name, value in bound.items() if name == 'timeout_source'}
        return status_from_result(timeout_result(applied_bound, duration, log_file, command_str, **source))
    if status == STATUS_KILLED:
        return status_payload(
            STATUS_KILLED,
            duration_seconds=duration,
            log_file=log_file,
            exit_code=returncode if returncode is not None else -1,
            **bound,
        )
    if status == 'success':
        return status_from_result(success_result(duration, log_file, command_str))
    if status == STATUS_FAILURE:
        return status_from_result(error_result(ERROR_BUILD_FAILED, returncode or 1, duration, log_file, command_str))
    # Unrecognised: the caller handed a status outside the terminal wire
    # vocabulary. Report it verbatim rather than claiming a failure nobody
    # observed — the client maps an unrecognised terminal status to
    # ``indeterminate``, and this arm is what lets it see one.
    return status_payload(
        status,
        duration_seconds=duration,
        log_file=log_file,
        exit_code=returncode if returncode is not None else -1,
    )


def _wire_status_from_log_verdict(verdict_status: str) -> str:
    """Translate a LOG-SOURCED verdict status to the wire vocabulary, fail-closed.

    :func:`wire_status_from_result` raises when handed a :mod:`_build_result`
    status the wire table cannot translate — a deliberate totality guard on a
    value that normally arrives from code in this same tree. Here the value did
    not: it was READ OFF A JOB LOG, so it can come from a version-skewed wrapper
    binary emitting a status this daemon's protocol module predates (the
    condition ``manage-build-server status`` reports as ``binary_diverges``).

    Letting that raise escape would abort :func:`run_job` mid-job and lose the
    whole result, turning a translation gap into a daemon crash. ADR-009's
    fail-closed rule applies instead: an untranslatable log status becomes
    ``indeterminate`` — the value that exists precisely for "the outcome could
    not be established" — and the job still returns a terminal payload.

    A status outside BOTH vocabularies (a truncated or foreign log yielding
    arbitrary text) does not reach this branch at all: it passes through
    :func:`wire_status_from_result` unchanged and
    :func:`_terminal_payload` renders it verbatim for the client to map.

    The two unrecognised classes therefore end DIFFERENTLY, and must not be
    described as converging: this branch's class is re-read as ``indeterminate``
    and so leaves on the wire as ``failure`` (``indeterminate`` has no wire row of
    its own), which a client maps back to ``error``; the outside-both class leaves
    verbatim, as whatever text the log carried. What they share is narrower than a
    common outcome — neither crashes the daemon, and both still return a terminal
    payload.

    Args:
        verdict_status: The ``status:`` value read back from the job log.

    Returns:
        The corresponding wire status, or the wire status for ``indeterminate``
        when the value cannot be translated.
    """
    try:
        return wire_status_from_result(verdict_status)
    except ValueError:
        return wire_status_from_result(RESULT_STATUS_INDETERMINATE)


def _signal_job_group(pgid: int, signum: int) -> None:
    """Send ``signum`` to the job's process group; a vanished group is not an error.

    Args:
        pgid: The process-group id — the child's pid, because the child is
            launched as the leader of its own session.
        signum: The signal to deliver to every member of the group.
    """
    # ProcessLookupError: every member already exited, so nothing is left to stop.
    # PermissionError: the remaining members are ones this process may not signal.
    with contextlib.suppress(ProcessLookupError, PermissionError):
        os.killpg(pgid, signum)


def _job_group_is_empty(pgid: int) -> bool:
    """Report whether the job's process group has no member this process can signal.

    Args:
        pgid: The process-group id — the child's pid.
    """
    try:
        os.killpg(pgid, 0)
    except (ProcessLookupError, PermissionError):
        return True
    return False


async def _stop_job_tree(proc: asyncio.subprocess.Process) -> None:
    """Stop a timed-out job's process group and reap the child.

    On POSIX the child leads its own session, so its pid is the id of a process
    group holding every descendant that did not move itself elsewhere. The group
    receives ``SIGTERM``, then — once the group is empty or
    :data:`_JOB_KILL_GRACE_SECONDS` has passed, whichever comes first —
    ``SIGKILL``. On Windows only the child itself is killed.

    Args:
        proc: The timed-out build child.
    """
    if _IS_WINDOWS:
        proc.kill()
        await proc.wait()
        return
    _signal_job_group(proc.pid, signal.SIGTERM)
    # Reaped concurrently: an exited but unreaped child keeps the group non-empty.
    reaped = asyncio.ensure_future(proc.wait())
    deadline = time.monotonic() + _JOB_KILL_GRACE_SECONDS
    while time.monotonic() < deadline and not _job_group_is_empty(proc.pid):
        await asyncio.sleep(_GROUP_POLL_SECONDS)
    _signal_job_group(proc.pid, signal.SIGKILL)
    await reaped


_JOB_LOG_SUBDIR = Path('.plan') / 'local' / 'marshalld' / 'job-logs'
"""Where a job log lives, relative to the submitting project's tree root.

The log belongs to the tree that produced it, not to the machine that ran it: a
daemon-routed build's child runs ``{tree}/.plan/execute-script.py`` with ``cwd``
inside that tree, and its log is reachable by the same rule — a consumer that may
read the project (and nothing outside it) can open the ``log_file`` a build result
names. The tier is the project's own machine-local ``.plan/local``, which every
plan-marshall project's ``.gitignore`` covers, so a log never surfaces as an
untracked change, and the subtree is removed with the worktree it was written in.
"""


class JobLogUnavailable(RuntimeError):
    """The job log could not be prepared inside the submitting project's tree.

    This is a failure the daemon REPORTS, never one it works around: a
    machine-global copy of a job log is precisely the defect the in-tree location
    removes, so an unwritable tree fails the job instead of re-offending. The two
    fields make the failure legible — the path that could not be used, and why.

    Attributes:
        log_file: The in-tree path the job's log was to be written at.
        reason: What prevented it, in words (the ``OSError``'s own text).
    """

    def __init__(self, log_file: str, reason: str) -> None:
        super().__init__(f'{log_file}: {reason}')
        self.log_file = log_file
        self.reason = reason


def job_log_dir(project_root: str | Path) -> Path:
    """Return the job-log directory inside ``project_root``'s tree.

    Args:
        project_root: The submitting project's tree root (a plan worktree, when
            the job was submitted for one).

    Returns:
        ``{project_root}/.plan/local/marshalld/job-logs`` — not created here.
    """
    return Path(project_root) / _JOB_LOG_SUBDIR


def log_file_failure_payload(log_file: str, command_str: str, reason: str) -> dict[str, Any]:
    """Render the RECORDED failure of a job whose log could not be written.

    It is a LAUNCH fault (``log_file_failed``), not a red build: no child was
    started, so there is no test row, no bound and no verdict to report. The
    identifier is the one the in-process wrapper emits for the same condition, so
    the failure carries a single name in this tree; how the routed client renders a
    daemon ``failure`` is its own surface (:mod:`_build_execute_factory`), not this
    module's.

    Args:
        log_file: The log path that could not be written.
        command_str: The command that was not run.
        reason: What prevented the write, in words.

    Returns:
        A terminal ``failure`` payload carrying the named error and the reason.
    """
    return status_payload(
        STATUS_FAILURE,
        duration_seconds=0,
        log_file=log_file,
        exit_code=-1,
        error=ERROR_LOG_FILE_FAILED,
        reason=reason,
        command=command_str,
    )


_JOB_LOG_FILE_MODE = 0o600
"""Mode a job log is created with — build output is the project's own business."""


def _open_job_log(log_file: str) -> IO[bytes]:
    """Open (and create) a job log for writing, refusing anything but a regular file.

    The path sits inside a project the submitting user can write, so the open must
    not be steerable by something already at that name: ``O_NOFOLLOW`` rejects a
    pre-created symlink, ``O_NONBLOCK`` makes a FIFO fail instead of parking the
    daemon's event loop on an open that waits for a reader, and the ``S_ISREG``
    check covers a device or socket the flags alone would accept. The file is
    created ``0600`` and tightened if an earlier writer left it wider.

    Args:
        log_file: The job's log path, already inside the submitting tree.

    Returns:
        The write sink.

    Raises:
        OSError: when the path cannot be opened, or is not a regular file.
    """
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    flags |= getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0)
    fd = os.open(log_file, flags, _JOB_LOG_FILE_MODE)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise OSError(f'{log_file} is not a regular file')
        if hasattr(os, 'fchmod') and info.st_mode & 0o777 != _JOB_LOG_FILE_MODE:
            os.fchmod(fd, _JOB_LOG_FILE_MODE)
    except BaseException:
        os.close(fd)
        raise
    return os.fdopen(fd, 'wb')


async def run_job(
    command: list[str],
    cwd: str,
    *,
    timeout: int,
    log_file: str,
    timeout_source: str | None = None,
    env: dict[str, str] | None = None,
    progress: JobProgress | None = None,
) -> dict[str, Any]:
    """Run one build child and return its terminal status payload.

    A ``timeout`` or ``killed`` payload names the bound the job was measured
    against as ``timeout_used_seconds`` / ``timeout_source``. For the
    supervisor's OWN timeout or kill that is ``timeout`` with ``timeout_source``;
    for a payload narrowed from the job log it is the INNER wrapper's own bound
    and source as the log stated them, and neither field when the log stated no
    bound.

    Args:
        command: The executor-form argv to run (already verified).
        cwd: The working directory (the submitted tree).
        timeout: Wall-clock timeout in seconds; on expiry the child's whole
            process group is stopped (the child alone on Windows) and the
            status is ``timeout``.
        log_file: Path to stream combined stdout/stderr into — the in-tree target
            prepared by the daemon (:func:`job_log_dir`). It is opened BEFORE the
            child is spawned, so a path that cannot be opened returns a
            ``log_file_failed`` payload instead of starting a build whose output
            has nowhere to go.
        timeout_source: Where ``timeout`` came from (``daemon_default`` or
            ``explicit``, see ``marshalld.Daemon._resolve_job_timeout``).
            ``None`` means the caller did not say, and the supervisor's own
            non-finish payloads then carry the bound without a source.
        env: The child environment; defaults to :func:`build_baseline_env`.
        progress: Optional liveness tracker updated on each output chunk.

    Returns:
        The terminal status payload (``success | failure | timeout | killed``)
        in the shared result shape.
    """
    # Stamp the re-entrancy marker so the child's own build wrapper (when the
    # child re-runs the executor-form command) never routes back to the daemon —
    # a build already running inside a marshalld job always runs in-process. The
    # child env is copied first so a caller-supplied env dict is not mutated.
    child_env = dict(env if env is not None else build_baseline_env())
    child_env[MARSHALLD_JOB_ENV] = '1'
    command_str = ' '.join(command)
    if progress is None:
        progress = JobProgress()

    # The sink is opened BEFORE the child is spawned, so a tree that cannot hold
    # the job's log fails the job (as a LAUNCH fault) instead of starting a build
    # whose output has nowhere to go. There is no fall-back directory: writing the
    # log anywhere but the submitting tree is the defect this location removes.
    #
    # The creation is deliberately not a plain `open()`: the path is inside a
    # project the submitting user can write, so a pre-created symlink or FIFO at
    # that name must not be followed (a FIFO would block the daemon's event loop)
    # and the file must be private, whatever the process umask says.
    try:
        sink = _open_job_log(log_file)
    except OSError as exc:
        return log_file_failure_payload(
            log_file,
            command_str,
            f'the job log could not be written at {log_file}: {exc}',
        )

    # On POSIX the child leads its own session, so a timeout can stop the
    # child's process group (see _stop_job_tree).
    try:
        proc = await asyncio.create_subprocess_exec(
            *command,
            cwd=cwd,
            env=child_env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            start_new_session=not _IS_WINDOWS,
        )
    except OSError:
        # The sink exists but no build will write into it; release the handle and
        # remove the empty file, so a job that never started leaves no log behind.
        sink.close()
        with contextlib.suppress(OSError):
            Path(log_file).unlink()
        raise

    timed_out = False
    pump_results: list[Any] = []
    try:
        with sink:
            pumps = [
                asyncio.create_task(_pump(proc.stdout, sink, progress)),
                asyncio.create_task(_pump(proc.stderr, sink, progress)),
            ]
            try:
                await asyncio.wait_for(proc.wait(), timeout=timeout)
            except TimeoutError:
                timed_out = True
                await _stop_job_tree(proc)
            finally:
                pump_results = await asyncio.gather(*pumps, return_exceptions=True)
    except OSError as exc:
        # Closing the buffered sink flushes what is still pending, so the LAST write
        # of a small output can fail here rather than in a pump. It is the same
        # logging failure, reported the same way.
        return log_file_failure_payload(
            log_file,
            command_str,
            f'the job log at {log_file} could not be flushed when the job ended: {exc}',
        )

    # A voice that could not be written is a failed logging outcome, not a build
    # verdict: the pumps swallowed nothing on purpose, so a write failure is
    # reported as itself rather than leaving a truncated log beside a green result.
    write_failure = next(
        (result for result in pump_results if isinstance(result, OSError)),
        None,
    )
    if write_failure is not None:
        return log_file_failure_payload(
            log_file,
            command_str,
            f'the job log at {log_file} could not be written while the job ran: {write_failure}',
        )

    duration = int(progress.elapsed())
    status = classify_terminal(proc.returncode, timed_out=timed_out)
    returncode = proc.returncode
    # A log removed under a still-running job (a worktree cleaned up mid-build) takes
    # the wrapper's own verdict with it, so an exit-0 child must not be reported as a
    # green build. A timeout or an external kill is a verdict of ITS OWN — it outranks
    # log content and is never re-labelled by the missing file.
    if status == 'success' and not Path(log_file).exists():
        return log_file_failure_payload(
            log_file,
            command_str,
            f'the job log at {log_file} disappeared before its verdict could be read',
        )
    # Exit 0 is necessary but not sufficient: the build wrapper exits 0 even when
    # the build failed, so a `success` classification only stands when the
    # emitted build TOON affirmatively agrees. The supervisor's OWN timeout /
    # killed legs are untouched — they always outrank log content.
    #
    # When the verdict disagrees, the narrowed status is the verdict's OWN status
    # translated to the wire vocabulary — never a hard-coded `failure`. The
    # wrapper reports three ways to be non-green, and two of them are NON-FINISHES
    # it observed first-hand: its own bound fired (`timeout`), or its build child
    # was signalled while it survived (`killed`, the INNER kill — distinct from
    # the outer kill `classify_terminal` sees as a negative returncode). Flattening
    # those to `failure` here would re-collapse, at the daemon, exactly what the
    # wrapper just took care to distinguish: a routed timeout and a routed kill
    # would both reach every downstream gate as a red build.
    #
    # The bound travels with the verdict it belongs to. The supervisor's own
    # timeout or kill was measured against the supervisor's bound; a narrowed
    # non-finish was measured against the INNER wrapper's, which is the smaller
    # one and the one that fired, so reporting the daemon's bound there would
    # name a number that never applied.
    applied_bound: int | None = timeout
    bound_source = timeout_source
    if status == 'success':
        verdict = read_log_verdict(log_file)
        if verdict is not None and verdict.status != RESULT_STATUS_SUCCESS:
            status = _wire_status_from_log_verdict(verdict.status)
            returncode = verdict.exit_code
            applied_bound = verdict.timeout_used_seconds
            bound_source = verdict.timeout_source
    return _terminal_payload(
        status,
        returncode=returncode,
        duration=duration,
        log_file=log_file,
        command_str=command_str,
        applied_bound=applied_bound,
        bound_source=bound_source,
    )
