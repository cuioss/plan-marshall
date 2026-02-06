#!/usr/bin/env python3
"""Python build operations - run command with auto-parse on failure.

Provides:
- execute_direct(): Foundation API for pyprojectx command execution
- cmd_run(): Run subcommand handler (execute + auto-parse on failure)
- detect_wrapper(): Find ./pw wrapper

Usage:
    from python_build import execute_direct, cmd_run

    # Foundation API
    result = execute_direct(
        args="verify",
        command_key="python:verify",
        default_timeout=300
    )

    # Run subcommand (CLI entry point)
    cmd_run(args)  # args from argparse
"""

import argparse
import re
import subprocess
import sys
import time
from pathlib import Path

from _build_format import format_json, format_toon  # type: ignore[import-not-found]
from _build_parse import (  # type: ignore[import-not-found]
    Issue,
    UnitTestSummary,
    filter_warnings,
    load_acceptable_warnings,
    partition_issues,
)
from _build_result import (  # type: ignore[import-not-found]
    ERROR_BUILD_FAILED,
    ERROR_EXECUTION_FAILED,
    ERROR_LOG_FILE_FAILED,
    DirectCommandResult,
    create_log_file,
    error_result,
    success_result,
    timeout_result,
)
from _build_wrapper import detect_wrapper as _detect_wrapper  # type: ignore[import-not-found]
from plan_logging import log_entry  # type: ignore[import-not-found]

# Cross-skill imports (PYTHONPATH set by executor)
from run_config import timeout_get, timeout_set  # type: ignore[import-not-found]

# =============================================================================
# Constants
# =============================================================================

# Default timeout for Python builds (seconds)
DEFAULT_TIMEOUT = 300

# Minimum timeout enforced (seconds)
MIN_TIMEOUT = 60


# =============================================================================
# Wrapper Detection
# =============================================================================


def detect_wrapper(project_dir: str = '.') -> str:
    """Detect pyprojectx wrapper based on platform.

    On Windows: pw.bat > pwx (system)
    On Unix: ./pw > pwx (system)

    Args:
        project_dir: Project root directory.

    Returns:
        Path to wrapper executable.

    Raises:
        FileNotFoundError: If no wrapper is available.
    """
    wrapper = _detect_wrapper(project_dir, 'pw', 'pw.bat', 'pwx')
    if wrapper is None:
        raise FileNotFoundError('No pyprojectx wrapper found (pw, pw.bat, or pwx)')
    return str(wrapper)  # Cast: _detect_wrapper typed as Any due to cross-skill import


# =============================================================================
# execute_direct() - Foundation API
# =============================================================================


