#!/usr/bin/env python3
"""Manage command handlers for architecture script.

Handles: discover, init, derived, derived-module
"""

from pathlib import Path

from _architecture_core import (
    DataNotFoundError,
    ModuleNotFoundInProjectError,
    error_result_module_not_found,
    get_derived_path,
    get_enriched_path,
    get_module,
    get_module_names,
    load_derived_data,
    load_llm_enriched,
    require_derived_data_result,
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
        ModuleNotFoundInProjectError: If module not found
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


def cmd_discover(args) -> dict:
    """CLI handler for discover command."""
    try:
        return api_discover(args.project_dir, args.force)
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


def cmd_init(args) -> dict:
    """CLI handler for init command."""
    try:
        return api_init(args.project_dir, args.check, args.force)
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


def cmd_derived(args) -> dict:
    """CLI handler for derived command."""
    try:
        derived = api_get_derived(args.project_dir)
        return {'status': 'success', **derived}
    except DataNotFoundError:
        return require_derived_data_result(args.project_dir)
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


def cmd_derived_module(args) -> dict:
    """CLI handler for derived-module command."""
    try:
        module = api_get_derived_module(args.name, args.project_dir)
        return {'status': 'success', 'module_name': args.name, 'module': module}
    except DataNotFoundError:
        return require_derived_data_result(args.project_dir)
    except ModuleNotFoundInProjectError:
        modules = get_module_names(load_derived_data(args.project_dir))
        return error_result_module_not_found(args.name, modules)
    except Exception as e:
        return {'status': 'error', 'error': str(e)}
