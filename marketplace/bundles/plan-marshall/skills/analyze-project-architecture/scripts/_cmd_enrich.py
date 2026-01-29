#!/usr/bin/env python3
"""Enrich command handlers for architecture script.

Handles: enrich project, module, package, skills, dependencies, tip, insight, best-practice
These commands write to llm-enriched.json.
"""

import sys
from typing import Any

from _architecture_core import (
    DataNotFoundError,
    ModuleNotFoundError,
    get_enriched_path,
    get_module_names,
    load_derived_data,
    load_llm_enriched,
    print_toon_list,
    save_llm_enriched,
)

# =============================================================================
# API Functions
# =============================================================================


def enrich_project(description: str, project_dir: str = '.', reasoning: str | None = None) -> dict:
    """Update project description.

    Args:
        description: Project description (1-2 sentences)
        project_dir: Project directory path
        reasoning: Source/rationale for the description

    Returns:
        Dict with status and updated field
    """
    enriched = load_llm_enriched(project_dir)

    if 'project' not in enriched:
        enriched['project'] = {}

    enriched['project']['description'] = description

    # Only update reasoning if provided (preserve existing)
    if reasoning is not None:
        enriched['project']['description_reasoning'] = reasoning

    save_llm_enriched(enriched, project_dir)

    return {'status': 'success', 'updated': 'project.description'}


def enrich_module(
    module_name: str,
    responsibility: str,
    purpose: str | None = None,
    project_dir: str = '.',
    reasoning: str | None = None,
    responsibility_reasoning: str | None = None,
    purpose_reasoning: str | None = None,
) -> dict:
    """Update module responsibility and purpose.

    Args:
        module_name: Module name
        responsibility: Module description (1-3 sentences)
        purpose: Module classification (library, extension, etc.)
        project_dir: Project directory path
        reasoning: Shared reasoning for both fields (convenience)
        responsibility_reasoning: Specific reasoning for responsibility
        purpose_reasoning: Specific reasoning for purpose

    Returns:
        Dict with status, module, and updated fields
    """
    # Validate module exists in derived data
    derived = load_derived_data(project_dir)
    modules = get_module_names(derived)
    if module_name not in modules:
        raise ModuleNotFoundError(f'Module not found: {module_name}', modules)

    enriched = load_llm_enriched(project_dir)

    if 'modules' not in enriched:
        enriched['modules'] = {}
    if module_name not in enriched['modules']:
        enriched['modules'][module_name] = {}

    updated = []
    enriched['modules'][module_name]['responsibility'] = responsibility
    updated.append('responsibility')

    # Handle responsibility reasoning
    resp_reason = responsibility_reasoning or reasoning
    if resp_reason is not None:
        enriched['modules'][module_name]['responsibility_reasoning'] = resp_reason

    if purpose:
        enriched['modules'][module_name]['purpose'] = purpose
        updated.append('purpose')

        # Handle purpose reasoning
        purp_reason = purpose_reasoning or reasoning
        if purp_reason is not None:
            enriched['modules'][module_name]['purpose_reasoning'] = purp_reason

    save_llm_enriched(enriched, project_dir)

    return {'status': 'success', 'module': module_name, 'updated': updated}


def enrich_package(
    module_name: str, package_name: str, description: str, project_dir: str = '.', components: list | None = None
) -> dict:
    """Add or update key package description and components.

    Args:
        module_name: Module name
        package_name: Full package name
        description: Package description (1-2 sentences)
        project_dir: Project directory path
        components: List of key class/interface names in the package

    Returns:
        Dict with status, module, package, action, and optionally components
    """
    # Validate module exists
    derived = load_derived_data(project_dir)
    modules = get_module_names(derived)
    if module_name not in modules:
        raise ModuleNotFoundError(f'Module not found: {module_name}', modules)

    enriched = load_llm_enriched(project_dir)

    if 'modules' not in enriched:
        enriched['modules'] = {}
    if module_name not in enriched['modules']:
        enriched['modules'][module_name] = {}
    if 'key_packages' not in enriched['modules'][module_name]:
        enriched['modules'][module_name]['key_packages'] = {}

    action = 'updated' if package_name in enriched['modules'][module_name]['key_packages'] else 'added'

    # Preserve existing components if not provided
    existing = enriched['modules'][module_name]['key_packages'].get(package_name, {})
    existing_components = existing.get('components')

    pkg_data: dict[str, Any] = {'description': description}

    # Use provided components, or preserve existing
    if components is not None:
        pkg_data['components'] = components
    elif existing_components is not None:
        pkg_data['components'] = existing_components

    enriched['modules'][module_name]['key_packages'][package_name] = pkg_data

    save_llm_enriched(enriched, project_dir)

    result = {'status': 'success', 'module': module_name, 'package': package_name, 'action': action}

    if 'components' in pkg_data:
        result['components'] = pkg_data['components']

    return result


