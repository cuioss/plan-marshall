#!/usr/bin/env python3
"""Architecture analysis CLI.

Entry point for all architecture operations. Dispatches to command modules.
"""

import argparse

from file_ops import output_toon, safe_main  # type: ignore[import-not-found]
from input_validation import (  # type: ignore[import-not-found]
    add_domain_arg,
    add_module_arg,
    add_name_arg,
    add_package_arg,
    parse_args_with_toon_errors,
    validate_module_name,
)


@safe_main
def main() -> int:
    parser = argparse.ArgumentParser(
        description='Architecture analysis and enrichment operations', allow_abbrev=False
    )
    parser.add_argument('--project-dir', default='.', help='Project directory (default: current directory)')
    subparsers = parser.add_subparsers(dest='command', required=True)

    # =========================================================================
    # Manage Commands (Setup)
    # =========================================================================

    # discover - Run extension API discovery
    discover_parser = subparsers.add_parser('discover', help='Run extension API discovery', allow_abbrev=False)
    discover_parser.add_argument(
        '--force',
        action='store_true',
        help='Overwrite the existing project-architecture/ tree (atomic tmp+swap)',
    )

    # init - Initialize per-module enrichment stubs
    init_parser = subparsers.add_parser(
        'init',
        help='Initialize per-module enriched.json stubs from _project.json',
        allow_abbrev=False,
    )
    init_parser.add_argument(
        '--check',
        action='store_true',
        help='Check whether _project.json exists and how many modules are enriched; output status only',
    )
    init_parser.add_argument(
        '--force',
        action='store_true',
        help='Overwrite existing per-module enriched.json stubs',
    )

    # =========================================================================
    # Manage Commands (Read Raw)
    # =========================================================================

    # derived - Read raw discovered data for all modules
    subparsers.add_parser('derived', help='Read raw discovered data for all modules', allow_abbrev=False)

    # derived-module - Read raw discovered data for single module
    derived_module_parser = subparsers.add_parser(
        'derived-module', help='Read raw discovered data for a single module', allow_abbrev=False
    )
    add_module_arg(derived_module_parser)

    # =========================================================================
    # Client Commands (Consumer Queries)
    # =========================================================================

    # info - Project summary
    subparsers.add_parser('info', help='Get project summary with metadata and module overview', allow_abbrev=False)

    # modules - List module names
    modules_parser = subparsers.add_parser('modules', help='List available module names', allow_abbrev=False)
    modules_parser.add_argument(
        '--command',
        dest='filter_command',  # Avoid collision with subparser dest='command'
        help='Filter to modules that provide this command',
    )

    # graph - Get module dependency graph
    graph_parser = subparsers.add_parser(
        'graph', help='Get complete internal module dependency graph', allow_abbrev=False
    )
    graph_parser.add_argument('--full', action='store_true', help='Include aggregator modules (pom-only parents)')

    # path - BFS shortest path between two modules
    path_parser = subparsers.add_parser(
        'path',
        help='BFS shortest path between two modules over the dependency graph',
        allow_abbrev=False,
    )
    path_parser.add_argument('source', type=validate_module_name, help='Source module name')
    path_parser.add_argument('target', type=validate_module_name, help='Target module name')

    # neighbors - N-hop neighborhood
    neighbors_parser = subparsers.add_parser(
        'neighbors',
        help='N-hop neighborhood of a module over the dependency graph',
        allow_abbrev=False,
    )
    add_module_arg(neighbors_parser)
    neighbors_parser.add_argument(
        '--depth',
        type=int,
        default=1,
        help='Hop count (default 1, max 8)',
    )

    # impact - reverse-dependency closure
    impact_parser = subparsers.add_parser(
        'impact',
        help='Transitive reverse-dependency closure for a module',
        allow_abbrev=False,
    )
    add_module_arg(impact_parser)

    # module - Get module information
    module_parser = subparsers.add_parser('module', help='Get module information', allow_abbrev=False)
    add_module_arg(module_parser, required=False)
    module_parser.add_argument(
        '--full', action='store_true', help='Include all fields (packages, dependencies, reasoning)'
    )
    module_parser.add_argument(
        '--budget',
        type=int,
        default=None,
        help='Render markdown deep-dive bounded to this many lines (requires --full)',
    )

    # overview - Render deterministic project overview markdown
    overview_parser = subparsers.add_parser(
        'overview',
        help='Render deterministic markdown summary of the project architecture',
        allow_abbrev=False,
    )
    overview_parser.add_argument(
        '--budget',
        type=int,
        default=200,
        help='Maximum line count for the rendered overview (default 200)',
    )

    # commands - List commands for module
    commands_parser = subparsers.add_parser(
        'commands', help='List available commands for a module', allow_abbrev=False
    )
    add_module_arg(commands_parser, required=False)

    # resolve - Resolve command to executable
    resolve_parser = subparsers.add_parser('resolve', help='Resolve command to executable form', allow_abbrev=False)
    resolve_parser.add_argument('--command', required=True, dest='resolve_command', help='Command name to resolve')
    add_module_arg(resolve_parser, required=False)

    # siblings - Find sibling virtual modules
    siblings_parser = subparsers.add_parser(
        'siblings', help='Find sibling virtual modules for a given module', allow_abbrev=False
    )
    add_module_arg(siblings_parser)

    # suggest-domains - Suggest applicable skill domains for a module
    suggest_parser = subparsers.add_parser(
        'suggest-domains', help='Suggest applicable skill domains for a module', allow_abbrev=False
    )
    add_module_arg(suggest_parser)

    # profiles - Extract unique profiles from modules
    profiles_parser = subparsers.add_parser(
        'profiles',
        help='Extract unique profile keys from skills_by_profile for modules',
        allow_abbrev=False,
    )
    profiles_parser.add_argument(
        '--modules', help='Comma-separated module names (default: all modules with enrichment)'
    )

    # files - List files inventory for a module (optionally filtered by category)
    files_parser = subparsers.add_parser(
        'files',
        help="List a module's files inventory grouped by category",
        allow_abbrev=False,
    )
    add_module_arg(files_parser)
    files_parser.add_argument(
        '--category',
        help='Filter to a single category (skill, agent, command, script, standard, '
        'template, source, test, build_file, doc, config)',
    )

    # which-module - Reverse-lookup a path back to its owning module
    which_module_parser = subparsers.add_parser(
        'which-module',
        help='Find which module owns a given path (uses files inventory)',
        allow_abbrev=False,
    )
    which_module_parser.add_argument('--path', required=True, help='Path to look up')

    # find - Cross-module glob pattern search across the files inventory
    find_parser = subparsers.add_parser(
        'find',
        help='Search the files inventory across all modules for a glob pattern',
        allow_abbrev=False,
    )
    find_parser.add_argument(
        '--pattern',
        required=True,
        help='Glob pattern (fnmatch syntax, case-sensitive, anchored to full path)',
    )
    find_parser.add_argument('--category', help='Restrict search to a single category')

    # diff-modules - Diff per-module derived.json files against a pre-snapshot
    diff_modules_parser = subparsers.add_parser(
        'diff-modules',
        help=(
            'Diff per-module derived.json files against a pre-snapshot directory. '
            'Returns added/removed/changed/unchanged module name lists.'
        ),
        allow_abbrev=False,
    )
    diff_modules_parser.add_argument(
        '--pre',
        required=True,
        help=(
            'Path to the pre-snapshot directory (either a snapshot root '
            'containing _project.json directly, or a project root whose '
            '.plan/project-architecture/ subtree holds the snapshot)'
        ),
    )

    # =========================================================================
    # Enrich Commands (Write Enrichment)
    # =========================================================================

    enrich_parser = subparsers.add_parser('enrich', help='Enrichment commands', allow_abbrev=False)
    enrich_subparsers = enrich_parser.add_subparsers(dest='enrich_command', required=True)

    # enrich project
    enrich_project_parser = enrich_subparsers.add_parser(
        'project', help='Update project description', allow_abbrev=False
    )
    enrich_project_parser.add_argument('--description', required=True, help='Project description (1-2 sentences)')
    enrich_project_parser.add_argument(
        '--reasoning', help='Source/rationale for the description (e.g., "Derived from README.md first paragraph")'
    )

    # enrich module
    enrich_module_parser = enrich_subparsers.add_parser(
        'module', help='Update module responsibility and purpose', allow_abbrev=False
    )
    add_name_arg(enrich_module_parser)
    enrich_module_parser.add_argument('--responsibility', required=True, help='Module description (1-3 sentences)')
    enrich_module_parser.add_argument('--purpose', help='Module classification (library, extension, deployment, etc.)')
    enrich_module_parser.add_argument('--reasoning', help='Shared reasoning for both responsibility and purpose')
    enrich_module_parser.add_argument(
        '--responsibility-reasoning',
        dest='responsibility_reasoning',
        help='Specific reasoning for responsibility (overrides --reasoning)',
    )
    enrich_module_parser.add_argument(
        '--purpose-reasoning', dest='purpose_reasoning', help='Specific reasoning for purpose (overrides --reasoning)'
    )

    # enrich package
    enrich_package_parser = enrich_subparsers.add_parser(
        'package', help='Add or update key package description', allow_abbrev=False
    )
    add_module_arg(enrich_package_parser)
    add_package_arg(enrich_package_parser)
    enrich_package_parser.add_argument('--description', required=True, help='Package description (1-2 sentences)')
    enrich_package_parser.add_argument(
        '--components', help='Comma-separated list of key class/interface names in the package'
    )

    # enrich skills-by-profile
    enrich_skills_bp_parser = enrich_subparsers.add_parser(
        'skills-by-profile',
        help='Update skills organized by profile (for architecture enrichment)',
        allow_abbrev=False,
    )
    add_module_arg(enrich_skills_bp_parser)
    enrich_skills_bp_parser.add_argument(
        '--skills-json', dest='skills_json', required=True, help='JSON object mapping profile names to skill lists'
    )
    enrich_skills_bp_parser.add_argument('--reasoning', help='Selection rationale for the skill domains')

    # enrich dependencies
    enrich_deps_parser = enrich_subparsers.add_parser(
        'dependencies', help='Update key and internal dependencies', allow_abbrev=False
    )
    add_module_arg(enrich_deps_parser)
    enrich_deps_parser.add_argument('--key', help='Comma-separated key external dependencies')
    enrich_deps_parser.add_argument('--internal', help='Comma-separated internal module dependencies')
    enrich_deps_parser.add_argument('--reasoning', help='Filtering rationale for key dependencies')

    # enrich tip
    enrich_tip_parser = enrich_subparsers.add_parser(
        'tip', help='Add implementation tip to a module', allow_abbrev=False
    )
    add_module_arg(enrich_tip_parser)
    enrich_tip_parser.add_argument('--tip', required=True, help='Implementation tip')

    # enrich insight
    enrich_insight_parser = enrich_subparsers.add_parser(
        'insight', help='Add learned insight to a module', allow_abbrev=False
    )
    add_module_arg(enrich_insight_parser)
    enrich_insight_parser.add_argument('--insight', required=True, help='Learned insight from implementation')

    # enrich best-practice
    enrich_bp_parser = enrich_subparsers.add_parser(
        'best-practice', help='Add best practice to a module', allow_abbrev=False
    )
    add_module_arg(enrich_bp_parser)
    enrich_bp_parser.add_argument('--practice', required=True, help='Established best practice')

    # enrich add-domain
    enrich_add_domain_parser = enrich_subparsers.add_parser(
        'add-domain',
        help="Add a domain's skills to a module additively",
        allow_abbrev=False,
    )
    add_module_arg(enrich_add_domain_parser)
    add_domain_arg(enrich_add_domain_parser)
    enrich_add_domain_parser.add_argument(
        '--include-optionals', dest='include_optionals', action='store_true', help='Include optional skills'
    )
    enrich_add_domain_parser.add_argument('--reasoning', help='Rationale for adding this domain')
    enrich_add_domain_parser.add_argument(
        '--profiles', help='Comma-separated profiles to include (overrides config and detection)'
    )

    # enrich all
    enrich_all_parser = enrich_subparsers.add_parser(
        'all',
        help='Populate skills_by_profile for every module x every applicable extension',
        allow_abbrev=False,
    )
    enrich_all_parser.add_argument(
        '--include-optionals', dest='include_optionals', action='store_true', help='Include optional skills'
    )
    enrich_all_parser.add_argument('--reasoning', help='Shared rationale appended to every enriched module')

    # =========================================================================
    # Parse and Dispatch
    # =========================================================================

    args = parse_args_with_toon_errors(parser)

    # Import command handlers
    from _cmd_client import (
        cmd_commands,
        cmd_diff_modules,
        cmd_files,
        cmd_find,
        cmd_graph,
        cmd_impact,
        cmd_info,
        cmd_module,
        cmd_modules,
        cmd_neighbors,
        cmd_overview,
        cmd_path,
        cmd_profiles,
        cmd_resolve,
        cmd_siblings,
        cmd_which_module,
    )
    from _cmd_enrich import (
        cmd_enrich_add_domain,
        cmd_enrich_all,
        cmd_enrich_best_practice,
        cmd_enrich_dependencies,
        cmd_enrich_insight,
        cmd_enrich_module,
        cmd_enrich_package,
        cmd_enrich_project,
        cmd_enrich_skills_by_profile,
        cmd_enrich_tip,
    )
    from _cmd_manage import (
        cmd_derived,
        cmd_derived_module,
        cmd_discover,
        cmd_init,
    )
    from _cmd_suggest import cmd_suggest_domains

    # Dispatch to handlers
    handlers = {
        'discover': cmd_discover,
        'init': cmd_init,
        'derived': cmd_derived,
        'derived-module': cmd_derived_module,
        'info': cmd_info,
        'modules': cmd_modules,
        'graph': cmd_graph,
        'path': cmd_path,
        'neighbors': cmd_neighbors,
        'impact': cmd_impact,
        'module': cmd_module,
        'overview': cmd_overview,
        'commands': cmd_commands,
        'resolve': cmd_resolve,
        'profiles': cmd_profiles,
        'siblings': cmd_siblings,
        'suggest-domains': cmd_suggest_domains,
        'files': cmd_files,
        'which-module': cmd_which_module,
        'find': cmd_find,
        'diff-modules': cmd_diff_modules,
    }

    if args.command == 'enrich':
        enrich_handlers = {
            'project': cmd_enrich_project,
            'module': cmd_enrich_module,
            'package': cmd_enrich_package,
            'skills-by-profile': cmd_enrich_skills_by_profile,
            'dependencies': cmd_enrich_dependencies,
            'tip': cmd_enrich_tip,
            'insight': cmd_enrich_insight,
            'best-practice': cmd_enrich_best_practice,
            'add-domain': cmd_enrich_add_domain,
            'all': cmd_enrich_all,
        }
        handler = enrich_handlers.get(args.enrich_command)
    else:
        handler = handlers.get(args.command)

    if handler:
        result = handler(args)
        if isinstance(result, str):
            print(result, end='' if result.endswith('\n') else '\n')
        else:
            output_toon(result)
        return 0
    else:
        parser.print_help()
        return 1


if __name__ == '__main__':
    main()
