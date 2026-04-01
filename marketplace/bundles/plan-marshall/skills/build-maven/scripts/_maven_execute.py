#!/usr/bin/env python3
"""Maven command execution - foundation layer and run subcommand.

Provides:
- execute_direct(): Foundation API for Maven command execution
- cmd_run(): Run subcommand handler (execute + auto-parse on failure)
- detect_wrapper(): Maven wrapper detection
- get_bash_timeout(): Moved to _build_shared module

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
import time

from _build_result import (
    DirectCommandResult,
    create_log_file,
)
from _build_shared import cmd_run_common
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



# =============================================================================
# Run Subcommand (execute + auto-parse on failure)
# =============================================================================


def cmd_run(args):
    """Handle run subcommand - execute + auto-parse on failure.

    Delegates to execute_direct() for execution and cmd_run_common() for result handling.
    """
    project_dir = getattr(args, 'project_dir', '.')

    # Build command key for timeout learning (use first goal as key)
    command_args = args.command_args
    first_goal = command_args.split()[0] if command_args else 'default'
    command_key = f'maven:{first_goal.replace("-", "_")}'

    # Get timeout in seconds
    timeout_seconds = getattr(args, 'timeout', None) or DEFAULT_TIMEOUT_SECONDS

    # Execute via direct_command foundation layer
    result = execute_direct(
        args=command_args, command_key=command_key, default_timeout=timeout_seconds, project_dir=project_dir
    )

    return cmd_run_common(
        result=result,
        parser_fn=parse_log,
        tool_name='maven',
        output_format=getattr(args, 'format', 'toon'),
        mode=getattr(args, 'mode', 'actionable'),
        project_dir=project_dir,
    )