def _extract_skill_names_from_profile(profile_data: dict | list) -> list[str]:
    """Extract skill names from a profile, handling both flat and structured formats.

    Args:
        profile_data: Either a flat list of skills or a dict with defaults/optionals

    Returns:
        List of skill names
    """
    if isinstance(profile_data, list):
        # Legacy flat format: ["skill1", "skill2"]
        return profile_data

    # New structured format: {defaults: [...], optionals: [...]}
    skills = []
    for section in ['defaults', 'optionals']:
        entries = profile_data.get(section, [])
        for entry in entries:
            if isinstance(entry, dict):
                skill = entry.get('skill', '')
                if skill:
                    skills.append(skill)
            elif isinstance(entry, str):
                skills.append(entry)
    return skills


def _validate_skills_by_profile_structure(skills_by_profile: dict) -> list[str]:
    """Validate the skills_by_profile structure.

    Supports two formats:
    1. Flat lists (legacy): {"profile": ["skill1", "skill2"]}
    2. Defaults/optionals with descriptions (new):
       {"profile": {"defaults": [{"skill": "...", "description": "..."}], "optionals": [...]}}

    Args:
        skills_by_profile: Dict mapping profile names to skill lists or structured dicts

    Returns:
        List of warning messages (empty if valid)
    """
    warnings: list[str] = []

    for profile_name, profile_data in skills_by_profile.items():
        if isinstance(profile_data, list):
            # Legacy flat format - validate skill notation
            for skill in profile_data:
                if ':' not in skill:
                    warnings.append(f"Skill '{skill}' in profile '{profile_name}' missing bundle:skill notation")
        elif isinstance(profile_data, dict):
            # New structured format - validate defaults and optionals
            for section in ['defaults', 'optionals']:
                entries = profile_data.get(section, [])
                if not isinstance(entries, list):
                    warnings.append(f"Profile '{profile_name}.{section}' must be a list")
                    continue
                for i, entry in enumerate(entries):
                    if isinstance(entry, dict):
                        if 'skill' not in entry:
                            warnings.append(f"Entry {i} in '{profile_name}.{section}' missing 'skill' field")
                        elif ':' not in entry.get('skill', ''):
                            warnings.append(
                                f"Skill '{entry.get('skill')}' in '{profile_name}.{section}' missing bundle:skill notation"
                            )
                        if 'description' not in entry:
                            warnings.append(f"Entry {i} in '{profile_name}.{section}' missing 'description' field")
                    elif isinstance(entry, str):
                        # Allow plain strings for backwards compatibility
                        if ':' not in entry:
                            warnings.append(f"Skill '{entry}' in '{profile_name}.{section}' missing bundle:skill notation")
                    else:
                        warnings.append(f"Entry {i} in '{profile_name}.{section}' must be a dict or string")
        else:
            warnings.append(f"Profile '{profile_name}' must be a list or dict, got {type(profile_data).__name__}")

    return warnings


