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

from _build_execute import CaptureStrategy, execute_direct_base
from _build_result import DirectCommandResult
from _build_shared import cmd_run_common
from _build_wrapper import detect_wrapper as _detect_wrapper

# Import parser (underscore prefix = private)
from _maven_cmd_parse import parse_log

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


def _maven_scope_fn(args: str) -> str:
    """Extract scope from Maven -pl argument."""
    if '-pl ' in args:
        try:
            pl_idx = args.index('-pl ') + 4
            return args[pl_idx:].split()[0]
        except (ValueError, IndexError):
            pass
    return 'default'


def _maven_build_command_fn(wrapper: str, args: str, log_file: str) -> tuple[list[str], str]:
    """Build Maven command with -l flag for log file output.

    Maven uses -l <log_file> to direct all output to a file, so the log file
    path is embedded directly in the command parts.
    """
    cmd_parts = [wrapper, '-l', log_file] + args.split()
    command_str = ' '.join(cmd_parts)
    return cmd_parts, command_str


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
    wrapper = detect_wrapper(project_dir)

    return execute_direct_base(
        args=args,
        command_key=command_key,
        default_timeout=default_timeout,
        project_dir=project_dir,
        tool_name='maven',
        build_command_fn=_maven_build_command_fn,
        wrapper=wrapper,
        capture_strategy=CaptureStrategy.MAVEN_LOG_FLAG,
        scope_fn=_maven_scope_fn,
    )



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
