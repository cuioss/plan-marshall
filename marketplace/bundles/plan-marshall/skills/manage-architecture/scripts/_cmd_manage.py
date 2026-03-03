#!/usr/bin/env python3
"""Manage command handlers for architecture script.

Handles: discover, init, derived, derived-module
"""

import sys
from pathlib import Path

from _architecture_core import (
    DataNotFoundError,
    ModuleNotFoundError,
    error_data_not_found,
    error_module_not_found,
    get_derived_path,
    get_enriched_path,
    get_module,
    get_module_names,
    load_derived_data,
    load_llm_enriched,
    print_toon_list,
    print_toon_table,
    save_derived_data,
    save_llm_enriched,
)

# =============================================================================
# API Functions
# =============================================================================


def api_discover(project_dir: str = '.', force: bool = False) -> dict:
    """Run extension API discovery and save results.

    Args:
        project_dir: Project directory path
        force: Overwrite existing derived-data.json

    Returns:
        Dict with status, modules_discovered, output_file
    """
    derived_path = get_derived_path(project_dir)

    if derived_path.exists() and not force:
        return {'status': 'exists', 'file': str(derived_path), 'message': 'Use --force to overwrite'}

    # Import extension API for discovery (PYTHONPATH set by executor)
    from extension_discovery import discover_project_modules  # type: ignore[import-not-found]

    # Run discovery
    project_path = Path(project_dir).resolve()
    result = discover_project_modules(project_path)

    # Build derived-data structure
    derived_data = {
        'project': {'name': project_path.name},
        'modules': result.get('modules', {}),
        'extensions_used': result.get('extensions_used', []),
    }

    # Save
    output_path = save_derived_data(derived_data, project_dir)

    return {'status': 'success', 'modules_discovered': len(derived_data['modules']), 'output_file': str(output_path)}


def api_init(project_dir: str = '.', check: bool = False, force: bool = False) -> dict:
    """Initialize llm-enriched.json template.

    Args:
        project_dir: Project directory path
        check: Only check if file exists
        force: Overwrite existing file

    Returns:
        Dict with status and file info
    """
    enriched_path = get_enriched_path(project_dir)

    if check:
        if enriched_path.exists():
            enriched = load_llm_enriched(project_dir)
            return {
                'status': 'exists',
                'file': str(enriched_path),
                'modules_enriched': len(enriched.get('modules', {})),
            }
        else:
            return {'status': 'missing', 'file': str(enriched_path)}

    if enriched_path.exists() and not force:
        return {'status': 'exists', 'file': str(enriched_path), 'message': 'Use --force to overwrite'}

    # Load derived data to get module list
    try:
        derived = load_derived_data(project_dir)
    except DataNotFoundError as e:
        return {'status': 'error', 'error': str(e)}

    # Create empty enrichment structure
    enriched = {'project': {'description': '', 'description_reasoning': ''}, 'modules': {}}

    # Create stub for each module
    for module_name in derived.get('modules', {}).keys():
        enriched['modules'][module_name] = {
            'responsibility': '',
            'responsibility_reasoning': '',
            'purpose': '',
            'purpose_reasoning': '',
            'key_packages': {},
            'internal_dependencies': [],
            'key_dependencies': [],
            'key_dependencies_reasoning': '',
            'skills_by_profile': {},
            'skills_by_profile_reasoning': '',
            'tips': [],
            'insights': [],
            'best_practices': [],
        }

    # Save
    output_path = save_llm_enriched(enriched, project_dir)

    return {'status': 'success', 'modules_initialized': len(enriched['modules']), 'output_file': str(output_path)}


def api_get_derived(project_dir: str = '.') -> dict:
    """Get raw discovered data for all modules.

    Args:
        project_dir: Project directory path

    Returns:
        Dict with project and modules data
    """
    derived = load_derived_data(project_dir)
    return derived


def api_get_derived_module(module_name: str, project_dir: str = '.') -> dict:
    """Get raw discovered data for a single module.

    Args:
        module_name: Module name
        project_dir: Project directory path

    Returns:
        Module data dict

    Raises:
        ModuleNotFoundError: If module not found
    """
    derived = load_derived_data(project_dir)
    return get_module(derived, module_name)


def list_modules(project_dir: str = '.') -> list:
    """List module names.

    Args:
        project_dir: Project directory path

    Returns:
        List of module names
    """
    derived = load_derived_data(project_dir)
    return get_module_names(derived)


# =============================================================================
# CLI Handlers
# =============================================================================


def cmd_discover(args) -> int:
    """CLI handler for discover command."""
    try:
        result = api_discover(args.project_dir, args.force)

        print(f'status\t{result["status"]}')
        if result['status'] == 'success':
            print(f'modules_discovered\t{result["modules_discovered"]}')
            print(f'output_file\t{result["output_file"]}')
        elif result['status'] == 'exists':
            print(f'file\t{result["file"]}')
            print(f'message\t{result.get("message", "")}')
        else:
            print(f'error\t{result.get("error", "Unknown error")}')
            return 1

        return 0
    except Exception as e:
        print('status\terror', file=sys.stderr)
        print(f'error\t{e}', file=sys.stderr)
        return 1


