#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""CLI scaffolding for build-* skills.

Provides argparse subparser helpers, registration utilities, and the common
main() entry point used by all build skill scripts (maven.py, gradle.py,
npm.py, pyproject_build.py).

Split from _build_shared.py to separate CLI wiring from command implementations.
"""

from __future__ import annotations

from collections.abc import Callable

from _build_format import format_toon
from _build_parse import Issue
from _build_shared import ParserFn, cmd_discover_common, cmd_parse_common
from file_ops import safe_main  # noqa: F401  # canonical entry-point wrapper
from marketplace_paths import NO_PLAN_SENTINEL


def add_project_dir_arg(parser) -> None:
    """Attach the standard --project-dir / --plan-id argument pair to a subparser.

    Every build-class subcommand accepts ``--project-dir`` and ``--plan-id``
    so invocations from an isolated worktree (or any non-cwd directory)
    can pin subprocess cwd without relying on the caller's working
    directory. This helper is the SINGLE declaration site for the pair:
    the shared registrations below call it, and the two wrapper-local
    registrations that build their subparsers outside this module
    (``maven.py::_register_rewrite_log`` and
    ``gradle.py::_register_find_project``) import it rather than
    re-declaring the flags. The universality of that claim is asserted
    against the argparse-derived build-class roster rather than restated
    as prose, so a subcommand registered without the pair fails a test
    instead of silently falsifying this sentence.

    The two flags implement the two-state contract documented
    in ``script_shared/scripts/resolve_project_dir.py``:

    * ``--plan-id X`` and ``--project-dir Y`` together — error
      ``mutually_exclusive_args``.
    * ``--plan-id X`` only — auto-resolve the worktree face through
      ``file_ops.resolve_plan_context``, which owns the single
      ``manage-status get-worktree-path`` invocation in the codebase.
    * ``--plan-id NO_PLAN`` — the plan-less sentinel. NOT a routing
      source: it resolves like the neither-flag branch and does not
      trigger the mutual-exclusion error, so ``--plan-id NO_PLAN
      --project-dir Y`` stays legal.
    * ``--project-dir Y`` only — explicit override (legacy / escape
      hatch).
    * Neither — the cwd-relative checkout root via
      ``file_ops.cwd_checkout_root`` (nearest ``.plan/local`` ancestor of
      cwd, per the uniform cwd rule / ADR-002). ``build_main`` then
      resolves the absent ``--plan-id`` to ``NO_PLAN`` so every handler
      sees a non-empty plan id.

    The ``--project-dir`` default stays ``'.'`` so the existing
    ``execute_direct(project_dir=args.project_dir, ...)`` call sites
    keep compiling. ``apply_plan_id_routing`` (called by the run / parse
    / coverage / check-warnings handlers via ``_build_shared``)
    rewrites ``args.project_dir`` to the resolved value before
    subprocess execution.
    """
    parser.add_argument(
        '--project-dir',
        dest='project_dir',
        default='.',
        help='Project root directory (default: current directory). Mutually exclusive with --plan-id.',
    )
    # The companion --plan-id flag is added by the shared helper so the
    # help text and default stay aligned with the canonical contract.
    from resolve_project_dir import add_plan_id_arg

    add_plan_id_arg(parser)


def add_root_arg(parser, *, help_text: str = 'Project root directory') -> None:
    """Attach the ``--root`` flag with a ``None`` sentinel default.

    ``default=None`` is a load-bearing SENTINEL, not a missing default — the
    same pattern ``--timeout`` uses in ``add_run_subparser`` below. It is the
    only way :func:`resolve_root_arg` can tell an explicit ``--root .`` from an
    unsupplied flag, which is what lets a subcommand declaring BOTH ``--root``
    and the ``--project-dir`` / ``--plan-id`` routing pair give the explicit
    flag precedence rather than guessing.

    Args:
        parser: The subparser to extend.
        help_text: Lead sentence of the flag's help string.
    """
    parser.add_argument(
        '--root',
        default=None,
        help=f'{help_text}. When omitted, the root resolved from --plan-id / --project-dir is used.',
    )


def resolve_root_arg(args) -> str:
    """Return the effective project root for a subcommand declaring ``--root``.

    Precedence: an explicitly-supplied ``--root`` wins verbatim; otherwise the
    root ``build_main`` already resolved into ``args.project_dir`` from the
    ``--plan-id`` / ``--project-dir`` pair applies. That fallback is what makes
    ``discover --plan-id X`` enumerate modules in X's worktree instead of
    silently enumerating the caller's cwd.

    Args:
        args: The parsed namespace, carrying ``root`` and (after
            :func:`build_main` resolution) ``project_dir``.

    Returns:
        The project root path to hand to the subcommand's handler.
    """
    root: str | None = getattr(args, 'root', None)
    if root is not None:
        return root
    project_dir: str | None = getattr(args, 'project_dir', None)
    return project_dir or '.'


def add_run_subparser(
    subparsers,
    *,
    command_args_help: str = 'Complete command arguments',
    default_timeout: int = 300,
    extra_args_fn=None,
):
    """Add standard 'run' subparser with common arguments.

    All build skills share the same run subparser pattern:
    --command-args, --timeout, --mode, --format, --project-dir.

    Args:
        subparsers: argparse subparsers object.
        command_args_help: Help text for --command-args.
        default_timeout: The engine's fallback timeout in seconds, named in the
            ``--timeout`` help text. It is NOT the argparse default — that is a
            ``None`` sentinel so an explicit ``--timeout`` stays distinguishable
            from an unsupplied one.
        extra_args_fn: Optional callable(run_parser) to add tool-specific args
            (e.g., --working-dir, --env for npm).

    Returns:
        The created run subparser (for setting defaults like func=cmd_run).
    """
    run_parser = subparsers.add_parser(
        'run', help='Execute build and auto-parse on failure (primary API)', allow_abbrev=False
    )
    run_parser.add_argument(
        '--command-args',
        dest='command_args',
        required=True,
        help=command_args_help,
    )
    # ``default=None`` is a load-bearing SENTINEL, not a missing default: it is
    # the only way ``cmd_run`` can tell an explicitly-supplied ``--timeout N``
    # from an unsupplied flag. An explicit value is a true override of the
    # persisted learned value; when the flag is absent the engine's
    # ``config.default_timeout`` supplies the fallback, exactly as before.
    run_parser.add_argument(
        '--timeout',
        type=int,
        default=None,
        help='Build timeout in seconds — an explicit value overrides the learned value '
        '(no learned value can reduce it, though the engine floor still applies). '
        f'When omitted, the learned value is used, falling back to {default_timeout}.',
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
        help='Output format (default: toon)',
    )
    # Explicit build-execute routing mode (D5 build-server client API). Declared
    # once here so all four build tools (maven, gradle, npm, pyproject) inherit
    # the flag from this single shared 'run' subparser:
    #   auto        — route to marshalld opportunistically; fall back in-process
    #                 on any unavailability (the historical default behaviour).
    #   in_process  — never attempt to route; always build in-process.
    #   daemon      — require the marshalld daemon; fail loud instead of falling
    #                 back when the daemon cannot run the build.
    run_parser.add_argument(
        '--execution-mode',
        dest='execution_mode',
        choices=['auto', 'in_process', 'daemon'],
        default='auto',
        help='Build-execute routing mode (default: auto)',
    )
    # ``add_project_dir_arg`` adds BOTH ``--project-dir`` and ``--plan-id``
    # so the run subparser inherits the canonical two-state routing
    # contract automatically. The same ``--plan-id`` value also drives
    # the producer-side auto-storage of parsed issues into the per-type
    # finding store via manage-findings (always-on when set; when unset,
    # the historical silent behaviour is preserved — parse + format
    # only). The flag is therefore declared exactly once.
    add_project_dir_arg(run_parser)
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
    cov_parser = subparsers.add_parser('coverage-report', help=help_text, allow_abbrev=False)
    cov_parser.add_argument('--project-path', dest='project_path', help='Project or module directory path')
    cov_parser.add_argument('--report-path', dest='report_path', help='Override coverage report path')
    cov_parser.add_argument(
        '--threshold',
        type=int,
        default=default_threshold,
        help=f'Coverage threshold percent (default: {default_threshold})',
    )
    add_project_dir_arg(cov_parser)
    return cov_parser


def add_parse_subparser(
    subparsers,
    parse_fn,
    *,
    help_text: str = 'Parse build output and categorize issues',
    extra_modes: list[str] | None = None,
    extra_filters: dict[str, Callable[[Issue], bool]] | None = None,
    parser_needs_command: bool = False,
):
    """Add standard 'parse' subparser with common arguments.

    All build skills share the same parse subparser pattern:
    --log, --mode, --format. This helper creates the subparser, wires
    up the func default to call cmd_parse_common with the right args.

    Args:
        subparsers: argparse subparsers object.
        parse_fn: Tool-specific parse_log function.
        help_text: Help text for the subparser.
        extra_modes: Additional mode choices beyond default/errors/structured.
        extra_filters: Mode filters to pass to cmd_parse_common.
        parser_needs_command: If True, passes command to parser_fn.

    Returns:
        The created parse subparser.
    """
    modes = ['default', 'errors', 'structured']
    if extra_modes:
        modes.extend(extra_modes)

    parse_parser = subparsers.add_parser('parse', help=help_text, allow_abbrev=False)
    parse_parser.add_argument('--log', required=True, help='Path to build log file')
    parse_parser.add_argument('--mode', choices=modes, default='structured', help='Output mode')
    parse_parser.add_argument(
        '--format',
        choices=['toon', 'json'],
        default='toon',
        help='Output format (default: toon)',
    )
    add_project_dir_arg(parse_parser)

    def _cmd_parse(args):
        return cmd_parse_common(
            args,
            parse_fn,
            extra_filters=extra_filters,
            parser_needs_command=parser_needs_command,
        )

    parse_parser.set_defaults(func=_cmd_parse)
    return parse_parser


def add_check_warnings_subparser(
    subparsers,
    check_warnings_fn,
    *,
    help_text: str = 'Categorize build warnings',
    extra_args_fn=None,
):
    """Add standard 'check-warnings' subparser with common arguments.

    Args:
        subparsers: argparse subparsers object.
        check_warnings_fn: Handler function (from create_check_warnings_handler).
        help_text: Help text for the subparser.
        extra_args_fn: Optional callable(warn_parser) to add tool-specific args
            (e.g., npm's --warning-baseline). Only tools that pass this seam
            register the extra flag, so other build tools stay unaffected.

    Returns:
        The created check-warnings subparser.
    """
    warn_parser = subparsers.add_parser('check-warnings', help=help_text, allow_abbrev=False)
    warn_parser.add_argument('--warnings', help='JSON array of warning objects')
    warn_parser.add_argument(
        '--acceptable-warnings',
        dest='acceptable_warnings',
        help='JSON object with acceptable patterns',
    )
    add_project_dir_arg(warn_parser)
    if extra_args_fn:
        extra_args_fn(warn_parser)
    warn_parser.set_defaults(func=check_warnings_fn)
    return warn_parser


def add_discover_subparser(subparsers, discover_fn, *, help_text: str = 'Discover project modules'):
    """Add standard 'discover' subparser with common arguments.

    All build skills share the same discover subparser pattern:
    --root, --format, plus the canonical --project-dir / --plan-id routing
    pair. ``--root`` and the routing pair are reconciled by
    :func:`resolve_root_arg` before the handler runs: an explicit ``--root``
    wins, and otherwise the resolved routing root applies, so
    ``discover --plan-id X`` enumerates X's worktree rather than the caller's
    cwd.

    Args:
        subparsers: argparse subparsers object.
        discover_fn: Tool-specific discover_modules function.
            Must accept (project_root: str) and return list of module dicts.
        help_text: Help text for the subparser.

    Returns:
        The created discover subparser.
    """
    discover_parser = subparsers.add_parser('discover', help=help_text, allow_abbrev=False)
    add_root_arg(discover_parser)
    discover_parser.add_argument(
        '--format',
        choices=['toon', 'json'],
        default='toon',
        help='Output format (default: toon)',
    )
    add_project_dir_arg(discover_parser)

    def _cmd_discover(args):
        # ``build_main`` has already rewritten ``args.project_dir`` to the
        # resolved routing root; collapse the two sources to the single value
        # ``cmd_discover_common`` reads.
        args.root = resolve_root_arg(args)
        return cmd_discover_common(args, discover_fn)

    discover_parser.set_defaults(func=_cmd_discover)
    return discover_parser


def add_run_config_key_subparser(subparsers, config, *, help_text: str = 'Compute canonical run-config key for a given command args string'):
    """Add a 'run-config-key' subparser that prints the canonical run-config key.

    Returns TOON with three fields:

    * ``build_tool`` — the build skill's ``tool_name`` (e.g. ``maven``,
      ``python``, ``gradle``, ``npm``).
    * ``key_suffix`` — output of ``config.command_key_fn(command_args)``
      (the part after the colon).
    * ``command_key`` — the full key ``{build_tool}:{key_suffix}`` produced
      by ``compute_command_key(config, command_args)``.

    The handler reuses the same ``compute_command_key`` helper that
    ``cmd_run`` uses at execute time, so there is exactly one source of
    truth for the canonical key. Consumers of ``architecture resolve``
    use this subcommand to look up the adaptive-timeout entry without
    re-implementing the key construction.

    Args:
        subparsers: argparse subparsers object.
        config: The build skill's ExecuteConfig instance.
        help_text: Help text for the subparser.

    Returns:
        The created run-config-key subparser.
    """
    from _build_execute_factory import compute_command_key as _compute_command_key

    key_parser = subparsers.add_parser('run-config-key', help=help_text, allow_abbrev=False)
    key_parser.add_argument(
        '--command-args',
        dest='command_args',
        required=True,
        help='Canonical command args string (e.g., "verify", "verify plan-marshall")',
    )
    key_parser.add_argument(
        '--format',
        choices=['toon', 'json'],
        default='toon',
        help='Output format (default: toon)',
    )
    # ``run-config-key`` is a pure key computation and reads no path, so the
    # resolved ``--project-dir`` is inert here. The pair is declared anyway so
    # the routing/ledger contract is uniform across the whole build-class
    # surface rather than two-tier — a reader never has to look up whether a
    # given build subcommand happens to accept --plan-id.
    add_project_dir_arg(key_parser)

    def _cmd_run_config_key(args) -> int:
        key_suffix = config.command_key_fn(args.command_args)
        command_key = _compute_command_key(config, args.command_args)
        result = {
            'status': 'success',
            'build_tool': config.tool_name,
            'key_suffix': key_suffix,
            'command_key': command_key,
        }
        output_format = getattr(args, 'format', 'toon')
        if output_format == 'json':
            import json as _json

            print(_json.dumps(result, indent=2))
        else:
            # Use the canonical generic TOON serializer rather than
            # ``format_toon``: the latter is build-result-specific and silently
            # drops keys outside its CORE_FIELDS/EXTRA_FIELDS allow-list (e.g.
            # ``build_tool``, ``key_suffix``, ``command_key``), which would
            # collapse our payload to just ``status: success``.
            from toon_parser import serialize_toon as _serialize_toon

            print(_serialize_toon(result))
        return 0

    key_parser.set_defaults(func=_cmd_run_config_key)
    return key_parser


def register_standard_subparsers(
    *,
    run_handler: Callable | None = None,
    run_args_help: str = 'Complete command arguments',
    run_extra_args_fn: Callable | None = None,
    parse_handler: ParserFn | None = None,
    parse_help: str = 'Parse build output and categorize issues',
    parse_extra_modes: list[str] | None = None,
    parse_extra_filters: dict[str, Callable[[Issue], bool]] | None = None,
    parse_needs_command: bool = False,
    discover_handler: Callable | None = None,
    discover_help: str = 'Discover project modules',
    coverage_handler: Callable | None = None,
    coverage_help: str = 'Parse coverage report',
    check_warnings_handler: Callable | None = None,
    check_warnings_extra_args_fn: Callable | None = None,
    run_config_key_config=None,
    extra_register_fns: list[Callable] | None = None,
) -> list[Callable]:
    """Build a list of subparser registration functions from declarative config.

    Reduces boilerplate in build skill main scripts by replacing individual
    _register_* wrapper functions with a single declarative call.

    Args:
        run_handler: Handler for 'run' subcommand (cmd_run function).
        run_args_help: Help text for --command-args.
        run_extra_args_fn: Extra args callback for run subparser (e.g., npm's --env).
        parse_handler: Log parser function for 'parse' subcommand.
        parse_help: Help text for parse subparser.
        parse_extra_modes: Additional parse mode choices.
        parse_extra_filters: Extra mode filters for parse.
        parse_needs_command: If True, passes command to parser.
        discover_handler: Discovery function for 'discover' subcommand.
        discover_help: Help text for discover subparser.
        coverage_handler: Handler for 'coverage-report' subcommand.
        coverage_help: Help text for coverage subparser.
        check_warnings_handler: Handler for 'check-warnings' subcommand.
        check_warnings_extra_args_fn: Extra args callback for the check-warnings
            subparser (e.g., npm's --warning-baseline). Tools that omit it keep
            the standard check-warnings surface unchanged.
        run_config_key_config: When non-None, an ExecuteConfig instance that
            registers the 'run-config-key' subcommand exposing the canonical
            run-config key construction. The same config object that
            cmd_run uses MUST be passed so the exposed key matches the
            persisted key exactly (round-trip property).
        extra_register_fns: Additional registration functions for tool-specific subcommands.

    Returns:
        List of registration functions suitable for build_main().
    """
    fns: list[Callable] = []

    if run_handler is not None:

        def _reg_run(subparsers, _h=run_handler, _help=run_args_help, _extra=run_extra_args_fn):
            p = add_run_subparser(subparsers, command_args_help=_help, extra_args_fn=_extra)
            p.set_defaults(func=_h)

        fns.append(_reg_run)

    if parse_handler is not None:

        def _reg_parse(
            subparsers,
            _h=parse_handler,
            _ht=parse_help,
            _em=parse_extra_modes,
            _ef=parse_extra_filters,
            _nc=parse_needs_command,
        ):
            add_parse_subparser(
                subparsers, _h, help_text=_ht, extra_modes=_em, extra_filters=_ef, parser_needs_command=_nc
            )

        fns.append(_reg_parse)

    if extra_register_fns:
        fns.extend(extra_register_fns)

    if coverage_handler is not None:

        def _reg_cov(subparsers, _h=coverage_handler, _ht=coverage_help):
            p = add_coverage_subparser(subparsers, help_text=_ht)
            p.set_defaults(func=_h)

        fns.append(_reg_cov)

    if check_warnings_handler is not None:

        def _reg_warn(subparsers, _h=check_warnings_handler, _extra=check_warnings_extra_args_fn):
            add_check_warnings_subparser(subparsers, _h, extra_args_fn=_extra)

        fns.append(_reg_warn)

    if discover_handler is not None:

        def _reg_disc(subparsers, _h=discover_handler, _ht=discover_help):
            add_discover_subparser(subparsers, _h, help_text=_ht)

        fns.append(_reg_disc)

    if run_config_key_config is not None:

        def _reg_rck(subparsers, _cfg=run_config_key_config):
            add_run_config_key_subparser(subparsers, _cfg)

        fns.append(_reg_rck)

    return fns


def build_main(
    description: str,
    subparser_fns: list[Callable],
) -> int:
    """Common main() entry point for all build skills.

    Creates the argparse parser, adds all subparsers via the provided
    registration functions, parses args, and dispatches to the handler.

    Each subparser_fn receives (subparsers) and registers one subcommand.

    Args:
        description: Parser description (e.g., 'Maven build operations').
        subparser_fns: List of callables that each add one subparser.

    Returns:
        Exit code from the dispatched handler.
    """
    import argparse as _argparse

    parser = _argparse.ArgumentParser(
        description=description,
        formatter_class=_argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    for register_fn in subparser_fns:
        register_fn(subparsers)

    args = parser.parse_args()

    # Two-state ``--plan-id`` / ``--project-dir`` resolution. Bucket B
    # build scripts uniformly opt in via ``add_project_dir_arg`` so the
    # routing happens here, before any handler reads ``args.project_dir``.
    # Subcommands that do not declare the pair (e.g., ``parse``) simply
    # lack ``args.plan_id`` and ``args.project_dir`` — the helper is a
    # no-op for those namespaces.
    from resolve_project_dir import (
        MutuallyExclusiveArgsError,
        WorktreeResolutionError,
        emit_mutually_exclusive_error,
        emit_worktree_error,
        resolve_project_dir,
    )

    plan_id = getattr(args, 'plan_id', None)
    project_dir = getattr(args, 'project_dir', None)
    if hasattr(args, 'project_dir'):
        try:
            args.project_dir = resolve_project_dir(plan_id, project_dir, default='.')
        except MutuallyExclusiveArgsError:
            print(format_toon(emit_mutually_exclusive_error(plan_id, project_dir)))
            return 2
        except WorktreeResolutionError as exc:
            assert plan_id is not None  # only reachable when plan_id was supplied
            print(format_toon(emit_worktree_error(plan_id, exc)))
            return 2

    # Every build-class handler downstream sees a RESOLVED plan id: an absent
    # ``--plan-id`` becomes the ``NO_PLAN`` sentinel, so a build is always
    # attributable (the executor's kind=build ledger row can never carry null).
    # Deliberately AFTER the resolution above: the sentinel is not a routing
    # source, so the mutual-exclusion and worktree-resolution error paths keep
    # observing the caller's actual flags. The sentinel is truthy, so every
    # downstream ``plan_id`` guard tests for it explicitly rather than relying
    # on falsiness — see the guard sites in ``_build_queue_slot``,
    # ``_build_execute_factory``, ``_build_shared`` and ``pyproject_build``.
    if hasattr(args, 'plan_id'):
        args.plan_id = args.plan_id or NO_PLAN_SENTINEL

    result: int = args.func(args)
    return result