def _validate_skills_for_technology(skills_by_profile: dict, technology: str) -> list[str]:
    """Validate that skills match the module's technology.

    Args:
        skills_by_profile: Dict mapping profile names to skill lists or structured dicts
        technology: Module technology (maven, npm, gradle)

    Returns:
        List of warning messages (empty if no issues)
    """
    warnings: list[str] = []

    # Technology to expected skill bundle patterns
    tech_skill_patterns = {
        'maven': ['pm-dev-java:', 'pm-dev-java-cui:'],
        'gradle': ['pm-dev-java:', 'pm-dev-java-cui:'],
        'npm': ['pm-dev-frontend:'],
    }

    expected_patterns = tech_skill_patterns.get(technology, [])
    if not expected_patterns:
        return warnings  # Unknown technology, skip validation

    # Check each skill (handles both flat and structured formats)
    for _profile_name, profile_data in skills_by_profile.items():
        skills = _extract_skill_names_from_profile(profile_data)
        for skill in skills:
            # Check if skill matches expected patterns
            matches = any(skill.startswith(pattern) for pattern in expected_patterns)
            if not matches:
                # Check if it's from a different technology
                for other_tech, other_patterns in tech_skill_patterns.items():
                    if other_tech != technology:
                        if any(skill.startswith(p) for p in other_patterns):
                            warnings.append(
                                f"Skill '{skill}' appears to be for {other_tech}, but module technology is {technology}"
                            )
                            break

    return warnings


def enrich_skills_by_profile(
    module_name: str, skills_by_profile: dict, project_dir: str = '.', reasoning: str | None = None
) -> dict:
    """Update skills organized by profile.

    Supports two formats:
    1. Flat lists (legacy): {"implementation": ["skill1", "skill2"]}
    2. Defaults/optionals with descriptions (new):
       {"implementation": {"defaults": [{"skill": "...", "description": "..."}], "optionals": [...]}}

    Args:
        module_name: Module name
        skills_by_profile: Dict mapping profile names to skill lists or structured dicts
        project_dir: Project directory path
        reasoning: Selection rationale

    Returns:
        Dict with status, module, skills_by_profile, and optional warnings
    """
    # Validate module exists
    derived = load_derived_data(project_dir)
    modules = get_module_names(derived)
    if module_name not in modules:
        raise ModuleNotFoundError(f'Module not found: {module_name}', modules)

    # Validate structure
    warnings = _validate_skills_by_profile_structure(skills_by_profile)

    # Get module data to check technology for virtual modules
    module_data = derived.get('modules', {}).get(module_name, {})
    virtual_module = module_data.get('virtual_module', {})
    technology = virtual_module.get('technology') if virtual_module else None

    # If no virtual_module, infer technology from build_systems
    if not technology:
        build_systems = module_data.get('build_systems', [])
        if build_systems:
            technology = build_systems[0]

    # Validate skills match technology
    if technology:
        warnings.extend(_validate_skills_for_technology(skills_by_profile, technology))

    enriched = load_llm_enriched(project_dir)

    if 'modules' not in enriched:
        enriched['modules'] = {}
    if module_name not in enriched['modules']:
        enriched['modules'][module_name] = {}

    enriched['modules'][module_name]['skills_by_profile'] = skills_by_profile

    if reasoning is not None:
        enriched['modules'][module_name]['skills_by_profile_reasoning'] = reasoning

    save_llm_enriched(enriched, project_dir)

    result = {'status': 'success', 'module': module_name, 'skills_by_profile': skills_by_profile}

    if warnings:
        result['warnings'] = warnings

    return result


def enrich_dependencies(
    module_name: str,
    key_deps: list | None = None,
    internal_deps: list | None = None,
    project_dir: str = '.',
    reasoning: str | None = None,
) -> dict:
    """Update key and internal dependencies.

    Args:
        module_name: Module name
        key_deps: List of key external dependencies
        internal_deps: List of internal module dependencies
        project_dir: Project directory path
        reasoning: Filtering rationale for key dependencies

    Returns:
        Dict with status, module, and updated dependencies
    """
    # Validate module exists
    derived = load_derived_data(project_dir)
    modules = get_module_names(derived)
    if module_name not in modules:
        raise ModuleNotFoundError(f'Module not found: {module_name}', modules)

    enriched = load_llm_enriched(project_dir)

    if 'modules' not in enriched:
        enriched['modules'] = {}
    if module_name not in enriched['modules']:
        enriched['modules'][module_name] = {}

    result: dict[str, Any] = {'status': 'success', 'module': module_name}

    if key_deps is not None:
        enriched['modules'][module_name]['key_dependencies'] = key_deps
        result['key_dependencies'] = key_deps

    if internal_deps is not None:
        enriched['modules'][module_name]['internal_dependencies'] = internal_deps
        result['internal_dependencies'] = internal_deps

    if reasoning is not None:
        enriched['modules'][module_name]['key_dependencies_reasoning'] = reasoning

    save_llm_enriched(enriched, project_dir)

    return result


