#!/usr/bin/env python3
"""Shared utilities for build-* skills.

Provides common functions used across Maven, Gradle, npm, and Python build skills
to avoid duplication.
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from typing import Any

from _build_format import format_json, format_toon
from _build_parse import (
    Issue,
    UnitTestSummary,
    filter_warnings,
    load_acceptable_warnings,
    partition_issues,
)
from _build_result import (
    ERROR_BUILD_FAILED,
    ERROR_EXECUTION_FAILED,
    ERROR_LOG_FILE_FAILED,
    DirectCommandResult,
    error_result,
    success_result,
    timeout_result,
)

# Type alias for parser functions.
# Accepts (log_file,) or (log_file, command) and returns (issues, test_summary, build_status).
ParserFn = Callable[..., tuple[list[Issue], UnitTestSummary | None, str]]

# Buffer added to inner timeout for Bash tool timeout calculation.
# The Bash tool has a default 120-second timeout. For long-running builds,
# the outer timeout must be higher than the inner (shell) timeout.
OUTER_TIMEOUT_BUFFER = 30


def get_bash_timeout(inner_timeout_seconds: int) -> int:
    """Calculate Bash tool timeout with buffer.

    Args:
        inner_timeout_seconds: The shell timeout in seconds.

    Returns:
        Bash tool timeout in seconds (inner + buffer).
    """
    return inner_timeout_seconds + OUTER_TIMEOUT_BUFFER


def add_run_subparser(
    subparsers,
    *,
    command_args_help: str = "Complete command arguments",
    default_timeout: int = 300,
    extra_args_fn=None,
):
    """Add standard 'run' subparser with common arguments.

    All build skills share the same run subparser pattern:
    --command-args, --timeout, --mode, --format, --project-dir.

    Args:
        subparsers: argparse subparsers object.
        command_args_help: Help text for --command-args.
        default_timeout: Default timeout in seconds.
        extra_args_fn: Optional callable(run_parser) to add tool-specific args
            (e.g., --working-dir, --env for npm).

    Returns:
        The created run subparser (for setting defaults like func=cmd_run).
    """
    run_parser = subparsers.add_parser('run', help='Execute build and auto-parse on failure (primary API)')
    run_parser.add_argument(
        '--command-args', dest='command_args', required=True, help=command_args_help,
    )
    run_parser.add_argument(
        '--timeout', type=int, default=default_timeout,
        help=f'Build timeout in seconds (default: {default_timeout})',
    )
    run_parser.add_argument(
        '--mode', choices=['actionable', 'structured', 'errors'], default='actionable', help='Output mode',
    )
    run_parser.add_argument(
        '--format', choices=['toon', 'json'], default='toon', help='Output format (default: toon)',
    )
    run_parser.add_argument(
        '--project-dir', dest='project_dir', default='.', help='Project root directory',
    )
    if extra_args_fn:
        extra_args_fn(run_parser)
    return run_parser


def add_coverage_subparser(subparsers, *, help_text: str = 'Parse coverage report', default_threshold: int = 80):
    """Add standard 'coverage-report' subparser with common arguments.

    Args:
        subparsers: argparse subparsers object.
        help_text: Help text for the subparser.
        default_threshold: Default coverage threshold percent.

    Returns:
        The created coverage-report subparser.
    """
    cov_parser = subparsers.add_parser('coverage-report', help=help_text)
    cov_parser.add_argument('--project-path', dest='project_path', help='Project or module directory path')
    cov_parser.add_argument('--report-path', dest='report_path', help='Override coverage report path')
    cov_parser.add_argument(
        '--threshold', type=int, default=default_threshold, help=f'Coverage threshold percent (default: {default_threshold})',
    )
    return cov_parser


def cmd_run_common(
    result: DirectCommandResult,
    parser_fn: ParserFn,
    tool_name: str,
    output_format: str = 'toon',
    mode: str = 'actionable',
    project_dir: str = '.',
    parser_needs_command: bool = False,
) -> int:
    """Common cmd_run logic shared across all build skills.

    Handles the execute_direct() result: routes success/error/timeout to
    the appropriate formatter and parses build failures for structured errors.

    Args:
        result: DirectCommandResult from execute_direct().
        parser_fn: Log parser function. Called as parser_fn(log_file) or
            parser_fn(log_file, command) depending on parser_needs_command.
        tool_name: Build tool name for acceptable warnings lookup
            (e.g., 'maven', 'gradle', 'npm', 'python').
        output_format: Output format ('toon' or 'json').
        mode: Output mode ('actionable', 'structured', 'errors').
        project_dir: Project root directory for warning pattern lookup.
        parser_needs_command: If True, passes command string as second arg to parser_fn.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    formatter = format_json if output_format == 'json' else format_toon

    log_file = result['log_file']
    command_str = result['command']
    print(f'[EXEC] {command_str}', file=sys.stderr)

    # Handle execution errors (wrapper not found, log file creation failed)
    if result['status'] == 'error' and result['exit_code'] == -1:
        error_type = ERROR_EXECUTION_FAILED
        if 'log file' in result.get('error', '').lower():
            error_type = ERROR_LOG_FILE_FAILED

        err_output = error_result(
            error=error_type,
            exit_code=-1,
            duration_seconds=0,
            log_file=log_file,
            command=command_str,
        )
        print(formatter(err_output))
        return 1

    # Handle timeout
    if result['status'] == 'timeout':
        timeout_output = timeout_result(
            timeout_used_seconds=result['timeout_used_seconds'],
            duration_seconds=result['duration_seconds'],
            log_file=log_file,
            command=command_str,
        )
        print(formatter(timeout_output))
        return 1

    # Success case
    if result['status'] == 'success':
        success_output = success_result(
            duration_seconds=result['duration_seconds'],
            log_file=log_file,
            command=command_str,
        )
        print(formatter(success_output))
        return 0

    # Build failed - parse the log file for errors
    try:
        if parser_needs_command:
            issues, test_summary, build_status = parser_fn(log_file, command_str)
        else:
            issues, test_summary, build_status = parser_fn(log_file)

        # Partition issues into errors and warnings
        errors, warnings = partition_issues(issues)

        # Load acceptable warnings and filter based on mode
        patterns = load_acceptable_warnings(project_dir, tool_name)
        filtered_warnings = filter_warnings(warnings, patterns, mode)

        # Build result dict
        output: dict[str, Any] = error_result(
            error=ERROR_BUILD_FAILED,
            exit_code=result['exit_code'],
            duration_seconds=result['duration_seconds'],
            log_file=log_file,
            command=command_str,
        )

        # Add errors if present
        if errors:
            output['errors'] = errors[:20]

        # Add warnings if present
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
