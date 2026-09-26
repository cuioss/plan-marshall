#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Read-only architecture query CLI.

Thin entry point that imports handlers from manage-architecture's _cmd_client
module and exposes consumer query commands: info, modules, graph, module,
commands, resolve, siblings, profiles.
"""

import argparse

from file_ops import output_toon, safe_main
from resolve_project_dir import (
    MutuallyExclusiveArgsError,
    WorktreeResolutionError,
    add_plan_id_arg,
    emit_mutually_exclusive_error,
    emit_worktree_error,
    resolve_project_dir,
)


@safe_main
def main() -> int:
    parser = argparse.ArgumentParser(description='Read-only project architecture queries', allow_abbrev=False)
    parser.add_argument(
        '--project-dir',
        default='.',
        help='Project directory (default: current directory). Mutually exclusive with --plan-id.',
    )
    add_plan_id_arg(parser)
    subparsers = parser.add_subparsers(dest='command', required=True)

    # info - Project summary
    subparsers.add_parser('info', help='Get project summary with metadata and module overview', allow_abbrev=False)

    # modules - List module names
    modules_parser = subparsers.add_parser('modules', help='List available module names', allow_abbrev=False)
    modules_parser.add_argument(
        '--command',
        dest='filter_command',
        help='Filter to modules that provide this command',
    )
    modules_parser.add_argument(
        '--physical-path',
        dest='physical_path',
        help='Filter to modules at this physical path (for virtual modules)',
    )

    # graph - Get module dependency graph
    graph_parser = subparsers.add_parser(
        'graph', help='Get complete internal module dependency graph', allow_abbrev=False
    )
    graph_parser.add_argument('--full', action='store_true', help='Include aggregator modules (pom-only parents)')

    # module - Get module information
    module_parser = subparsers.add_parser('module', help='Get module information', allow_abbrev=False)
    module_parser.add_argument('--name', help='Module name (default: root module)')
    module_parser.add_argument(
        '--full', action='store_true', help='Include all fields (packages, dependencies, reasoning)'
    )

    # commands - List commands for module
    commands_parser = subparsers.add_parser('commands', help='List available commands for a module', allow_abbrev=False)
    commands_parser.add_argument('--name', help='Module name (default: root module)')

    # resolve - Resolve command to executable
    resolve_parser = subparsers.add_parser('resolve', help='Resolve command to executable form', allow_abbrev=False)
    resolve_parser.add_argument('--command', required=True, dest='resolve_command', help='Command name to resolve')
    resolve_parser.add_argument('--module', help='Module name (default: root module)')

    # siblings - Find sibling virtual modules
    siblings_parser = subparsers.add_parser(
        'siblings', help='Find sibling virtual modules for a given module', allow_abbrev=False
    )
    siblings_parser.add_argument('--name', required=True, help='Module name')

    # profiles - Extract unique profiles from modules
    profiles_parser = subparsers.add_parser(
        'profiles', help='Extract unique profile keys from skills_by_profile for modules', allow_abbrev=False
    )
    profiles_parser.add_argument(
        '--modules', help='Comma-separated module names (default: all modules with enrichment)'
    )

    args = parser.parse_args()

    # Two-state resolution: --plan-id auto-routes via manage-status;
    # --project-dir is the explicit override; both together is an
    # error; neither falls back to the main checkout.
    try:
        args.project_dir = resolve_project_dir(getattr(args, 'plan_id', None), args.project_dir, default='.')
    except MutuallyExclusiveArgsError:
        output_toon(emit_mutually_exclusive_error(getattr(args, 'plan_id', None), args.project_dir))
        return 2
    except WorktreeResolutionError as exc:
        output_toon(emit_worktree_error(args.plan_id, exc))
        return 2

    # Import command handlers from manage-architecture's _cmd_client
    from _cmd_client import (
        cmd_commands,
        cmd_graph,
        cmd_info,
        cmd_module,
        cmd_modules,
        cmd_profiles,
        cmd_resolve,
        cmd_siblings,
    )

    # Dispatch to handlers
    handlers = {
        'info': cmd_info,
        'modules': cmd_modules,
        'graph': cmd_graph,
        'module': cmd_module,
        'commands': cmd_commands,
        'resolve': cmd_resolve,
        'siblings': cmd_siblings,
        'profiles': cmd_profiles,
    }

    handler = handlers.get(args.command)
    if handler:
        result = handler(args)
        output_toon(result)
        return 0
    else:
        parser.print_help()
        return 0


if __name__ == '__main__':
    main()