def enrich_tip(module_name: str, tip: str, project_dir: str = '.') -> dict:
    """Add implementation tip to a module.

    Args:
        module_name: Module name
        tip: Implementation tip
        project_dir: Project directory path

    Returns:
        Dict with status, module, and tips list
    """
    return _append_to_list(module_name, 'tips', tip, project_dir)


def enrich_insight(module_name: str, insight: str, project_dir: str = '.') -> dict:
    """Add learned insight to a module.

    Args:
        module_name: Module name
        insight: Learned insight from implementation
        project_dir: Project directory path

    Returns:
        Dict with status, module, and insights list
    """
    return _append_to_list(module_name, 'insights', insight, project_dir)


def enrich_best_practice(module_name: str, practice: str, project_dir: str = '.') -> dict:
    """Add best practice to a module.

    Args:
        module_name: Module name
        practice: Established best practice
        project_dir: Project directory path

    Returns:
        Dict with status, module, and best_practices list
    """
    return _append_to_list(module_name, 'best_practices', practice, project_dir)


def _append_to_list(module_name: str, field: str, value: str, project_dir: str = '.') -> dict:
    """Append value to a list field in module enrichment.

    Args:
        module_name: Module name
        field: Field name (tips, insights, best_practices)
        value: Value to append
        project_dir: Project directory path

    Returns:
        Dict with status, module, and field list
    """
    # Validate module exists
    derived = load_derived_data(project_dir)
    modules = get_module_names(derived)
    if module_name not in modules:
        raise ModuleNotFoundError(f'Module not found: {module_name}', modules)

    enriched = load_llm_enriched(project_dir)

    if 'modules' not in enriched:
        enriched['modules'] = {}
    if module_name not in enriched['modules']:
        enriched['modules'][module_name] = {}
    if field not in enriched['modules'][module_name]:
        enriched['modules'][module_name][field] = []

    # Append if not duplicate
    if value not in enriched['modules'][module_name][field]:
        enriched['modules'][module_name][field].append(value)

    save_llm_enriched(enriched, project_dir)

    return {'status': 'success', 'module': module_name, field: enriched['modules'][module_name][field]}


# =============================================================================
# CLI Handlers
# =============================================================================


def _handle_module_not_found(module_name: str, project_dir: str) -> int:
    """Handle module not found error with available modules list."""
    try:
        derived = load_derived_data(project_dir)
        modules = get_module_names(derived)
    except Exception:
        modules = []

    print('error: Module not found')
    print(f'module: {module_name}')
    print_toon_list('available', modules)
    return 1


def cmd_enrich_project(args) -> int:
    """CLI handler for enrich project command."""
    try:
        reasoning = getattr(args, 'reasoning', None)
        result = enrich_project(args.description, args.project_dir, reasoning)
        print(f'status\t{result["status"]}')
        print(f'updated\t{result["updated"]}')
        return 0
    except DataNotFoundError:
        print('error: Enrichment data not found')
        print(f'expected_file: {get_enriched_path(args.project_dir)}')
        print("resolution: Run 'architecture.py init' first")
        return 1
    except Exception as e:
        print('status\terror', file=sys.stderr)
        print(f'error\t{e}', file=sys.stderr)
        return 1


