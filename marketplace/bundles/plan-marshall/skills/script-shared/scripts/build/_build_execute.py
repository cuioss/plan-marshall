#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared build command execution - foundation layer for all build systems.

Provides execute_direct_base() with common subprocess execution, timeout handling,
adaptive learning, and error handling. Each build system provides a thin wrapper
that supplies build-specific configuration (command construction, capture strategy,
scope extraction).

Usage:
    from _build_execute import execute_direct_base, CaptureStrategy

    result = execute_direct_base(
        args="clean verify",
        command_key="maven:verify",
        default_timeout=300,
        project_dir=".",
        tool_name="maven",
        build_command_fn=my_build_command_fn,
        plan_id="my-plan",
        scope_fn=my_scope_fn,
        capture_strategy=CaptureStrategy.TOOL_LOG_FLAG,
    )
"""

from __future__ import annotations

import contextlib
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from enum import Enum
from pathlib import Path
from typing import IO, Any

from _build_result import DirectCommandResult, create_log_file, killed_result
from plan_logging import log_entry
from run_config import TIMEOUT_SOURCE_FLOOR, timeout_resolve, timeout_set

# ---------------------------------------------------------------------------
# Platform-aware build wrapper detection (merged from _build_wrapper.py)
# ---------------------------------------------------------------------------

IS_WINDOWS = sys.platform == 'win32'


def detect_wrapper(
    project_dir: str,
    unix_wrapper: str,
    windows_wrapper: str,
    system_fallback: str | None = None,
) -> str | None:
    """Detect build wrapper based on platform.

    Args:
        project_dir: Project root directory.
        unix_wrapper: Unix wrapper filename (e.g., 'pw', 'mvnw', 'gradlew').
        windows_wrapper: Windows wrapper filename (e.g., 'pw.bat', 'mvnw.cmd').
        system_fallback: Optional system command to check on PATH.

    Returns:
        Path to wrapper or system command, None if not found.
        On Unix: returns './wrapper' (relative, standard convention).
        On Windows: returns absolute path (required for subprocess).
    """
    root = Path(project_dir).resolve()

    if IS_WINDOWS:
        wrapper_path = root / windows_wrapper
        if wrapper_path.exists() and wrapper_path.is_file():
            return str(wrapper_path)
    else:
        wrapper_path = root / unix_wrapper
        if wrapper_path.exists() and wrapper_path.is_file():
            return f'./{unix_wrapper}'

    # Fallback to system command
    if system_fallback and shutil.which(system_fallback):
        return system_fallback

    return None


def has_wrapper(project_root: Path, unix_wrapper: str, windows_wrapper: str) -> bool:
    """Check if wrapper exists for current platform.

    Args:
        project_root: Project root directory.
        unix_wrapper: Unix wrapper filename.
        windows_wrapper: Windows wrapper filename.

    Returns:
        True if wrapper exists for current platform.
    """
    if IS_WINDOWS:
        return (project_root / windows_wrapper).exists()
    return (project_root / unix_wrapper).exists()


# Tool-agnostic DEFAULT minimum timeout floor (seconds) — prevents adaptive
# learning from producing dangerously short timeouts (e.g., a warm cache run
# teaching 5s that then fails on a cold start). It is a default, not a ceiling
# on the floor: a tool with its own inner timeout backstop overrides it via the
# ``min_timeout`` parameter of ``execute_direct_base`` / ``ExecuteConfig``.
MIN_TIMEOUT = 60

# Maximum timeout cap (seconds) — prevents exponential growth from successive
# timeouts (each timeout doubles the learned value: 300→600→1200→...).
# 30 minutes is a reasonable upper bound for any single build command.
MAX_TIMEOUT = 1800

# Seconds between the group SIGTERM and the group SIGKILL when the wrapper stops
# its build group — on its own timeout, or after forwarding a signal it received.
# MUST stay strictly less than ``_marshalld_supervisor._JOB_KILL_GRACE_SECONDS``:
# the daemon supervisor SIGKILLs the wrapper once that longer grace has passed,
# and a SIGKILL of the wrapper cannot be forwarded, so the wrapper's own stop of
# the build group has to complete first.
_GROUP_KILL_GRACE_SECONDS = 5

# Upper bound (seconds) on one blocking wait for the build child. The wait is
# sliced so a forwarded signal is noticed promptly instead of after the bound.
_WAIT_SLICE_SECONDS = 0.5


class CaptureStrategy(Enum):
    """How build output is captured to the log file."""

    STDOUT_REDIRECT = 'stdout_redirect'
    """Redirect stdout/stderr to log file via open() (Gradle, npm, Python)."""

    TOOL_LOG_FLAG = 'tool_log_flag'
    """Tool manages log file (e.g., Maven -l flag); subprocess gets capture_output=False."""


# Type for build command function: (wrapper, args, log_file) -> (cmd_parts, command_str)
# log_file is passed so tools like Maven can embed it via -l flag.
BuildCommandFn = Callable[[str, str, str], tuple[list[str], str]]

# Type for scope extraction function: (args) -> scope string
ScopeFn = Callable[[str], str]


def _default_scope_fn(args: str) -> str:
    """Default scope extraction - always returns 'default'."""
    return 'default'


def _signal_build_group(pgid: int, signum: int) -> None:
    """Send ``signum`` to the build's process group; a vanished group is not an error.

    Args:
        pgid: The process-group id — the build child's pid, because the child
            is launched as the leader of its own group.
        signum: The signal to deliver to every member of the group.
    """
    # ProcessLookupError: every member already exited, so nothing is left to stop.
    with contextlib.suppress(ProcessLookupError):
        os.killpg(pgid, signum)


def _kill_build_group_after_grace(proc: subprocess.Popen[bytes]) -> int:
    """Give an already-signalled build group its grace, then SIGKILL it and reap.

    Args:
        proc: The build child, leader of the build process group.

    Returns:
        The child's returncode.
    """
    # TimeoutExpired: the child outlived the whole grace period.
    with contextlib.suppress(subprocess.TimeoutExpired):
        proc.wait(timeout=_GROUP_KILL_GRACE_SECONDS)
    # Sent even when the child already exited: other group members may remain.
    _signal_build_group(proc.pid, signal.SIGKILL)
    return proc.wait()


def _run_bounded(
    cmd_parts: list[str],
    *,
    timeout_seconds: int,
    stdout: IO[Any] | None,
    stderr: int | None,
    cwd: str,
    env: dict[str, str] | None,
    log_prefix: str,
    command_str: str,
) -> int:
    """Run the build command under its bound and stop its whole process tree on expiry.

    On POSIX the command is started as the leader of its own process group. When
    the bound expires the group receives ``SIGTERM``, then — after
    :data:`_GROUP_KILL_GRACE_SECONDS` — ``SIGKILL``, the child is reaped and
    ``subprocess.TimeoutExpired`` is raised. While the child runs, ``SIGTERM``,
    ``SIGINT`` and ``SIGHUP`` delivered to this process are forwarded to the
    group, which is then stopped with the same grace and ``SIGKILL``; the
    previous handlers are restored before returning. Handlers can only be
    installed from the main thread, so a call from any other thread runs
    without forwarding. A ``SIGKILL`` addressed to the wrapper's pid or to the
    wrapper's process group does not reach the build group.

    On Windows there are no process groups to signal: the command runs as a
    plain child and an expired bound kills that one process, as before.

    Args:
        cmd_parts: The build argv.
        timeout_seconds: The resolved bound in seconds.
        stdout: Where the child's stdout goes; ``None`` inherits.
        stderr: Where the child's stderr goes; ``None`` inherits.
        cwd: The child's working directory.
        env: The child's environment; ``None`` inherits.
        log_prefix: Tool prefix for the forwarded-signal log line.
        command_str: Printable command for the forwarded-signal log line.

    Returns:
        The child's returncode.

    Raises:
        subprocess.TimeoutExpired: The bound expired and the build was stopped.
    """
    if IS_WINDOWS:
        child = subprocess.Popen(cmd_parts, stdout=stdout, stderr=stderr, cwd=cwd, env=env)
        try:
            return child.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait()
            raise

    proc = subprocess.Popen(cmd_parts, stdout=stdout, stderr=stderr, cwd=cwd, env=env, process_group=0)
    received: list[int] = []

    def _forward(signum: int, _frame: object) -> None:
        received.append(signum)
        _signal_build_group(proc.pid, signum)

    previous: dict[signal.Signals, Any] = {}
    if threading.current_thread() is threading.main_thread():
        for forwarded in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
            previous[forwarded] = signal.signal(forwarded, _forward)
    try:
        deadline = time.monotonic() + timeout_seconds
        while not received:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                _signal_build_group(proc.pid, signal.SIGTERM)
                _kill_build_group_after_grace(proc)
                raise subprocess.TimeoutExpired(cmd_parts, timeout_seconds)
            try:
                finished = proc.wait(timeout=min(remaining, _WAIT_SLICE_SECONDS))
            except subprocess.TimeoutExpired:
                # This slice ended with the child still running.
                continue
            # The child ending is not proof that no signal was forwarded: a
            # handler that ran during this very wait usually ends the child at
            # once, while group members that ignore the signal keep running.
            # Only an exit with no forwarded signal is an ordinary finish.
            if not received:
                return finished
        returncode = _kill_build_group_after_grace(proc)
        log_entry(
            'script',
            'global',
            'ERROR',
            f'[{log_prefix}] Received {signal.Signals(received[0]).name}, forwarded it to the build '
            f'process group and stopped that group: {command_str}. A SIGKILL of this wrapper '
            f'cannot be forwarded and leaves the build group running.',
        )
        return returncode
    finally:
        for forwarded, handler in previous.items():
            signal.signal(forwarded, handler)


def execute_direct_base(
    args: str,
    command_key: str,
    default_timeout: int,
    project_dir: str,
    tool_name: str,
    build_command_fn: BuildCommandFn,
    wrapper: str,
    plan_id: str,
    capture_strategy: CaptureStrategy = CaptureStrategy.STDOUT_REDIRECT,
    scope_fn: ScopeFn | None = None,
    env_vars: dict[str, str] | None = None,
    working_dir: str | None = None,
    extra_result_fields: dict | None = None,
    min_timeout: int = MIN_TIMEOUT,
    explicit_timeout: int | None = None,
) -> DirectCommandResult:
    """Execute a build command with adaptive timeout learning.

    This is the shared foundation layer for all build system command execution.
    Handles log file creation, timeout management, subprocess execution, and
    structured result construction.

    The timeout the subprocess is measured against resolves as::

        explicit_timeout supplied     -> max(explicit_timeout,                        min_timeout)
        explicit_timeout NOT supplied -> max(timeout_get(command_key, default_timeout), min_timeout)

    An explicit bound is therefore a true OVERRIDE of the persisted learned
    value — no learned value can reduce it — while the engine's declared floor
    still binds, because the floor protects against under-specification.

    The bound is resolved through ``run_config.timeout_resolve``, which returns
    the same integer ``timeout_get`` does together with its origin. A ``timeout``
    or ``killed`` result carries that pair as ``timeout_used_seconds`` (the
    applied bound, never the elapsed time) and ``timeout_source`` (``explicit``,
    ``learned``, ``default``, or ``floor`` when either the run-config minimum or
    ``min_timeout`` raised the value), plus the ``command_key`` the learned value
    is stored under.

    **Three non-green outcomes, three statuses.** The returned ``status``
    separates the conditions the caller must act on differently:

    * ``error`` — the build ran to completion and reported a failure.
    * ``timeout`` — the build exceeded the bound resolved above, so the kill
      signal was OURS and the elapsed equals the bound.
    * ``killed`` — the child died by a signal this stack did not send
      (``returncode < 0``). The build reported nothing, so this is neither a
      failure nor a timeout, and its elapsed is a truncation rather than a
      measurement — it is therefore NOT fed to the adaptive learner.

    Args:
        args: Complete command arguments with all routing embedded.
        command_key: Command identifier for timeout learning (e.g., "maven:verify").
        default_timeout: Default timeout in seconds if no learned value exists.
            Consulted only on the no-override path.
        project_dir: Project root directory.
        tool_name: Build system name for logging prefix (e.g., "MAVEN", "GRADLE").
        build_command_fn: Callable(wrapper, args, log_file) -> (cmd_parts, command_str).
            Constructs the tool-specific command line. log_file is passed so
            tools like Maven can embed it via -l flag.
        wrapper: Resolved wrapper/executable path.
        plan_id: Plan identifier the build is attributed to, or the ``NO_PLAN``
            sentinel for a genuinely plan-less build. Forwarded to
            :func:`create_log_file`, which places the log under that plan's
            ``build-results/`` directory.
        capture_strategy: How output is captured to the log file.
        scope_fn: Callable(args) -> scope string for log file scoping.
            Defaults to returning 'default'.
        env_vars: Additional environment variables to inject.
        working_dir: Working directory override (defaults to project_dir).
        extra_result_fields: Additional fields to include in all result dicts
            (e.g., {"wrapper": "./mvnw"} or {"command_type": "npm"}).
        min_timeout: Floor (seconds) applied to the learned/default timeout.
            Defaults to the tool-agnostic MIN_TIMEOUT. A tool that runs its own
            inner timeout backstop MUST pass a floor strictly greater than that
            backstop — otherwise the outer timeout can fire first and kill the
            run before the inner backstop can report which step hung, leaving an
            opaque timeout instead of a diagnosable one.
        explicit_timeout: Caller-supplied bound (seconds) that overrides the
            persisted learned value. ``None`` means "not supplied" and selects
            the learned path. It does NOT waive ``min_timeout``.

    Returns:
        DirectCommandResult with status (``success`` / ``error`` / ``timeout``
        / ``killed``), exit_code, duration_seconds, log_file, command, and
        optional error/message/timeout_used_seconds fields.
    """
    log_prefix = tool_name.upper()
    extras = dict(extra_result_fields) if extra_result_fields else {}

    # Step 1: Extract scope and create log file
    scope = (scope_fn or _default_scope_fn)(args)
    log_file = create_log_file(tool_name.lower(), scope, plan_id=plan_id)
    if not log_file:
        return {
            'status': 'error',
            'exit_code': -1,
            'duration_seconds': 0,
            'timeout_used_seconds': 0,
            'log_file': '',
            'command': '',
            'error': 'Failed to create log file',
            **extras,
        }

    # Step 2: Resolve the bound — an explicit override wins over the learned
    # value; the caller's floor binds on either path (see the docstring).
    # The source travels with the bound so a timeout or killed result can name
    # which of the paths produced the number it was measured against.
    timeout_seconds, timeout_source = timeout_resolve(command_key, default_timeout, project_dir, explicit_timeout)
    if timeout_seconds < min_timeout:
        timeout_seconds, timeout_source = min_timeout, TIMEOUT_SOURCE_FLOOR

    # Step 3: Build command using tool-specific function
    # log_file is passed so Maven can embed it via -l flag
    cmd_parts, command_str = build_command_fn(wrapper, args, log_file)

    # Step 4: Prepare environment if needed
    env = None
    if env_vars:
        env = os.environ.copy()
        env.update(env_vars)

    # Step 5: Determine working directory
    cwd = working_dir if working_dir else project_dir

    # Step 6: Execute
    start_time = time.time()

    try:
        if capture_strategy == CaptureStrategy.TOOL_LOG_FLAG:
            # Maven uses -l flag; no stdout capture needed
            returncode = _run_bounded(
                cmd_parts,
                timeout_seconds=timeout_seconds,
                stdout=None,
                stderr=None,
                cwd=cwd,
                env=env,
                log_prefix=log_prefix,
                command_str=command_str,
            )
        else:
            # stdout_redirect: pipe stdout+stderr to log file
            with open(log_file, 'w') as log:
                returncode = _run_bounded(
                    cmd_parts,
                    timeout_seconds=timeout_seconds,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    cwd=cwd,
                    env=env,
                    log_prefix=log_prefix,
                    command_str=command_str,
                )
        duration_seconds = int(time.time() - start_time)

        # Step 7: Classify the exit BEFORE learning from it. A child terminated
        # by POSIX signal N is reported as returncode ``-N``, and the outer
        # timeout above did NOT send it (that path raises TimeoutExpired
        # instead). So a negative returncode here is a kill this stack did not
        # decide on — an external one, or a signal the wrapper only forwarded:
        # the build reported nothing, and its elapsed is a truncation of a
        # run that never finished — not a measurement of what this command
        # costs. Feeding that truncation to the adaptive learner would blend a
        # non-measurement into the budget at 20% weight (see
        # ``run_config.compute_weighted_timeout``), so the learner is fed only
        # by a genuine finish. This is a truthfulness rule, not a budget
        # adjustment: no bound, margin, floor, or cap is changed here.
        if returncode < 0:
            log_entry(
                'script',
                'global',
                'ERROR',
                f'[{log_prefix}] Externally killed by signal {-returncode} after {duration_seconds}s: {command_str}',
            )
            return killed_result(  # type: ignore[return-value]
                exit_code=returncode,
                duration_seconds=duration_seconds,
                log_file=log_file,
                command=command_str,
                timeout_used_seconds=timeout_seconds,
                timeout_source=timeout_source,
                command_key=command_key,
                **extras,
            )

        # Step 8: Record duration for adaptive learning (genuine finishes only)
        timeout_set(command_key, duration_seconds, project_dir)

        # Step 9: Return structured result
        if returncode == 0:
            return {
                'status': 'success',
                'exit_code': 0,
                'duration_seconds': duration_seconds,
                'timeout_used_seconds': timeout_seconds,
                'log_file': log_file,
                'command': command_str,
                **extras,
            }
        else:
            return {
                'status': 'error',
                'exit_code': returncode,
                'duration_seconds': duration_seconds,
                'timeout_used_seconds': timeout_seconds,
                'log_file': log_file,
                'command': command_str,
                'error': f'Build failed with exit code {returncode}',
                **extras,
            }

    except subprocess.TimeoutExpired:
        duration_seconds = int(time.time() - start_time)
        log_entry('script', 'global', 'ERROR', f'[{log_prefix}] Timeout after {timeout_seconds}s: {command_str}')
        # Adaptive learning: double the timeout so next run has enough headroom,
        # but cap at MAX_TIMEOUT to prevent exponential growth from successive timeouts.
        timeout_set(command_key, min(timeout_seconds * 2, MAX_TIMEOUT), project_dir)
        return {
            'status': 'timeout',
            'exit_code': -1,
            'duration_seconds': duration_seconds,
            'timeout_used_seconds': timeout_seconds,
            'timeout_source': timeout_source,
            'command_key': command_key,
            'log_file': log_file,
            'command': command_str,
            'error': f'Command timed out after {timeout_seconds} seconds',
            **extras,
        }

    except FileNotFoundError:
        log_entry('script', 'global', 'ERROR', f'[{log_prefix}] Wrapper not found: {wrapper}')
        return {
            'status': 'error',
            'exit_code': -1,
            'duration_seconds': 0,
            'timeout_used_seconds': timeout_seconds,
            'log_file': log_file,
            'command': command_str,
            'error': f'{tool_name} wrapper not found: {wrapper}',
            **extras,
        }

    except OSError as e:
        log_entry('script', 'global', 'ERROR', f'[{log_prefix}] OS error: {e}')
        return {
            'status': 'error',
            'exit_code': -1,
            'duration_seconds': 0,
            'timeout_used_seconds': timeout_seconds,
            'log_file': log_file,
            'command': command_str,
            'error': str(e),
            **extras,
        }