def cmd_init(args) -> int:
    """CLI handler for init command."""
    try:
        result = api_init(args.project_dir, args.check, args.force)

        print(f'status\t{result["status"]}')
        if result['status'] == 'success':
            print(f'modules_initialized\t{result["modules_initialized"]}')
            print(f'output_file\t{result["output_file"]}')
        elif result['status'] == 'exists':
            print(f'file\t{result["file"]}')
            if 'modules_enriched' in result:
                print(f'modules_enriched\t{result["modules_enriched"]}')
            if 'message' in result:
                print(f'message\t{result["message"]}')
        elif result['status'] == 'missing':
            print(f'file\t{result["file"]}')
        else:
            print(f'error\t{result.get("error", "Unknown error")}')
            return 1

        return 0
    except Exception as e:
        print('status\terror', file=sys.stderr)
        print(f'error\t{e}', file=sys.stderr)
        return 1


def cmd_derived(args) -> int:
    """CLI handler for derived command."""
    try:
        derived = api_get_derived(args.project_dir)

        # Output project info
        project = derived.get('project', {})
        print('project:')
        print(f'  name: {project.get("name", "")}')
        print()

        # Output modules table
        modules = derived.get('modules', {})
        items = []
        for name, data in modules.items():
            paths = data.get('paths', {})
            metadata = data.get('metadata', {})
            build_systems = data.get('build_systems', [])
            items.append(
                {
                    'name': name,
                    'path': paths.get('module', ''),
                    'build_systems': '+'.join(build_systems) if build_systems else '',
                    'readme': paths.get('readme', ''),
                    'description': metadata.get('description', ''),
                }
            )

        print_toon_table('modules', items, ['name', 'path', 'build_systems', 'readme', 'description'])

        return 0
    except DataNotFoundError:
        error_data_not_found(str(get_derived_path(args.project_dir)), "Run 'architecture.py discover' first")
        return 1
    except Exception as e:
        print('status\terror', file=sys.stderr)
        print(f'error\t{e}', file=sys.stderr)
        return 1


def cmd_derived_module(args) -> int:
    """CLI handler for derived-module command."""
    try:
        derived = load_derived_data(args.project_dir)
        module = get_module(derived, args.name)

        # Output module info
        print('module:')
        print(f'  name: {module.get("name", args.name)}')
        paths = module.get('paths', {})
        print(f'  path: {paths.get("module", "")}')
        build_systems = module.get('build_systems', [])
        print(f'  build_systems: {"+".join(build_systems) if build_systems else ""}')
        print()

        # Output paths
        print('paths:')
        if paths.get('readme'):
            print(f'  readme: {paths["readme"]}')
        if paths.get('descriptor'):
            print(f'  descriptor: {paths["descriptor"]}')
        sources = paths.get('sources', [])
        if sources:
            print(f'  sources[{len(sources)}]:')
            for s in sources:
                print(f'    - {s}')
        tests = paths.get('tests', [])
        if tests:
            print(f'  tests[{len(tests)}]:')
            for t in tests:
                print(f'    - {t}')
        print()

        # Output metadata
        metadata = module.get('metadata', {})
        if metadata:
            print('metadata:')
            for key, value in metadata.items():
                if value and not isinstance(value, (list, dict)):
                    print(f'  {key}: {value}')
            print()

        # Output packages table
        packages = module.get('packages', {})
        if packages:
            pkg_items = []
            for pkg_name, pkg_data in packages.items():
                pkg_items.append(
                    {
                        'name': pkg_name,
                        'path': pkg_data.get('path', ''),
                        'package_info': pkg_data.get('package_info', ''),
                    }
                )
            print_toon_table('packages', pkg_items, ['name', 'path', 'package_info'])
            print()

        # Output dependencies
        deps = module.get('dependencies', [])
        if deps:
            print_toon_list('dependencies', deps[:20])  # Limit to 20 for readability
            if len(deps) > 20:
                print(f'  ... and {len(deps) - 20} more')
            print()

        # Output stats
        stats = module.get('stats', {})
        if stats:
            print('stats:')
            for key, value in stats.items():
                print(f'  {key}: {value}')
            print()

        # Output commands
        commands = module.get('commands', {})
        if commands:
            print_toon_list('commands', list(commands.keys()))

        return 0
    except DataNotFoundError:
        error_data_not_found(str(get_derived_path(args.project_dir)), "Run 'architecture.py discover' first")
        return 1
    except ModuleNotFoundError:
        modules = get_module_names(load_derived_data(args.project_dir))
        error_module_not_found(args.name, modules)
        return 1
    except Exception as e:
        print('status\terror', file=sys.stderr)
        print(f'error\t{e}', file=sys.stderr)
        return 1
