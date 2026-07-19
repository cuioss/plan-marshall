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
    run                 Execute build and auto-parse on failure (primary API)
    parse               Parse pyprojectx build output and categorize issues
    check-warnings      Categorize build warnings against acceptable patterns
    resolve-test-scope  Resolve the scoped module set and scoped-vs-whole-tree
                        divergence risk for the live footprint (consumed by the
                        phase-6-finalize whole-tree module-tests divergence gate)
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
    add_project_dir_arg,
    build_main,
    register_standard_subparsers,
    safe_main,
)
from _build_coverage_report import create_coverage_report_handler
from _build_shared import cmd_parse_common
from _pyproject_cmd_discover import discover_python_modules
from _pyproject_cmd_parse import parse_log, slice_failure_details
from _pyproject_execute import _CONFIG, cmd_run
from _test_scope_divergence import resolve_test_scope
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


def cmd_resolve_test_scope(args) -> int:
    """Resolve the scoped module set and scoped-vs-whole-tree divergence risk.

    Reads the live footprint and the ``build.map`` globs the same way
    ``pre-push-quality-gate.md`` does — here through the in-process
    ``script-shared`` seams that back ``should_execute_build`` — then delegates
    the derivation to the pure ``resolve_test_scope`` helper. ``whole_tree_available``
    reflects whether a whole-tree pytest run is structurally possible (a
    discoverable Python module set exists). Prints the resolution as TOON:
    ``scoped_modules[]``, ``divergence_possible``, ``recommended_target``,
    ``whole_tree_available``.

    The footprint is plan-scoped, so ``--plan-id`` is required; the ``--project-dir``
    escape hatch alone cannot resolve a live footprint.
    """
    # In-process form of the manage-references compute-footprint /
    # manage-config build-map read seams — same script-shared bundle, no
    # subprocess round-trip. Deferred so the top level carries no extra
    # cross-module dependency beyond the pure helper.
    from extension_base import _read_build_map_globs, _resolve_plan_footprint

    plan_id = getattr(args, 'plan_id', None)
    if not plan_id:
        print(
            serialize_toon(
                {
                    'status': 'error',
                    'error': 'plan_id_required',
                    'message': 'resolve-test-scope requires --plan-id to resolve the live footprint',
                }
            )
        )
        return 2

    globs = _read_build_map_globs(getattr(args, 'project_dir', None))
    footprint = _resolve_plan_footprint(plan_id)
    resolution = resolve_test_scope(footprint, globs)
    whole_tree_available = bool(discover_python_modules(args.project_dir))

    print(
        serialize_toon(
            {
                'status': 'success',
                'scoped_modules': list(resolution.scoped_modules),
                'divergence_possible': resolution.divergence_possible,
                'recommended_target': resolution.recommended_target,
                'whole_tree_available': whole_tree_available,
            }
        )
    )
    return 0


def _register_resolve_test_scope(subparsers) -> None:
    """Register the ``resolve-test-scope`` subcommand.

    Accepts the canonical ``--project-dir`` / ``--plan-id`` pair (mutually
    exclusive, mirroring ``run``) so ``build_main`` resolves the worktree before
    the handler runs.
    """
    scope_parser = subparsers.add_parser(
        'resolve-test-scope',
        help='Resolve scoped module set and scoped-vs-whole-tree divergence risk',
        allow_abbrev=False,
    )
    add_project_dir_arg(scope_parser)
    scope_parser.set_defaults(func=cmd_resolve_test_scope)


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
            extra_register_fns=[_register_pyproject_parse, _register_resolve_test_scope],
        ),
    )


if __name__ == '__main__':
    safe_main(main)()