def cmd_enrich_module(args) -> int:
    """CLI handler for enrich module command."""
    try:
        reasoning = getattr(args, 'reasoning', None)
        responsibility_reasoning = getattr(args, 'responsibility_reasoning', None)
        purpose_reasoning = getattr(args, 'purpose_reasoning', None)
        result = enrich_module(
            args.name,
            args.responsibility,
            args.purpose,
            args.project_dir,
            reasoning,
            responsibility_reasoning,
            purpose_reasoning,
        )
        print(f'status\t{result["status"]}')
        print(f'module\t{result["module"]}')
        print_toon_list('updated', result['updated'])
        return 0
    except ModuleNotFoundError:
        return _handle_module_not_found(args.name, args.project_dir)
    except DataNotFoundError:
        print('error: Enrichment data not found')
        print(f'expected_file: {get_enriched_path(args.project_dir)}')
        print("resolution: Run 'architecture.py init' first")
        return 1
    except Exception as e:
        print('status\terror', file=sys.stderr)
        print(f'error\t{e}', file=sys.stderr)
        return 1


def cmd_enrich_package(args) -> int:
    """CLI handler for enrich package command."""
    try:
        components = None
        if hasattr(args, 'components') and args.components:
            components = [c.strip() for c in args.components.split(',')]
        result = enrich_package(args.module, args.package, args.description, args.project_dir, components)
        print(f'status\t{result["status"]}')
        print(f'module\t{result["module"]}')
        print(f'package\t{result["package"]}')
        print(f'action\t{result["action"]}')
        if 'components' in result:
            print_toon_list('components', result['components'])
        return 0
    except ModuleNotFoundError:
        return _handle_module_not_found(args.module, args.project_dir)
    except DataNotFoundError:
        print('error: Enrichment data not found')
        print(f'expected_file: {get_enriched_path(args.project_dir)}')
        print("resolution: Run 'architecture.py init' first")
        return 1
    except Exception as e:
        print('status\terror', file=sys.stderr)
        print(f'error\t{e}', file=sys.stderr)
        return 1


def _print_skills_by_profile(skills_by_profile: dict) -> None:
    """Print skills_by_profile in TOON format, handling both flat and structured formats.

    Args:
        skills_by_profile: Dict mapping profile names to skill lists or structured dicts
    """
    print('skills_by_profile:')
    for profile, profile_data in skills_by_profile.items():
        print(f'  {profile}:')
        if isinstance(profile_data, list):
            # Legacy flat format
            for skill in profile_data:
                print(f'    - {skill}')
        elif isinstance(profile_data, dict):
            # New structured format with defaults/optionals
            defaults = profile_data.get('defaults', [])
            optionals = profile_data.get('optionals', [])
            if defaults:
                print(f'    defaults[{len(defaults)}]{{skill,description}}:')
                for entry in defaults:
                    if isinstance(entry, dict):
                        skill = entry.get('skill', '')
                        desc = entry.get('description', '')
                        print(f'      - {skill},"{desc}"')
                    else:
                        print(f'      - {entry}')
            if optionals:
                print(f'    optionals[{len(optionals)}]{{skill,description}}:')
                for entry in optionals:
                    if isinstance(entry, dict):
                        skill = entry.get('skill', '')
                        desc = entry.get('description', '')
                        print(f'      - {skill},"{desc}"')
                    else:
                        print(f'      - {entry}')


def cmd_enrich_skills_by_profile(args) -> int:
    """CLI handler for enrich skills-by-profile command."""
    import json

    try:
        # Parse JSON input
        skills_by_profile = json.loads(args.skills_json)
        reasoning = getattr(args, 'reasoning', None)
        result = enrich_skills_by_profile(args.module, skills_by_profile, args.project_dir, reasoning)
        print(f'status\t{result["status"]}')
        print(f'module\t{result["module"]}')
        # Output skills_by_profile (handles both flat and structured formats)
        _print_skills_by_profile(result['skills_by_profile'])
        if result.get('warnings'):
            print()
            print_toon_list('warnings', result['warnings'])
        return 0
    except json.JSONDecodeError as e:
        print('status\terror', file=sys.stderr)
        print(f'error\tInvalid JSON: {e}', file=sys.stderr)
        return 1
    except ModuleNotFoundError:
        return _handle_module_not_found(args.module, args.project_dir)
    except DataNotFoundError:
        print('error: Enrichment data not found')
        print(f'expected_file: {get_enriched_path(args.project_dir)}')
        print("resolution: Run 'architecture.py init' first")
        return 1
    except Exception as e:
        print('status\terror', file=sys.stderr)
        print(f'error\t{e}', file=sys.stderr)
        return 1


