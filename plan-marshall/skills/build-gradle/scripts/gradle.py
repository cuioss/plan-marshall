#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""
Gradle build operations - run, parse, find projects, check warnings, coverage report.

Usage:
    gradle.py run --command-args <args> [--format toon|json] [--mode actionable|structured|errors] [options]
    gradle.py parse --log <path> [--mode <mode>]
    gradle.py find-project --project-name <name> | --project-path <path>
    gradle.py check-warnings --warnings <json> [--acceptable-warnings <json>]
    gradle.py coverage-report [--project-path <path>] [--threshold <percent>]
    gradle.py --help

Subcommands:
    run             Execute build and auto-parse on failure (primary API)
    parse           Parse Gradle build output and categorize issues
    find-project    Find Gradle project path from project name
    check-warnings  Categorize build warnings against acceptable patterns
    coverage-report Parse JaCoCo coverage report
"""

from _build_check_warnings import create_check_warnings_handler
from _build_cli import (
    add_project_dir_arg,
    add_root_arg,
    build_main,
    register_standard_subparsers,
    resolve_root_arg,
    safe_main,
)
from _build_coverage_report import create_coverage_report_handler
from _gradle_cmd_discover import discover_gradle_modules
from _gradle_cmd_find_project import cmd_find_project
from _gradle_cmd_parse import parse_log
from _gradle_execute import _CONFIG, cmd_run

# --- Tool-specific configuration inlined from former wrapper files ---

cmd_coverage_report = create_coverage_report_handler(
    search_paths=[
        ('build/reports/jacoco/test/jacocoTestReport.xml', 'jacoco'),
        ('build/reports/jacoco/jacocoTestReport.xml', 'jacoco'),
        ('build/jacoco/test.xml', 'jacoco'),
    ],
    not_found_message='No JaCoCo XML report found. Run coverage build first.',
)

cmd_check_warnings = create_check_warnings_handler(
    matcher='wildcard',
)


def _register_find_project(subparsers):
    """Register the wrapper-local 'find-project' subcommand.

    Built here rather than through the shared ``register_standard_subparsers``
    helper, so it attaches the canonical ``--project-dir`` / ``--plan-id``
    routing pair by calling the shared ``add_project_dir_arg`` — the pair keeps
    exactly one declaration site. ``--root`` uses the same sentinel-default
    precedence rule the shared ``discover`` registration uses (explicit
    ``--root`` wins, otherwise the resolved routing root applies).
    ``--project-path`` is a distinct flag inside the mutually-exclusive
    selector group and is untouched by the pair.
    """
    find_parser = subparsers.add_parser(
        'find-project', help='Find Gradle project path from project name', allow_abbrev=False
    )
    find_group = find_parser.add_mutually_exclusive_group(required=True)
    find_group.add_argument('--project-name', help='Project name to search for')
    find_group.add_argument('--project-path', help='Explicit project path to validate')
    add_root_arg(find_parser)
    add_project_dir_arg(find_parser)

    def _cmd_find_project(args):
        # ``build_main`` has already rewritten ``args.project_dir`` to the
        # resolved routing root; collapse the two sources to the single value
        # ``cmd_find_project`` reads.
        args.root = resolve_root_arg(args)
        return cmd_find_project(args)

    find_parser.set_defaults(func=_cmd_find_project)


def main() -> int:
    """Main entry point."""
    return build_main(
        'Gradle build operations',
        register_standard_subparsers(
            run_handler=cmd_run,
            run_args_help="Complete Gradle command arguments (e.g., ':module:build' or 'build')",
            parse_handler=parse_log,
            parse_help='Parse Gradle build output and categorize issues',
            parse_extra_modes=['no-openrewrite'],
            parse_extra_filters={'no-openrewrite': lambda i: i.category != 'openrewrite_info'},
            coverage_handler=cmd_coverage_report,
            coverage_help='Parse JaCoCo coverage report',
            check_warnings_handler=cmd_check_warnings,
            discover_handler=discover_gradle_modules,
            discover_help='Discover Gradle modules',
            run_config_key_config=_CONFIG,
            extra_register_fns=[
                _register_find_project,
            ],
        ),
    )


if __name__ == '__main__':
    safe_main(main)()
