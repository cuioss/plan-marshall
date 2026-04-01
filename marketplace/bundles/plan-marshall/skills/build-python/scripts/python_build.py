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
import sys
from pathlib import Path

from _build_execute import CaptureStrategy, execute_direct_base  # type: ignore[import-not-found]
from _build_parse import (  # type: ignore[import-not-found]
    Issue,
    UnitTestSummary,
)
from _build_result import (  # type: ignore[import-not-found]
    DirectCommandResult,
)
from _build_shared import cmd_run_common  # type: ignore[import-not-found]
from _build_wrapper import detect_wrapper as _detect_wrapper  # type: ignore[import-not-found]
from plan_logging import log_entry  # type: ignore[import-not-found]

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


def _python_build_command_fn(wrapper: str, args: str, log_file: str) -> tuple[list[str], str]:
    """Build pyprojectx command."""
    cmd_parts = [wrapper] + args.split()
    command_str = ' '.join(cmd_parts)
    return cmd_parts, command_str


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

    # Detect wrapper early to return a clean error if missing
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

    return execute_direct_base(
        args=args,
        command_key=command_key,
        default_timeout=default_timeout,
        project_dir=project_dir,
        tool_name='python',
        build_command_fn=_python_build_command_fn,
        wrapper=wrapper,
        capture_strategy=CaptureStrategy.STDOUT_REDIRECT,
        min_timeout=MIN_TIMEOUT,
        extra_result_fields={'wrapper': wrapper},
    )


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

    Delegates to execute_direct() for execution and cmd_run_common() for result handling.
    """
    project_dir = getattr(args, 'project_dir', '.')

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

    return cmd_run_common(
        result=result,
        parser_fn=parse_python_log,
        tool_name='python',
        output_format=getattr(args, 'format', 'toon'),
        mode=getattr(args, 'mode', 'actionable'),
        project_dir=project_dir,
    )


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

    # coverage-report subcommand
    from _python_cmd_coverage_report import cmd_coverage_report

    cov_parser = subparsers.add_parser('coverage-report', help='Parse coverage.py XML report')
    cov_parser.add_argument('--project-path', dest='project_path', help='Project directory path')
    cov_parser.add_argument('--report-path', dest='report_path', help='Override coverage XML report path')
    cov_parser.add_argument('--threshold', type=int, default=80, help='Coverage threshold percent (default: 80)')
    cov_parser.set_defaults(func=cmd_coverage_report)

    args = parser.parse_args()
    result: int = args.func(args)
    return result


if __name__ == '__main__':
    sys.exit(main())
