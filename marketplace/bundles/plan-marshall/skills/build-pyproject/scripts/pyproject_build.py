#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Pyproject build operations - run, parse, check warnings, coverage report.

Usage:
    pyproject_build.py run --command-args <args> [options]
    pyproject_build.py parse --log <path> [--mode <mode>]
    pyproject_build.py check-warnings --warnings <json> [--acceptable-warnings <json>]
    pyproject_build.py coverage-report [--project-path <path>] [--threshold <percent>]
    pyproject_build.py --help

Subcommands:
    run             Execute build and auto-parse on failure (primary API)
    parse           Parse pyprojectx build output and categorize issues
    check-warnings  Categorize build warnings against acceptable patterns
    coverage-report Ad-hoc diagnostic parser invoked manually for inspection.
                    NOT part of the default:verify:coverage verify-step
                    pipeline (which uses single-resolver native enforcement via
                    the architecture-resolved `coverage` canonical command, with
                    the pytest --cov-fail-under flag enforcing the threshold
                    inside the build itself). The composer derives the
                    `coverage` matrix role from the `coverage` canonical segment
                    of `default:verify:coverage`; this build skill exposes
                    `coverage` as a `run` canonical so `architecture resolve
                    --command coverage` resolves the executable. Use this
                    subcommand for manual local inspection of coverage.py XML
                    output only.
"""

import json

from _build_check_warnings import create_check_warnings_handler
from _build_cli import (
    add_parse_subparser,
    build_main,
    register_standard_subparsers,
    safe_main,
)
from _build_coverage_report import create_coverage_report_handler
from _build_shared import cmd_parse_common
from _pyproject_cmd_discover import discover_python_modules
from _pyproject_cmd_parse import parse_log, slice_failure_details
from _pyproject_execute import _CONFIG, cmd_run
from toon_parser import serialize_toon

# --- Tool-specific configuration inlined from former wrapper files ---

cmd_coverage_report = create_coverage_report_handler(
    search_paths=[
        ('coverage.xml', 'cobertura'),
        ('htmlcov/coverage.xml', 'cobertura'),
    ],
    not_found_message='No coverage.py XML report found. Run pytest with --cov --cov-report=xml first.',
)

cmd_check_warnings = create_check_warnings_handler(
    matcher='substring',
)


def cmd_parse(args) -> int:
    """Parse handler with optional per-signature failure-detail slicing.

    With neither slice flag set, behaves EXACTLY like the standard parse
    (delegates to ``cmd_parse_common``). With ``--failures-detail`` (all failing
    tests, deduped by signature) or ``--test <name>`` (one named test), returns
    the traceback slice(s) so a leaf never re-scans the raw log by hand. Both
    flags are additive; the existing ``--mode`` / ``--format`` surface is
    unchanged.
    """
    if getattr(args, 'failures_detail', False) or getattr(args, 'test_name', None):
        result = slice_failure_details(
            args.log,
            test_name=getattr(args, 'test_name', None),
            failures_detail=getattr(args, 'failures_detail', False),
        )
        fmt = getattr(args, 'format', None) or 'toon'
        if fmt == 'json':
            print(json.dumps(result, indent=2))
        else:
            print(serialize_toon(result))
        return 0 if result.get('status') == 'success' else 1
    return cmd_parse_common(args, parse_log)


def _register_pyproject_parse(subparsers) -> None:
    """Register the pyproject ``parse`` subcommand with the two additive
    failure-detail slice flags layered on the standard parse surface."""
    parse_parser = add_parse_subparser(
        subparsers,
        parse_log,
        help_text='Parse pyprojectx build output and categorize issues',
    )
    parse_parser.add_argument(
        '--failures-detail',
        action='store_true',
        dest='failures_detail',
        help='Slice the deduped per-signature traceback detail for ALL failing tests',
    )
    parse_parser.add_argument(
        '--test',
        dest='test_name',
        default=None,
        help='Slice the traceback detail for one named failing test',
    )
    parse_parser.set_defaults(func=cmd_parse)


def main() -> int:
    """Main entry point."""
    return build_main(
        'Python/pyprojectx (build-pyproject) build operations',
        register_standard_subparsers(
            run_handler=cmd_run,
            run_args_help="Canonical command to execute (e.g., 'compile', 'verify', 'module-tests', 'quality-gate', 'coverage')",
            parse_handler=None,
            coverage_handler=cmd_coverage_report,
            coverage_help='Parse coverage.py XML report',
            check_warnings_handler=cmd_check_warnings,
            discover_handler=discover_python_modules,
            discover_help='Discover Python modules',
            run_config_key_config=_CONFIG,
            extra_register_fns=[_register_pyproject_parse],
        ),
    )


if __name__ == '__main__':
    safe_main(main)()
