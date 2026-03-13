#!/usr/bin/env python3
"""Maven command execution - foundation layer and run subcommand.

Provides:
- execute_direct(): Foundation API for Maven command execution
- cmd_run(): Run subcommand handler (execute + auto-parse on failure)
- detect_wrapper(): Maven wrapper detection
- get_bash_timeout(): Bash tool timeout calculation

Usage:
    from maven_execute import execute_direct, cmd_run

    # Foundation API
    result = execute_direct(
        args="clean verify",
        command_key="maven:verify",
        default_timeout=300
    )

    # Run subcommand (used by maven.py CLI dispatcher)
    cmd_run(args)  # args from argparse
"""

import subprocess
import sys
import time

from _build_format import format_json, format_toon
from _build_parse import (
    filter_warnings,
    load_acceptable_warnings,
    partition_issues,
)
from _build_result import (
    ERROR_BUILD_FAILED,
    ERROR_EXECUTION_FAILED,
    ERROR_LOG_FILE_FAILED,
    DirectCommandResult,
    create_log_file,
    error_result,
    success_result,
    timeout_result,
)
from _build_wrapper import detect_wrapper as _detect_wrapper

# Import parser (underscore prefix = private)
from _maven_cmd_parse import parse_log
from plan_logging import log_entry

# Direct imports - executor sets up PYTHONPATH for cross-skill imports
from run_config import timeout_get, timeout_set

# =============================================================================
# Constants
# =============================================================================

# Default timeout in seconds for Maven builds
DEFAULT_TIMEOUT_SECONDS = 300

# Bash tool outer timeout buffer (seconds) - ensures outer > inner
OUTER_TIMEOUT_BUFFER = 30


# =============================================================================
# API Functions (no argparse dependency)
# =============================================================================


def detect_wrapper(project_dir: str = '.') -> str:
    """Detect Maven wrapper based on platform.

    On Windows: mvnw.cmd > mvn (system)
    On Unix: ./mvnw > mvn (system)

    Args:
        project_dir: Project root directory.

    Returns:
        Path to wrapper script or 'mvn' if no wrapper found.
    """
    wrapper = _detect_wrapper(project_dir, 'mvnw', 'mvnw.cmd', 'mvn')
    return wrapper or 'mvn'


def execute_direct(
    args: str, command_key: str, default_timeout: int = 300, project_dir: str = '.'
) -> DirectCommandResult:
    """Execute Maven command with log file output and adaptive timeout learning.

    This is the foundation layer for all Maven command execution.
    Uses Maven's -l flag for output capture and run-config for timeout learning.

    Note: The timeout system enforces a minimum of 120 seconds (via run-config)
    to prevent unreasonably short timeouts from warm JVM runs affecting cold starts.

    Args:
        args: Complete Maven command arguments with all routing embedded
              (e.g., "verify -Ppre-commit -pl my-module")
        command_key: Command identifier for timeout learning (e.g., "maven:verify")
        default_timeout: Default timeout in seconds if no learned value exists
        project_dir: Project root directory

    Returns:
        Dict with execution result:
        {
            "status": "success" | "error" | "timeout",
            "exit_code": int,
            "duration_seconds": int,
            "timeout_used_seconds": int,
            "log_file": str,
            "command": str,
            "error": str (on error only)
        }
    """
    # Step 1: Create log file in standard location
    # Extract module from -pl argument if present for scoped log files
    scope = 'default'
    if '-pl ' in args:
        try:
            pl_idx = args.index('-pl ') + 4
            scope = args[pl_idx:].split()[0]
        except (ValueError, IndexError):
            pass
    log_file = create_log_file('maven', scope, project_dir)
    if not log_file:
        return {
            'status': 'error',
            'exit_code': -1,
            'duration_seconds': 0,
            'timeout_used_seconds': 0,
            'log_file': '',
            'command': '',
            'error': 'Failed to create log file',
        }

    # Step 2: Detect wrapper
    wrapper = detect_wrapper(project_dir)

    # Step 3: Get timeout from run-config (enforces minimum of 120 seconds)
    timeout_seconds = timeout_get(command_key, default_timeout, project_dir)

    # Step 4: Build command with -l flag for log file output
    # args is complete and self-contained (includes all routing like -pl, -P)
    cmd_parts = [wrapper, '-l', log_file] + args.split()
    command_str = ' '.join(cmd_parts)

    # Step 5: Execute (output goes to log file, not captured)
    start_time = time.time()

    try:
        result = subprocess.run(
            cmd_parts,
            timeout=timeout_seconds,
            capture_output=False,  # Output goes to log file via -l
            check=False,
            cwd=project_dir,
        )
        duration_seconds = int(time.time() - start_time)

        # Step 6: Record duration for adaptive learning
        timeout_set(command_key, duration_seconds, project_dir)

        # Step 7: Return structured result
        if result.returncode == 0:
            return {
                'status': 'success',
                'exit_code': 0,
                'duration_seconds': duration_seconds,
                'timeout_used_seconds': timeout_seconds,
                'log_file': log_file,
                'command': command_str,
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
            }

    except subprocess.TimeoutExpired:
        duration_seconds = int(time.time() - start_time)
        log_entry('script', 'global', 'ERROR', f'[MAVEN-EXECUTE] Timeout after {timeout_seconds}s: {command_str}')
        return {
            'status': 'timeout',
            'exit_code': -1,
            'duration_seconds': duration_seconds,
            'timeout_used_seconds': timeout_seconds,
            'log_file': log_file,
            'command': command_str,
            'error': f'Command timed out after {timeout_seconds} seconds',
        }

    except FileNotFoundError:
        log_entry('script', 'global', 'ERROR', f'[MAVEN-EXECUTE] Wrapper not found: {wrapper}')
        return {
            'status': 'error',
            'exit_code': -1,
            'duration_seconds': 0,
            'timeout_used_seconds': timeout_seconds,
            'log_file': log_file,
            'command': command_str,
            'error': f'Maven wrapper not found: {wrapper}',
        }

    except OSError as e:
        log_entry('script', 'global', 'ERROR', f'[MAVEN-EXECUTE] OS error: {e}')
        return {
            'status': 'error',
            'exit_code': -1,
            'duration_seconds': 0,
            'timeout_used_seconds': timeout_seconds,
            'log_file': log_file,
            'command': command_str,
            'error': str(e),
        }