def cmd_enrich_dependencies(args) -> int:
    """CLI handler for enrich dependencies command."""
    try:
        key_deps = None
        internal_deps = None
        if args.key:
            key_deps = [d.strip() for d in args.key.split(',')]
        if args.internal:
            internal_deps = [d.strip() for d in args.internal.split(',')]
        reasoning = getattr(args, 'reasoning', None)

        result = enrich_dependencies(args.module, key_deps, internal_deps, args.project_dir, reasoning)
        print(f'status\t{result["status"]}')
        print(f'module\t{result["module"]}')
        if 'key_dependencies' in result:
            print_toon_list('key_dependencies', result['key_dependencies'])
        if 'internal_dependencies' in result:
            print_toon_list('internal_dependencies', result['internal_dependencies'])
        return 0
    except ModuleNotFoundError:
        return _handle_module_not_found(args.module, args.project_dir)
    except DataNotFoundError:
        print('error: Enrichment data not found')
        print(f'expected_file: {get_enriched_path(args.project_dir)}')
        print("resolution: Run 'architecture.py init' first")
        return 1
    except Exception as e:
        print('status\terror', file=sys.stderr)
        print(f'error\t{e}', file=sys.stderr)
        return 1


def cmd_enrich_tip(args) -> int:
    """CLI handler for enrich tip command."""
    try:
        result = enrich_tip(args.module, args.tip, args.project_dir)
        print(f'status\t{result["status"]}')
        print(f'module\t{result["module"]}')
        print_toon_list('tips', result['tips'])
        return 0
    except ModuleNotFoundError:
        return _handle_module_not_found(args.module, args.project_dir)
    except DataNotFoundError:
        print('error: Enrichment data not found')
        print(f'expected_file: {get_enriched_path(args.project_dir)}')
        print("resolution: Run 'architecture.py init' first")
        return 1
    except Exception as e:
        print('status\terror', file=sys.stderr)
        print(f'error\t{e}', file=sys.stderr)
        return 1


def cmd_enrich_insight(args) -> int:
    """CLI handler for enrich insight command."""
    try:
        result = enrich_insight(args.module, args.insight, args.project_dir)
        print(f'status\t{result["status"]}')
        print(f'module\t{result["module"]}')
        print_toon_list('insights', result['insights'])
        return 0
    except ModuleNotFoundError:
        return _handle_module_not_found(args.module, args.project_dir)
    except DataNotFoundError:
        print('error: Enrichment data not found')
        print(f'expected_file: {get_enriched_path(args.project_dir)}')
        print("resolution: Run 'architecture.py init' first")
        return 1
    except Exception as e:
        print('status\terror', file=sys.stderr)
        print(f'error\t{e}', file=sys.stderr)
        return 1


def cmd_enrich_best_practice(args) -> int:
    """CLI handler for enrich best-practice command."""
    try:
        result = enrich_best_practice(args.module, args.practice, args.project_dir)
        print(f'status\t{result["status"]}')
        print(f'module\t{result["module"]}')
        print_toon_list('best_practices', result['best_practices'])
        return 0
    except ModuleNotFoundError:
        return _handle_module_not_found(args.module, args.project_dir)
    except DataNotFoundError:
        print('error: Enrichment data not found')
        print(f'expected_file: {get_enriched_path(args.project_dir)}')
        print("resolution: Run 'architecture.py init' first")
        return 1
    except Exception as e:
        print('status\terror', file=sys.stderr)
        print(f'error\t{e}', file=sys.stderr)
        return 1
