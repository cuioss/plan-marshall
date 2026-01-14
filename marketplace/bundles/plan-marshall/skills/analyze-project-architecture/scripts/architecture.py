#!/usr/bin/env python3
"""Architecture analysis CLI.

Entry point for all architecture operations. Dispatches to command modules.
"""

import argparse
import sys


def main():
    parser = argparse.ArgumentParser(
        description='Architecture analysis and enrichment operations'
    )
    parser.add_argument(
        '--project-dir',
        default='.',
        help='Project directory (default: current directory)'
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    # =========================================================================
    # Manage Commands (Setup)
    # =========================================================================

    # discover - Run extension API discovery
    discover_parser = subparsers.add_parser(
        'discover',
        help='Run extension API discovery'
    )
    discover_parser.add_argument(
        '--force',
        action='store_true',
        help='Overwrite existing derived-data.json'
    )

    # init - Initialize enrichment file
    init_parser = subparsers.add_parser(
        'init',
        help='Initialize llm-enriched.json from derived data'
    )
    init_parser.add_argument(
        '--check',
        action='store_true',
        help='Check if enrichment file exists, output status only'
    )
    init_parser.add_argument(
        '--force',
        action='store_true',
        help='Overwrite existing llm-enriched.json'
    )

    # =========================================================================
    # Manage Commands (Read Raw)
    # =========================================================================

    # derived - Read raw discovered data for all modules
    subparsers.add_parser(
        'derived',
        help='Read raw discovered data for all modules'
    )

    # derived-module - Read raw discovered data for single module
    derived_module_parser = subparsers.add_parser(
        'derived-module',
        help='Read raw discovered data for a single module'
    )
    derived_module_parser.add_argument(
        '--name',
        required=True,
        help='Module name'
    )

    # =========================================================================
    # Client Commands (Consumer Queries)
    # =========================================================================

    # info - Project summary
    subparsers.add_parser(
        'info',
        help='Get project summary with metadata and module overview'
    )

    # modules - List module names
    modules_parser = subparsers.add_parser(
        'modules',
        help='List available module names'
    )
    modules_parser.add_argument(
        '--command',
        dest='filter_command',  # Avoid collision with subparser dest='command'
        help='Filter to modules that provide this command'
    )

    # graph - Get module dependency graph
    graph_parser = subparsers.add_parser(
        'graph',
        help='Get complete internal module dependency graph'
    )
    graph_parser.add_argument(
        '--full',
        action='store_true',
        help='Include aggregator modules (pom-only parents)'
    )

    # module - Get module information
    module_parser = subparsers.add_parser(
        'module',
        help='Get module information'
    )
    module_parser.add_argument(
        '--name',
        help='Module name (default: root module)'
    )
    module_parser.add_argument(
        '--full',
        action='store_true',
        help='Include all fields (packages, dependencies, reasoning)'
    )

    # commands - List commands for module
    commands_parser = subparsers.add_parser(
        'commands',
        help='List available commands for a module'
    )
    commands_parser.add_argument(
        '--name',
        help='Module name (default: root module)'
    )

    # resolve - Resolve command to executable
    resolve_parser = subparsers.add_parser(
        'resolve',
        help='Resolve command to executable form'
    )
    resolve_parser.add_argument(
        '--command',
        required=True,
        help='Command name to resolve'
    )
    resolve_parser.add_argument(
        '--name',
        help='Module name (default: root module)'
    )

    # profiles - Extract unique profiles from modules
    profiles_parser = subparsers.add_parser(
        'profiles',
        help='Extract unique profile keys from skills_by_profile for modules'
    )
    profiles_parser.add_argument(
        '--modules',
        help='Comma-separated module names (default: all modules with enrichment)'
    )

    # =========================================================================
    # Enrich Commands (Write Enrichment)
    # =========================================================================

    enrich_parser = subparsers.add_parser(
        'enrich',
        help='Enrichment commands'
    )
    enrich_subparsers = enrich_parser.add_subparsers(
        dest='enrich_command',
        required=True
    )

    # enrich project
    enrich_project_parser = enrich_subparsers.add_parser(
        'project',
        help='Update project description'
    )
    enrich_project_parser.add_argument(
        '--description',
        required=True,
        help='Project description (1-2 sentences)'
    )
    enrich_project_parser.add_argument(
        '--reasoning',
        help='Source/rationale for the description (e.g., "Derived from README.md first paragraph")'
    )

    # enrich module
    enrich_module_parser = enrich_subparsers.add_parser(
        'module',
        help='Update module responsibility and purpose'
    )
    enrich_module_parser.add_argument(
        '--name',
        required=True,
        help='Module name'
    )
    enrich_module_parser.add_argument(
        '--responsibility',
        required=True,
        help='Module description (1-3 sentences)'
    )
    enrich_module_parser.add_argument(
        '--purpose',
        help='Module classification (library, extension, deployment, etc.)'
    )
    enrich_module_parser.add_argument(
        '--reasoning',
        help='Shared reasoning for both responsibility and purpose'
    )
    enrich_module_parser.add_argument(
        '--responsibility-reasoning',
        dest='responsibility_reasoning',
        help='Specific reasoning for responsibility (overrides --reasoning)'
    )
    enrich_module_parser.add_argument(
        '--purpose-reasoning',
        dest='purpose_reasoning',
        help='Specific reasoning for purpose (overrides --reasoning)'
    )

    # enrich package
    enrich_package_parser = enrich_subparsers.add_parser(
        'package',
        help='Add or update key package description'
    )
    enrich_package_parser.add_argument(
        '--module',
        required=True,
        help='Module name'
    )
    enrich_package_parser.add_argument(
        '--package',
        required=True,
        help='Full package name'
    )
    enrich_package_parser.add_argument(
        '--description',
        required=True,
        help='Package description (1-2 sentences)'
    )
    enrich_package_parser.add_argument(
        '--components',
        help='Comma-separated list of key class/interface names in the package'
    )

    # enrich skills-by-profile
    enrich_skills_bp_parser = enrich_subparsers.add_parser(
        'skills-by-profile',
        help='Update skills organized by profile (for architecture enrichment)'
    )
    enrich_skills_bp_parser.add_argument(
        '--module',
        required=True,
        help='Module name'
    )
    enrich_skills_bp_parser.add_argument(
        '--skills-json',
        dest='skills_json',
        required=True,
        help='JSON object mapping profile names to skill lists'
    )
    enrich_skills_bp_parser.add_argument(
        '--reasoning',
        help='Selection rationale for the skill domains'
    )

    # enrich dependencies
    enrich_deps_parser = enrich_subparsers.add_parser(
        'dependencies',
        help='Update key and internal dependencies'
    )
    enrich_deps_parser.add_argument(
        '--module',
        required=True,
        help='Module name'
    )
    enrich_deps_parser.add_argument(
        '--key',
        help='Comma-separated key external dependencies'
    )
    enrich_deps_parser.add_argument(
        '--internal',
        help='Comma-separated internal module dependencies'
    )
    enrich_deps_parser.add_argument(
        '--reasoning',
        help='Filtering rationale for key dependencies'
    )

    # enrich tip
    enrich_tip_parser = enrich_subparsers.add_parser(
        'tip',
        help='Add implementation tip to a module'
    )
    enrich_tip_parser.add_argument(
        '--module',
        required=True,
        help='Module name'
    )
    enrich_tip_parser.add_argument(
        '--tip',
        required=True,
        help='Implementation tip'
    )

    # enrich insight
    enrich_insight_parser = enrich_subparsers.add_parser(
        'insight',
        help='Add learned insight to a module'
    )
    enrich_insight_parser.add_argument(
        '--module',
        required=True,
        help='Module name'
    )
    enrich_insight_parser.add_argument(
        '--insight',
        required=True,
        help='Learned insight from implementation'
    )

    # enrich best-practice
    enrich_bp_parser = enrich_subparsers.add_parser(
        'best-practice',
        help='Add best practice to a module'
    )
    enrich_bp_parser.add_argument(
        '--module',
        required=True,
        help='Module name'
    )
    enrich_bp_parser.add_argument(
        '--practice',
        required=True,
        help='Established best practice'
    )

    # =========================================================================
    # Parse and Dispatch
    # =========================================================================

    args = parser.parse_args()

    # Import command handlers
    from _cmd_client import (
        cmd_commands,
        cmd_graph,
        cmd_info,
        cmd_module,
        cmd_modules,
        cmd_profiles,
        cmd_resolve,
    )
    from _cmd_enrich import (
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

    # Dispatch to handlers
    handlers = {
        'discover': cmd_discover,
        'init': cmd_init,
        'derived': cmd_derived,
        'derived-module': cmd_derived_module,
        'info': cmd_info,
        'modules': cmd_modules,
        'graph': cmd_graph,
        'module': cmd_module,
        'commands': cmd_commands,
        'resolve': cmd_resolve,
        'profiles': cmd_profiles,
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
        }
        handler = enrich_handlers.get(args.enrich_command)
    else:
        handler = handlers.get(args.command)

    if handler:
        return handler(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main() or 0)
