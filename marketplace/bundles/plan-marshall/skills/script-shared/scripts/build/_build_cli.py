#!/usr/bin/env python3
"""CLI scaffolding for build-* skills.

Provides argparse subparser helpers, registration utilities, and the common
main() entry point used by all build skill scripts (maven.py, gradle.py,
npm.py, python_build.py).

Split from _build_shared.py to separate CLI wiring from command implementations.
"""

from __future__ import annotations

from collections.abc import Callable

from _build_format import format_toon
from _build_parse import Issue
from _build_shared import ParserFn, cmd_discover_common, cmd_parse_common


def add_project_dir_arg(parser) -> None:
    """Attach the standard --project-dir argument to a subparser.

    All build subcommands accept --project-dir so invocations from an
    isolated worktree (or any non-cwd directory) can pin subprocess cwd
    without relying on the caller's working directory. Default is '.'
    so existing invocations remain unchanged.
    """
    parser.add_argument(
        '--project-dir',
        dest='project_dir',
        default='.',
        help='Project root directory (default: current directory)',
    )


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
        default_timeout: Default timeout in seconds.
        extra_args_fn: Optional callable(run_parser) to add tool-specific args
            (e.g., --working-dir, --env for npm).

    Returns:
        The created run subparser (for setting defaults like func=cmd_run).
    """
    run_parser = subparsers.add_parser('run', help='Execute build and auto-parse on failure (primary API)')
    run_parser.add_argument(
        '--command-args',
        dest='command_args',
        required=True,
        help=command_args_help,
    )
    run_parser.add_argument(
        '--timeout',
        type=int,
        default=default_timeout,
        help=f'Build timeout in seconds (default: {default_timeout})',
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
    cov_parser = subparsers.add_parser('coverage-report', help=help_text)
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

    parse_parser = subparsers.add_parser('parse', help=help_text)
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


def add_check_warnings_subparser(subparsers, check_warnings_fn, *, help_text: str = 'Categorize build warnings'):
    """Add standard 'check-warnings' subparser with common arguments.

    Args:
        subparsers: argparse subparsers object.
        check_warnings_fn: Handler function (from create_check_warnings_handler).
        help_text: Help text for the subparser.

    Returns:
        The created check-warnings subparser.
    """
    warn_parser = subparsers.add_parser('check-warnings', help=help_text)
    warn_parser.add_argument('--warnings', help='JSON array of warning objects')
    warn_parser.add_argument(
        '--acceptable-warnings',
        dest='acceptable_warnings',
        help='JSON object with acceptable patterns',
    )
    add_project_dir_arg(warn_parser)
    warn_parser.set_defaults(func=check_warnings_fn)
    return warn_parser


def add_discover_subparser(subparsers, discover_fn, *, help_text: str = 'Discover project modules'):
    """Add standard 'discover' subparser with common arguments.

    All build skills share the same discover subparser pattern:
    --root, --format.

    Args:
        subparsers: argparse subparsers object.
        discover_fn: Tool-specific discover_modules function.
            Must accept (project_root: str) and return list of module dicts.
        help_text: Help text for the subparser.

    Returns:
        The created discover subparser.
    """
    discover_parser = subparsers.add_parser('discover', help=help_text)
    discover_parser.add_argument('--root', default='.', help='Project root directory')
    discover_parser.add_argument(
        '--format',
        choices=['toon', 'json'],
        default='toon',
        help='Output format (default: toon)',
    )

    def _cmd_discover(args):
        return cmd_discover_common(args, discover_fn)

    discover_parser.set_defaults(func=_cmd_discover)
    return discover_parser


def add_search_markers_subparser(subparsers, search_markers_fn, *, default_extensions: str = '.java'):
    """Add standard 'search-markers' subparser for OpenRewrite TODO markers.

    Used by Maven and Gradle build skills that support OpenRewrite integration.

    Args:
        subparsers: argparse subparsers object.
        search_markers_fn: Handler function for search-markers command.
        default_extensions: Default file extensions to search (e.g., '.java', '.java,.kt').

    Returns:
        The created search-markers subparser.
    """
    markers_parser = subparsers.add_parser('search-markers', help='Search for OpenRewrite TODO markers')
    markers_parser.add_argument('--source-dir', default='src', help='Directory to search')
    markers_parser.add_argument('--extensions', default=default_extensions, help='Comma-separated extensions')
    markers_parser.add_argument(
        '--format', choices=['toon', 'json'], default='toon', help='Output format (default: toon)'
    )
    markers_parser.set_defaults(func=search_markers_fn)
    return markers_parser


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

        def _reg_warn(subparsers, _h=check_warnings_handler):
            add_check_warnings_subparser(subparsers, _h)

        fns.append(_reg_warn)

    if discover_handler is not None:

        def _reg_disc(subparsers, _h=discover_handler, _ht=discover_help):
            add_discover_subparser(subparsers, _h, help_text=_ht)

        fns.append(_reg_disc)

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

    parser = _argparse.ArgumentParser(description=description, formatter_class=_argparse.RawDescriptionHelpFormatter)
    subparsers = parser.add_subparsers(dest='command', required=True)

    for register_fn in subparser_fns:
        register_fn(subparsers)

    args = parser.parse_args()
    result: int = args.func(args)
    return result


def safe_main(main_fn: Callable[[], int]) -> int:
    """Wrap a build script's main() to catch unhandled exceptions and emit TOON failure.

    Ensures all build scripts produce structured TOON output even on
    unexpected errors, instead of raw tracebacks that corrupt output.

    Usage::

        if __name__ == '__main__':
            sys.exit(safe_main(main))
    """
    try:
        return main_fn()
    except SystemExit as e:
        # Let argparse --help / missing-arg exits pass through
        raise e
    except Exception as e:
        print(format_toon({'status': 'error', 'error': f'unexpected_error: {e}'}))
        return 1
