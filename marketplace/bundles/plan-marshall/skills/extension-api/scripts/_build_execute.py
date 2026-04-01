#!/usr/bin/env python3
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
        scope_fn=my_scope_fn,
        capture_strategy=CaptureStrategy.MAVEN_LOG_FLAG,
    )
"""

from __future__ import annotations

import os
import subprocess
import time
from collections.abc import Callable
from enum import Enum

from _build_result import DirectCommandResult, create_log_file
from plan_logging import log_entry
from run_config import timeout_get, timeout_set


# Minimum timeout floor (seconds) — prevents adaptive learning from producing
# dangerously short timeouts (e.g., a warm cache run teaching 5s that then
# fails on a cold start).
MIN_TIMEOUT = 60


class CaptureStrategy(Enum):
    """How build output is captured to the log file."""

    STDOUT_REDIRECT = 'stdout_redirect'
    """Redirect stdout/stderr to log file via open() (Gradle, npm, Python)."""

    MAVEN_LOG_FLAG = 'maven_log_flag'
    """Use Maven's -l flag; subprocess gets capture_output=False."""


# Type for build command function: (wrapper, args, log_file) -> (cmd_parts, command_str)
# log_file is passed so tools like Maven can embed it via -l flag.
BuildCommandFn = Callable[[str, str, str], tuple[list[str], str]]

# Type for scope extraction function: (args) -> scope string
ScopeFn = Callable[[str], str]


def _default_scope_fn(args: str) -> str:
    """Default scope extraction - always returns 'default'."""
    return 'default'


def execute_direct_base(
    args: str,
    command_key: str,
    default_timeout: int,
    project_dir: str,
    tool_name: str,
    build_command_fn: BuildCommandFn,
    wrapper: str,
    capture_strategy: CaptureStrategy = CaptureStrategy.STDOUT_REDIRECT,
    scope_fn: ScopeFn | None = None,
    env_vars: dict[str, str] | None = None,
    working_dir: str | None = None,
    extra_result_fields: dict | None = None,
) -> DirectCommandResult:
    """Execute a build command with adaptive timeout learning.

    This is the shared foundation layer for all build system command execution.
    Handles log file creation, timeout management, subprocess execution, and
    structured result construction.

    Args:
        args: Complete command arguments with all routing embedded.
        command_key: Command identifier for timeout learning (e.g., "maven:verify").
        default_timeout: Default timeout in seconds if no learned value exists.
        project_dir: Project root directory.
        tool_name: Build system name for logging prefix (e.g., "MAVEN", "GRADLE").
        build_command_fn: Callable(wrapper, args, log_file) -> (cmd_parts, command_str).
            Constructs the tool-specific command line. log_file is passed so
            tools like Maven can embed it via -l flag.
        wrapper: Resolved wrapper/executable path.
        capture_strategy: How output is captured to the log file.
        scope_fn: Callable(args) -> scope string for log file scoping.
            Defaults to returning 'default'.
        env_vars: Additional environment variables to inject.
        working_dir: Working directory override (defaults to project_dir).
        extra_result_fields: Additional fields to include in all result dicts
            (e.g., {"wrapper": "./mvnw"} or {"command_type": "npm"}).

    Returns:
        DirectCommandResult with status, exit_code, duration_seconds,
        log_file, command, and optional error/timeout_used_seconds fields.
    """
    log_prefix = tool_name.upper()
    extras = dict(extra_result_fields) if extra_result_fields else {}

    # Step 1: Extract scope and create log file
    scope = (scope_fn or _default_scope_fn)(args)
    log_file = create_log_file(tool_name.lower(), scope, project_dir)
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

    # Step 2: Get timeout from run-config, enforce minimum floor
    timeout_seconds = max(timeout_get(command_key, default_timeout, project_dir), MIN_TIMEOUT)

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
        if capture_strategy == CaptureStrategy.MAVEN_LOG_FLAG:
            # Maven uses -l flag; no stdout capture needed
            result = subprocess.run(
                cmd_parts,
                timeout=timeout_seconds,
                capture_output=False,
                check=False,
                cwd=cwd,
                env=env,
            )
        else:
            # stdout_redirect: pipe stdout+stderr to log file
            with open(log_file, 'w') as log:
                result = subprocess.run(
                    cmd_parts,
                    timeout=timeout_seconds,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    cwd=cwd,
                    env=env,
                )
        duration_seconds = int(time.time() - start_time)

        # Step 7: Record duration for adaptive learning
        timeout_set(command_key, duration_seconds, project_dir)

        # Step 8: Return structured result
        if result.returncode == 0:
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
                'exit_code': result.returncode,
                'duration_seconds': duration_seconds,
                'timeout_used_seconds': timeout_seconds,
                'log_file': log_file,
                'command': command_str,
                'error': f'Build failed with exit code {result.returncode}',
                **extras,
            }

    except subprocess.TimeoutExpired:
        duration_seconds = int(time.time() - start_time)
        log_entry('script', 'global', 'ERROR', f'[{log_prefix}] Timeout after {timeout_seconds}s: {command_str}')
        # Adaptive learning: double the timeout so next run has enough headroom
        timeout_set(command_key, timeout_seconds * 2, project_dir)
        return {
            'status': 'timeout',
            'exit_code': -1,
            'duration_seconds': duration_seconds,
            'timeout_used_seconds': timeout_seconds,
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
            'error': f'{tool_name.capitalize()} wrapper not found: {wrapper}',
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