def get_bash_timeout(inner_timeout_seconds: int) -> int:
    """Calculate Bash tool timeout with buffer.

    The Bash tool has a default 120-second timeout. For long-running builds,
    we need to set the outer timeout higher than the inner (shell) timeout.

    Args:
        inner_timeout_seconds: The shell timeout in seconds.

    Returns:
        Bash tool timeout in seconds (inner + buffer).
    """
    return inner_timeout_seconds + OUTER_TIMEOUT_BUFFER


# =============================================================================
# Run Subcommand (execute + auto-parse on failure)
# =============================================================================


def cmd_run(args):
    """Handle run subcommand - execute + auto-parse on failure.

    Delegates to execute_direct() for all Maven execution.
    """
    project_dir = getattr(args, 'project_dir', '.')
    output_format = getattr(args, 'format', 'toon')
    mode = getattr(args, 'mode', 'actionable')

    # Select formatter based on output format
    formatter = format_json if output_format == 'json' else format_toon

    # Build command key for timeout learning (use first goal as key)
    command_args = args.command_args
    first_goal = command_args.split()[0] if command_args else 'default'
    command_key = f'maven:{first_goal.replace("-", "_")}'

    # Get timeout (convert ms to seconds if needed)
    if hasattr(args, 'timeout') and args.timeout:
        timeout_seconds = args.timeout // 1000 if args.timeout > 1000 else args.timeout
    else:
        timeout_seconds = DEFAULT_TIMEOUT_SECONDS

    # Execute via direct_command foundation layer
    # command-args is complete and self-contained (includes -pl, -P, etc.)
    result = execute_direct(
        args=command_args, command_key=command_key, default_timeout=timeout_seconds, project_dir=project_dir
    )

    log_file = result['log_file']
    command_str = result['command']
    print(f'[EXEC] {command_str}', file=sys.stderr)

    # Handle execution errors (wrapper not found, log file creation failed)
    if result['status'] == 'error' and result['exit_code'] == -1:
        error_type = ERROR_EXECUTION_FAILED
        if 'log file' in result.get('error', '').lower():
            error_type = ERROR_LOG_FILE_FAILED

        output = error_result(
            error=error_type,
            exit_code=-1,
            duration_seconds=0,
            log_file=log_file,
            command=command_str,
        )
        print(formatter(output))
        return 1

    # Handle timeout
    if result['status'] == 'timeout':
        output = timeout_result(
            timeout_used_seconds=result['timeout_used_seconds'],
            duration_seconds=result['duration_seconds'],
            log_file=log_file,
            command=command_str,
        )
        print(formatter(output))
        return 1

    # Success case
    if result['status'] == 'success':
        output = success_result(
            duration_seconds=result['duration_seconds'],
            log_file=log_file,
            command=command_str,
        )
        print(formatter(output))
        return 0

    # Build failed - parse the log file for errors
    try:
        issues, test_summary, build_status = parse_log(log_file)

        # Partition issues into errors and warnings
        errors, warnings = partition_issues(issues)

        # Load acceptable warnings and filter based on mode
        patterns = load_acceptable_warnings(project_dir, 'maven')
        filtered_warnings = filter_warnings(warnings, patterns, mode)

        # Build result dict
        output = error_result(
            error=ERROR_BUILD_FAILED,
            exit_code=result['exit_code'],
            duration_seconds=result['duration_seconds'],
            log_file=log_file,
            command=command_str,
        )

        # Add errors if present
        if errors:
            output['errors'] = errors[:20]

        # Add warnings if present (mode != errors already handled by filter_warnings)
        if filtered_warnings:
            output['warnings'] = filtered_warnings[:10]

        # Add test summary if present
        if test_summary:
            output['tests'] = test_summary

        print(formatter(output))

    except Exception:
        # If parsing fails, still return the build failure
        output = error_result(
            error=ERROR_BUILD_FAILED,
            exit_code=result['exit_code'],
            duration_seconds=result['duration_seconds'],
            log_file=log_file,
            command=command_str,
        )
        print(formatter(output))

    return 1