def execute_direct(
    args: str,
    command_key: str,
    default_timeout: int = DEFAULT_TIMEOUT,
    project_dir: str = '.',
) -> DirectCommandResult:
    """Execute pyprojectx command with adaptive timeout learning.

    This is the foundation layer for all Python command execution.
    Uses run-config for timeout retrieval and learning.
    Conforms to R1 requirement: all output goes to log file, not memory.

    Args:
        args: Canonical command name (e.g., "verify", "module-tests")
        command_key: Command identifier for timeout learning (e.g., "python:verify")
        default_timeout: Default timeout in seconds if no learned value exists
        project_dir: Project root directory

    Returns:
        DirectCommandResult with:
        - status: "success" | "error" | "timeout"
        - exit_code: int
        - duration_seconds: int
        - log_file: str (path to captured output)
        - command: str
        - timeout_used_seconds: int (optional)
        - wrapper: str (wrapper path used)
        - error: str (on error/timeout only)
    """
    log_entry('script', 'global', 'INFO', f'[PYTHON] Executing: pw {args}')

    # Step 1: Detect wrapper
    try:
        wrapper = detect_wrapper(project_dir)
    except FileNotFoundError as e:
        return {
            'status': 'error',
            'exit_code': -1,
            'duration_seconds': 0,
            'log_file': '',
            'command': f'./pw {args}',
            'error': str(e),
        }

    # Step 2: Get timeout from run-config (with safety margin)
    timeout_seconds = max(timeout_get(command_key, default_timeout, project_dir), MIN_TIMEOUT)

    # Step 3: Build command
    cmd_parts = [wrapper] + args.split()
    command_str = ' '.join(cmd_parts)

    # Step 4: Create log file for output (R1 requirement)
    log_file = create_log_file('python', 'default', project_dir)
    if not log_file:
        return {
            'status': 'error',
            'exit_code': -1,
            'duration_seconds': 0,
            'log_file': '',
            'command': command_str,
            'wrapper': wrapper,
            'error': 'Failed to create log file',
        }

    # Step 5: Execute with output to log file
    start_time = time.time()

    try:
        with open(log_file, 'w') as log:
            result = subprocess.run(
                cmd_parts,
                timeout=timeout_seconds,
                stdout=log,
                stderr=subprocess.STDOUT,
                cwd=project_dir,
            )
        duration_seconds = int(time.time() - start_time)

        # Step 6: Record duration for adaptive learning (only on completion)
        timeout_set(command_key, duration_seconds, project_dir)

        # Step 7: Return structured result
        if result.returncode == 0:
            log_entry('script', 'global', 'INFO', f'[PYTHON] Completed in {duration_seconds}s')
            return {
                'status': 'success',
                'exit_code': 0,
                'duration_seconds': duration_seconds,
                'log_file': log_file,
                'command': command_str,
                'timeout_used_seconds': timeout_seconds,
                'wrapper': wrapper,
            }
        else:
            log_entry('script', 'global', 'ERROR', f'[PYTHON] Failed with exit code {result.returncode}')
            return {
                'status': 'error',
                'exit_code': result.returncode,
                'duration_seconds': duration_seconds,
                'log_file': log_file,
                'command': command_str,
                'timeout_used_seconds': timeout_seconds,
                'wrapper': wrapper,
                'error': f'Build failed with exit code {result.returncode}',
            }

    except subprocess.TimeoutExpired:
        duration_seconds = int(time.time() - start_time)
        log_entry('script', 'global', 'ERROR', f'[PYTHON] Timeout after {timeout_seconds}s')
        return {
            'status': 'timeout',
            'exit_code': -1,
            'duration_seconds': duration_seconds,
            'log_file': log_file,
            'command': command_str,
            'timeout_used_seconds': timeout_seconds,
            'wrapper': wrapper,
            'error': f'Command timed out after {timeout_seconds} seconds',
        }

    except FileNotFoundError:
        return {
            'status': 'error',
            'exit_code': -1,
            'duration_seconds': 0,
            'log_file': log_file,
            'command': command_str,
            'timeout_used_seconds': timeout_seconds,
            'wrapper': wrapper,
            'error': f'Command not found: {wrapper}',
        }

    except OSError as e:
        return {
            'status': 'error',
            'exit_code': -1,
            'duration_seconds': 0,
            'log_file': log_file,
            'command': command_str,
            'timeout_used_seconds': timeout_seconds,
            'wrapper': wrapper,
            'error': str(e),
        }


# =============================================================================
# Log Parsing
# =============================================================================


