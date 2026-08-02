#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Pyproject build operations - run, parse, check warnings, coverage report.

Usage:
    pyproject_build.py run --command-args <args> [--working-dir <path>] [--env <vars>] [options]
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
from dataclasses import replace
from pathlib import Path

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
from marketplace_bundles import extract_bundle_name, find_bundles
from marketplace_paths import find_marketplace_path, names_real_plan
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


def _pyproject_extra_args(run_parser):
    run_parser.add_argument('--working-dir', dest='working_dir', help='Working directory for command execution')
    run_parser.add_argument('--env', help="Environment variables (e.g., 'PYTHONPATH=src CI=true')")


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


def _resolve_registered_modules(project_dir: str | None) -> frozenset[str]:
    """Enumerate the registered module names for ``project_dir``'s marketplace.

    The registered-module set the pure ``resolve_test_scope`` helper needs to
    reject a derived name that no module actually carries. It is resolved HERE,
    in the handler that already performs I/O, so the pure module stays free of
    it. The enumeration reuses the existing tested
    ``marketplace_bundles.find_bundles()`` + ``extract_bundle_name()`` seam
    anchored on the marketplace root ``find_marketplace_path()`` resolves from the
    already-available ``project_dir`` - no new inventory mechanism.

    Returns an EMPTY frozenset in exactly the two cases the body guards: the
    marketplace root does not resolve (``find_marketplace_path`` returns
    ``None``), or the walk raises ``OSError`` (an unreadable or vanished
    directory). The caller reads emptiness as ``modules_resolvable: false`` and
    fails toward the whole tree rather than silently disabling the check.

    The guard is deliberately no wider than the claim above. ``find_bundles`` /
    ``extract_bundle_name`` derive every name by ``re.match`` over a directory
    name and touch the filesystem only through calls whose failure mode is
    ``OSError``, so ``OSError`` is the walk's only expected failure. Anything
    else escapes as a crash, which is loud rather than a false
    ``modules_resolvable: true``; do NOT widen the ``except`` to a bare
    ``Exception``, which would relabel an unforeseen bug as a routine-looking
    ``modules_resolvable: false``.
    """
    try:
        bundles_root = find_marketplace_path(Path(project_dir) if project_dir else None)
        if bundles_root is None:
            return frozenset()
        return frozenset(extract_bundle_name(bundle_dir) for bundle_dir in find_bundles(bundles_root))
    except OSError:
        return frozenset()


