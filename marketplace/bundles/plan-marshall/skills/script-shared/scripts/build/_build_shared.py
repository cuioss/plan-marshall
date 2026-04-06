#!/usr/bin/env python3
"""Shared utilities for build-* skills.

Provides command implementations, constants, and factories used across
Maven, Gradle, npm, and Python build skills.

CLI scaffolding (subparser helpers, registration, main) lives in _build_cli.py.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from _build_format import format_json, format_toon
from _build_parse import (
    SEVERITY_ERROR,
    Issue,
    UnitTestSummary,
    filter_warnings,
    generate_summary_from_issues,
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

# ---------------------------------------------------------------------------
# Canonical command generation (merged from _build_commands.py)
# ---------------------------------------------------------------------------

EXECUTOR_PREFIX = 'python3 .plan/execute-script.py'
"""Base executor command shared by all build skills."""


def build_canonical_commands(
    skill_notation: str,
    command_map: dict[str, str],
) -> dict[str, str]:
    """Generate canonical command invocation strings.

    Each entry in command_map maps a canonical command name to its
    tool-specific arguments. This function wraps each with the
    standard executor invocation.

    Args:
        skill_notation: Three-part skill notation (e.g., 'plan-marshall:build-maven:maven').
        command_map: Dict mapping canonical name -> tool-specific command args.
            Example: {'clean': 'clean -pl core', 'verify': 'verify -pl core'}

    Returns:
        Dict mapping canonical name -> full executor command string.
    """
    base = f'{EXECUTOR_PREFIX} {skill_notation} run'
    return {name: f'{base} --command-args "{args}"' for name, args in command_map.items()}


def build_chained_commands(
    skill_notation: str,
    command_list: list[str],
) -> str:
    """Generate a chained command string (cmd1 && cmd2).

    Used by npm's verify command which chains build + test.

    Args:
        skill_notation: Three-part skill notation.
        command_list: List of tool-specific command args to chain.

    Returns:
        Chained command string with ' && ' between each invocation.
    """
    base = f'{EXECUTOR_PREFIX} {skill_notation} run'
    parts = [f'{base} --command-args "{args}"' for args in command_list]
    return ' && '.join(parts)


# Type alias for parser functions.
# Accepts (log_file,) or (log_file, command) and returns (issues, test_summary, build_status).
ParserFn = Callable[..., tuple[list[Issue], UnitTestSummary | None, str]]


def create_subcommand_handler(base_fn: Callable[..., int], **kwargs) -> Callable[..., int]:
    """Generic factory: bind keyword arguments to a base subcommand function.

    Replaces per-subcommand factory functions (create_coverage_report_handler,
    create_check_warnings_handler, etc.) with a single generic pattern.

    The returned handler accepts (args) and delegates to base_fn(args, **kwargs).

    Args:
        base_fn: Base function with signature (args, **config) -> int.
        **kwargs: Configuration arguments to bind to base_fn.

    Returns:
        A handler(args) -> int function ready for argparse set_defaults.

    Example::

        cmd_coverage_report = create_subcommand_handler(
            cmd_coverage_report_base,
            search_paths=[('target/site/jacoco/jacoco.xml', 'jacoco')],
            not_found_message='No JaCoCo XML report found.',
        )
    """

    def handler(args) -> int:
        return base_fn(args, **kwargs)

    return handler


def cmd_parse_common(
    args,
    parse_log_fn: ParserFn,
    *,
    extra_filters: dict[str, Callable[[Issue], bool]] | None = None,
    parser_needs_command: bool = False,
    output_format: str = 'toon',
) -> int:
    """Common parse subcommand logic shared across all build skills.

    Reads a log file, calls the tool-specific parse_log function, applies
    mode filters, and outputs the result in the requested format.

    Args:
        args: Parsed argparse namespace with 'log', 'mode', optional 'format'.
        parse_log_fn: Tool-specific log parser function.
        extra_filters: Additional mode filters beyond 'errors'.
            Maps mode name -> filter predicate (keep issues where predicate is True).
            Example: {'no-openrewrite': lambda i: i.category != 'openrewrite_info'}
        parser_needs_command: If True, passes command string as second arg to parser_fn.
        output_format: Output format ('toon' or 'json'). Overridden by args.format if present.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    log_path = Path(args.log)
    if not log_path.exists():
        print(format_toon({'status': 'error', 'error': f'Log file not found: {args.log}'}))
        return 1

    if parser_needs_command:
        issues, test_summary, build_status = parse_log_fn(log_path, getattr(args, 'command', ''))
    else:
        issues, test_summary, build_status = parse_log_fn(log_path)

    # Apply mode filters
    mode = getattr(args, 'mode', 'structured')
    if mode == 'errors':
        issues = [i for i in issues if i.severity == SEVERITY_ERROR]
    elif extra_filters and mode in extra_filters:
        issues = [i for i in issues if extra_filters[mode](i)]

    summary = generate_summary_from_issues(issues)
    result = {
        'status': 'success' if build_status == 'SUCCESS' else 'error',
        'data': {
            'build_status': build_status,
            'issues': [i.to_dict() for i in issues],
            'summary': summary,
        },
        'metrics': {
            'tests_run': test_summary.total if test_summary else 0,
            'tests_failed': test_summary.failed if test_summary else 0,
        },
    }

    fmt = getattr(args, 'format', None) or output_format
    if fmt == 'toon':
        print(format_toon(result))
    else:
        print(json.dumps(result, indent=2))
    return 0