def parse_python_log(log_file: str) -> tuple[list[Issue], UnitTestSummary | None, str]:
    """Parse Python build log for errors.

    Handles output from:
    - mypy: file.py:line: error: message
    - ruff: file.py:line:col: CODE message
    - pytest: FAILED test_file.py::test_name - ...

    Args:
        log_file: Path to the log file.

    Returns:
        Tuple of (issues, test_summary, build_status)
    """
    issues: list[Issue] = []
    test_summary: UnitTestSummary | None = None
    build_status = 'FAILURE'

    try:
        content = Path(log_file).read_text(encoding='utf-8', errors='replace')
    except OSError:
        return issues, test_summary, build_status

    # Parse mypy errors: file.py:line: error: message
    mypy_pattern = re.compile(r'^(.+\.py):(\d+): error: (.+)$', re.MULTILINE)
    for match in mypy_pattern.finditer(content):
        issues.append(
            Issue(
                file=match.group(1),
                line=int(match.group(2)),
                message=match.group(3),
                category='type_error',
                severity='error',
            )
        )

    # Parse ruff errors: file.py:line:col: CODE message
    ruff_pattern = re.compile(r'^(.+\.py):(\d+):\d+: ([A-Z]+\d+) (.+)$', re.MULTILINE)
    for match in ruff_pattern.finditer(content):
        issues.append(
            Issue(
                file=match.group(1),
                line=int(match.group(2)),
                message=f'{match.group(3)} {match.group(4)}',
                category='lint_error',
                severity='error',
            )
        )

    # Parse pytest failures: FAILED test_file.py::test_name - message
    pytest_pattern = re.compile(r'^FAILED (.+\.py)::(\S+)(?: - (.+))?$', re.MULTILINE)
    for match in pytest_pattern.finditer(content):
        message = match.group(3) if match.group(3) else f'Test {match.group(2)} failed'
        issues.append(
            Issue(
                file=match.group(1),
                line=-1,  # pytest doesn't give line numbers in summary
                message=message,
                category='test_failure',
                severity='error',
            )
        )

    # Parse pytest summary: X passed, Y failed, Z skipped
    summary_pattern = re.compile(r'(\d+) passed(?:.*?(\d+) failed)?(?:.*?(\d+) skipped)?')
    summary_match = summary_pattern.search(content)
    if summary_match:
        passed = int(summary_match.group(1))
        failed = int(summary_match.group(2)) if summary_match.group(2) else 0
        skipped = int(summary_match.group(3)) if summary_match.group(3) else 0
        total = passed + failed + skipped
        test_summary = UnitTestSummary(passed=passed, failed=failed, skipped=skipped, total=total)

    return issues, test_summary, build_status


# =============================================================================
# Run Subcommand (execute + auto-parse on failure)
# =============================================================================


def cmd_run(args: argparse.Namespace) -> int:
    """Handle run subcommand - execute + auto-parse on failure.

    Delegates to execute_direct() for all execution.

    Supports:
    - --format toon (default) or --format json
    - --mode actionable (default), structured, or errors
    """
    project_dir = getattr(args, 'project_dir', '.')
    output_format = getattr(args, 'format', 'toon')
    mode = getattr(args, 'mode', 'actionable')

    # Select formatter based on output format
    formatter = format_json if output_format == 'json' else format_toon

    # Build command key for timeout learning
    command_args = args.command_args
    args_key = command_args.split()[0].replace(' ', '_').replace('-', '_') if command_args else 'default'
    command_key = f'python:{args_key}'

    # Execute via execute_direct foundation layer
    result = execute_direct(
        args=command_args,
        command_key=command_key,
        default_timeout=args.timeout,
        project_dir=project_dir,
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
        issues, test_summary, _ = parse_python_log(log_file)

        # Partition issues into errors and warnings
        errors, warnings = partition_issues(issues)

        # Load acceptable warnings and filter based on mode
        patterns = load_acceptable_warnings(project_dir, 'python')
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


# =============================================================================
# Main
# =============================================================================


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Python/pyprojectx build operations',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    # run subcommand (primary API)
    run_parser = subparsers.add_parser('run', help='Execute build and auto-parse on failure (primary API)')
    run_parser.add_argument(
        '--command-args', dest='command_args',
        required=True,
        help="Canonical command to execute (e.g., 'verify', 'module-tests', 'quality-gate')",
    )
    run_parser.add_argument(
        '--timeout',
        type=int,
        default=DEFAULT_TIMEOUT,
        help=f'Build timeout in seconds (default: {DEFAULT_TIMEOUT})',
    )
    run_parser.add_argument(
        '--mode',
        choices=['actionable', 'structured', 'errors'],
        default='actionable',
        help='Output mode',
    )
    run_parser.add_argument(
        '--format',
        choices=['toon', 'json'],
        default='toon',
        help='Output format',
    )
    run_parser.add_argument(
        '--project-dir',
        dest='project_dir',
        default='.',
        help='Project root directory',
    )
    run_parser.set_defaults(func=cmd_run)

    args = parser.parse_args()
    result: int = args.func(args)
    return result


if __name__ == '__main__':
    sys.exit(main())