def cmd_resolve_test_scope(args) -> int:
    """Resolve the scoped module set and scoped-vs-whole-tree divergence risk.

    Derives the footprint from one of two sources and delegates the resolution
    to the pure ``resolve_test_scope`` helper. When ``--changed-paths`` is
    supplied the comma-separated list IS the footprint (a task-scoped footprint -
    exactly the files a single task's change touched); otherwise the whole-plan
    live footprint is read the same way ``pre-push-quality-gate.md`` does, here
    through the in-process ``script-shared`` seams that back
    ``should_execute_build``. ``--plan-id`` / ``--project-dir`` still resolve the
    ``build.map`` globs in both modes. ``whole_tree_available`` reflects whether a
    whole-tree pytest run is structurally possible (a discoverable Python module
    set exists). Prints the resolution as TOON: ``scoped_modules[]``,
    ``divergence_possible``, ``recommended_target``, ``unresolved_paths[]``,
    ``whole_tree_available``, ``footprint_resolvable``, ``modules_resolvable``.

    Footprint source: ``--changed-paths`` (task-scoped) supersedes the whole-plan
    footprint; when it is absent a REAL ``--plan-id`` is required to resolve the
    live plan footprint. The ``NO_PLAN`` sentinel does not satisfy that
    requirement - it names no plan whose footprint could be resolved, so it is
    refused with the same ``footprint_source_required`` error as an omitted flag.

    Two inputs can fail to resolve, and both fail toward the whole tree through
    the SAME ``dataclasses.replace`` call rather than through parallel branches:

    * ``footprint_resolvable`` is ``false`` only on the whole-plan path when the
      footprint cannot be resolved at all (no worktree materialised yet). That
      state yields no module ownership, so it is reported as
      ``divergence_possible: true`` with ``recommended_target: null`` - the
      whole-tree answer. Reporting it as a resolvable-but-empty footprint would
      instead claim ``divergence_possible: false`` ("a scoped run cannot miss a
      regression") on no evidence whatever.
    * ``modules_resolvable`` is ``false`` when the registered-module enumeration
      failed or came back empty. Without that set every derived module name is
      unverifiable, so a confident scoped target would rest on nothing. Failing
      closed here is what stops "the caller could not enumerate modules" from
      silently disabling the registered-module check.

    ``unresolved_paths`` carries every footprint entry that mapped to no
    registered module, so the suppression is disclosed to the consumer (ADR-014)
    instead of dying inside the dataclass.
    """
    # In-process form of the manage-references compute-footprint /
    # manage-config build-map read seams — same script-shared bundle, no
    # subprocess round-trip. Deferred so the top level carries no extra
    # cross-module dependency beyond the pure helper.
    from extension_base import _read_build_map_globs, _resolve_plan_footprint

    changed_paths = getattr(args, 'changed_paths', None)
    project_dir = getattr(args, 'project_dir', None)
    globs = _read_build_map_globs(project_dir)

    # ``None`` means the whole-plan footprint is UNRESOLVABLE (no worktree
    # materialised yet), which is materially different from a resolvable-but-empty
    # one. An unresolvable footprint yields no module ownership, so nothing can
    # substantiate the claim that a scoped run is safe — resolving it as an empty
    # list would report ``divergence_possible: false``, i.e. "a scoped run cannot
    # miss a regression", on no evidence at all. Fail toward the whole tree.
    footprint_resolvable = True
    if changed_paths is not None:
        footprint = [p.strip() for p in changed_paths.split(',') if p.strip()]
    else:
        plan_id: str = getattr(args, 'plan_id', None) or ''
        # The sentinel is refused alongside the falsy cases — it names no plan
        # whose footprint could be resolved. The error shape is unchanged: a
        # footprint-less invocation still fails closed.
        if not names_real_plan(plan_id):
            print(
                serialize_toon(
                    {
                        'status': 'error',
                        'error': 'footprint_source_required',
                        'message': 'resolve-test-scope requires --changed-paths (task-scoped) '
                        'or --plan-id (whole-plan) to resolve the footprint',
                    }
                )
            )
            return 2
        resolved_footprint = _resolve_plan_footprint(plan_id)
        footprint_resolvable = resolved_footprint is not None
        footprint = resolved_footprint or []

    registered_modules = _resolve_registered_modules(project_dir)
    modules_resolvable = bool(registered_modules)

    resolution = resolve_test_scope(footprint, globs, registered_modules)
    if not footprint_resolvable or not modules_resolvable:
        resolution = replace(resolution, divergence_possible=True, recommended_target=None)
    # discover_python_modules requires a concrete project root; when project_dir
    # is absent (args constructed dynamically or a test env lacking the
    # attribute) a whole-tree run is not structurally possible.
    whole_tree_available = bool(discover_python_modules(project_dir)) if project_dir else False

    print(
        serialize_toon(
            {
                'status': 'success',
                'scoped_modules': list(resolution.scoped_modules),
                'divergence_possible': resolution.divergence_possible,
                'recommended_target': resolution.recommended_target,
                'unresolved_paths': list(resolution.unresolved_paths),
                'whole_tree_available': whole_tree_available,
                'footprint_resolvable': footprint_resolvable,
                'modules_resolvable': modules_resolvable,
            }
        )
    )
    return 0


def _register_resolve_test_scope(subparsers) -> None:
    """Register the ``resolve-test-scope`` subcommand.

    Accepts the canonical ``--project-dir`` / ``--plan-id`` pair (mutually
    exclusive, mirroring ``run``) so ``build_main`` resolves the worktree before
    the handler runs. The optional ``--changed-paths`` input supplies a
    task-scoped footprint directly (comma-separated), superseding the whole-plan
    live footprint when present.
    """
    scope_parser = subparsers.add_parser(
        'resolve-test-scope',
        help='Resolve scoped module set and scoped-vs-whole-tree divergence risk',
        allow_abbrev=False,
    )
    add_project_dir_arg(scope_parser)
    scope_parser.add_argument(
        '--changed-paths',
        dest='changed_paths',
        default=None,
        help='Comma-separated task-scoped footprint; when set it IS the footprint '
        '(supersedes the whole-plan live footprint resolved from --plan-id)',
    )
    scope_parser.set_defaults(func=cmd_resolve_test_scope)


def main() -> int:
    """Main entry point."""
    return build_main(
        'Python/pyprojectx (build-pyproject) build operations',
        register_standard_subparsers(
            run_handler=cmd_run,
            run_args_help="Canonical command to execute (e.g., 'compile', 'verify', 'module-tests', 'quality-gate', 'coverage')",
            run_extra_args_fn=_pyproject_extra_args,
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
