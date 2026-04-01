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
import sys

from _build_coverage_report import create_coverage_report_handler  # type: ignore[import-not-found]
from _build_shared import add_run_subparser  # type: ignore[import-not-found]
from _build_wrapper import detect_wrapper as _detect_wrapper  # type: ignore[import-not-found]
from _python_cmd_parse import parse_python_log  # type: ignore[import-not-found]  # noqa: F401

# Re-export from _python_execute for backward compatibility
from _python_execute import cmd_run, execute_direct  # type: ignore[import-not-found]  # noqa: F401

# =============================================================================
# Constants
# =============================================================================

# Default timeout for Python builds (seconds)
DEFAULT_TIMEOUT = 300

# --- Tool-specific coverage configuration (inlined from former wrapper) ---

cmd_coverage_report = create_coverage_report_handler(
    search_paths=[
        ('coverage.xml', 'cobertura'),
        ('htmlcov/coverage.xml', 'cobertura'),
    ],
    not_found_message='No coverage.py XML report found. Run pytest with --cov --cov-report=xml first.',
)


# =============================================================================
# Wrapper Detection (kept for backward compatibility)
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
    run_parser = add_run_subparser(
        subparsers,
        command_args_help="Canonical command to execute (e.g., 'verify', 'module-tests', 'quality-gate')",
        default_timeout=DEFAULT_TIMEOUT,
    )
    run_parser.set_defaults(func=cmd_run)

    # coverage-report subcommand
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