# Default build timeout in seconds for all build systems.
# Used by ExecuteConfig instances across Maven, Gradle, npm, and Python.
# Related constants in _build_execute.py: MIN_TIMEOUT=60, MAX_TIMEOUT=1800
DEFAULT_BUILD_TIMEOUT = 300

# Buffer added to inner timeout for Bash tool timeout calculation.
# Bash tool timeout = inner script timeout + OUTER_TIMEOUT_BUFFER.
# This prevents the Bash tool from killing the process before the script's
# own timeout handling can produce a structured timeout result.
OUTER_TIMEOUT_BUFFER = 30


def get_bash_timeout(inner_timeout_seconds: int) -> int:
    """Calculate Bash tool timeout with buffer.

    Args:
        inner_timeout_seconds: The shell timeout in seconds.

    Returns:
        Bash tool timeout in seconds (inner + buffer).
    """
    return inner_timeout_seconds + OUTER_TIMEOUT_BUFFER


def cmd_discover_common(args, discover_fn: Callable) -> int:
    """Common discover subcommand logic shared across all build skills.

    Args:
        args: Parsed argparse namespace with 'root' and 'format'.
        discover_fn: Tool-specific discover function.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    try:
        modules = discover_fn(args.root)
        result = {
            'status': 'success',
            'modules': modules,
            'count': len(modules),
        }
        fmt = getattr(args, 'format', 'toon')
        if fmt == 'json':
            print(json.dumps(result, indent=2))
        else:
            print(format_toon(result))
        return 0
    except Exception as e:
        error_output = {'status': 'error', 'error': f'discovery_failed: {e}'}
        fmt = getattr(args, 'format', 'toon')
        if fmt == 'json':
            print(json.dumps(error_output, indent=2))
        else:
            print(format_toon(error_output))
        return 1


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

    Note: Uses format_toon()/format_json() from _build_format for all output.
    Both paths share the same normalization logic — format_toon delegates to
    serialize_toon after ordering fields; format_json normalizes Issue objects.

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
        return 0  # Status modeled in output, not exit code

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

    except Exception as parse_err:
        # If parsing fails, still return the build failure but log the parse error
        print(f'[WARN] Log parsing failed: {parse_err}', file=sys.stderr)
        output = error_result(
            error=ERROR_BUILD_FAILED,
            exit_code=result['exit_code'],
            duration_seconds=result['duration_seconds'],
            log_file=log_file,
            command=command_str,
        )
        print(formatter(output))

    return 0  # Status modeled in output, not exit code
