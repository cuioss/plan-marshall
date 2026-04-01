#!/usr/bin/env python3
"""Gradle command execution - foundation layer and run subcommand.

Provides:
- execute_direct(): Foundation API for Gradle command execution
- cmd_run(): Run subcommand handler (execute + auto-parse on failure)
- detect_wrapper(): Gradle wrapper detection
- get_bash_timeout(): Moved to _build_shared module

Usage:
    from gradle_execute import execute_direct, cmd_run

    # Foundation API
    result = execute_direct(
        args="build",
        command_key="gradle:build",
        default_timeout=300
    )

    # Run subcommand (used by gradle.py CLI dispatcher)
    cmd_run(args)  # args from argparse
"""

from _build_execute import CaptureStrategy, execute_direct_base
from _build_result import DirectCommandResult
from _build_shared import cmd_run_common
from _build_wrapper import detect_wrapper as _detect_wrapper

# Import parser (underscore prefix = private)
from _gradle_cmd_parse import parse_log

# =============================================================================
# Constants
# =============================================================================

# Default timeout in seconds for Gradle builds
DEFAULT_TIMEOUT_SECONDS = 300



# =============================================================================
# API Functions (no argparse dependency)
# =============================================================================


def detect_wrapper(project_dir: str = '.') -> str:
    """Detect Gradle wrapper based on platform.

    On Windows: gradlew.bat > gradle (system)
    On Unix: ./gradlew > gradle (system)

    Args:
        project_dir: Project root directory.

    Returns:
        Path to wrapper script or 'gradle' if no wrapper found.
    """
    wrapper = _detect_wrapper(project_dir, 'gradlew', 'gradlew.bat', 'gradle')
    return wrapper or 'gradle'  # Return gradle even if not found, let execution fail with clear error


def _gradle_scope_fn(args: str) -> str:
    """Extract scope from Gradle :module:task prefix."""
    if args.startswith(':'):
        parts = args.split(':')
        if len(parts) >= 2:
            return parts[1]
    return 'default'


def _gradle_build_command_fn(wrapper: str, args: str, log_file: str) -> tuple[list[str], str]:
    """Build Gradle command with --console=plain for parseable output."""
    cmd_parts = [wrapper] + args.split() + ['--console=plain']
    command_str = ' '.join(cmd_parts)
    return cmd_parts, command_str


def execute_direct(
    args: str, command_key: str, default_timeout: int = 300, project_dir: str = '.'
) -> DirectCommandResult:
    """Execute Gradle command with log file output and adaptive timeout learning.

    This is the foundation layer for all Gradle command execution.
    Captures output to log file and uses run-config for timeout learning.

    Note: The timeout system enforces a minimum of 120 seconds (via run-config)
    to prevent unreasonably short timeouts from warm daemon runs affecting cold starts.

    Args:
        args: Complete Gradle command arguments with all routing embedded
              (e.g., ":module:build" or "build" for root project)
        command_key: Command identifier for timeout learning (e.g., "gradle:build")
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
    wrapper = detect_wrapper(project_dir)

    return execute_direct_base(
        args=args,
        command_key=command_key,
        default_timeout=default_timeout,
        project_dir=project_dir,
        tool_name='gradle',
        build_command_fn=_gradle_build_command_fn,
        wrapper=wrapper,
        capture_strategy=CaptureStrategy.STDOUT_REDIRECT,
        scope_fn=_gradle_scope_fn,
    )



# =============================================================================
# Run Subcommand (execute + auto-parse on failure)
# =============================================================================


def cmd_run(args):
    """Handle run subcommand - execute + auto-parse on failure.

    Delegates to execute_direct() for execution and cmd_run_common() for result handling.
    """
    project_dir = getattr(args, 'project_dir', '.')

    # Build command key for timeout learning (use first task as key)
    command_args = args.command_args
    first_task = command_args.split()[0] if command_args else 'default'
    # Clean up task name for command key (remove leading colons)
    task_name = first_task.lstrip(':').replace(':', '_')
    command_key = f'gradle:{task_name}'

    # Get timeout in seconds
    timeout_seconds = getattr(args, 'timeout', None) or DEFAULT_TIMEOUT_SECONDS

    # Execute via direct_command foundation layer
    result = execute_direct(
        args=command_args, command_key=command_key, default_timeout=timeout_seconds, project_dir=project_dir
    )

    return cmd_run_common(
        result=result,
        parser_fn=parse_log,
        tool_name='gradle',
        output_format=getattr(args, 'format', 'toon'),
        mode=getattr(args, 'mode', 'actionable'),
        project_dir=project_dir,
    )
