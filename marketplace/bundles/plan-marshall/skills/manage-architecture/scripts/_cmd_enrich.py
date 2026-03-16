#!/usr/bin/env python3
"""Enrich command handlers for architecture script.

Handles: enrich project, module, package, skills, dependencies, tip, insight, best-practice
These commands write to llm-enriched.json.
"""

import sys
from pathlib import Path
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


def _extract_skill_names_from_profile(profile_data: dict) -> list[str]:
    """Extract skill names from a profile's structured format.

    Args:
        profile_data: Dict with defaults/optionals sections

    Returns:
        List of skill names
    """
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

    Expected format:
    {"profile": {"defaults": [{"skill": "...", "description": "..."}], "optionals": [...]}}

    Args:
        skills_by_profile: Dict mapping profile names to structured skill dicts

    Returns:
        List of warning messages (empty if valid)
    """
    warnings: list[str] = []

    for profile_name, profile_data in skills_by_profile.items():
        if not isinstance(profile_data, dict):
            warnings.append(f"Profile '{profile_name}' must be a dict, got {type(profile_data).__name__}")
            continue
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
                    if ':' not in entry:
                        warnings.append(
                            f"Skill '{entry}' in '{profile_name}.{section}' missing bundle:skill notation"
                        )
                else:
                    warnings.append(f"Entry {i} in '{profile_name}.{section}' must be a dict or string")

    return warnings


def _resolve_active_profiles(
    domain_key: str, project_dir: str, explicit: set[str] | None = None
) -> set[str] | None:
    """Resolve active profiles from CLI flag or marshal.json config.

    Resolution order:
    1. explicit (--profiles CLI flag) wins
    2. marshal.json skill_domains.{domain}.active_profiles (per-domain)
    3. marshal.json skill_domains.active_profiles (global default)
    4. None (fall through to signal detection in extension)
    """
    if explicit is not None:
        return explicit

    import json

    marshal_path = Path(project_dir) / '.plan' / 'marshal.json'
    if not marshal_path.exists():
        return None

    try:
        config = json.loads(marshal_path.read_text(encoding='utf-8'))
    except Exception:
        return None

    sd = config.get('skill_domains', {})

    # Per-domain override
    domain_cfg = sd.get(domain_key, {})
    if isinstance(domain_cfg, dict) and 'active_profiles' in domain_cfg:
        return set(domain_cfg['active_profiles'])

    # Global default
    if 'active_profiles' in sd:
        return set(sd['active_profiles'])

    return None


def enrich_add_domain(
    module_name: str,
    domain_key: str,
    project_dir: str = '.',
    include_optionals: bool = False,
    reasoning: str | None = None,
    profiles: set[str] | None = None,
) -> dict:
    """Add a domain's skills to a module's skills_by_profile additively.

    Loads the domain's extension, calls applies_to_module() to get resolved
    skills, then merges them into the module's existing skills_by_profile.

    Args:
        module_name: Module name
        domain_key: Domain key (e.g., 'java', 'general-dev')
        project_dir: Project directory path
        include_optionals: Whether to include optional skills
        reasoning: Rationale for adding this domain
        profiles: Explicit profile set (overrides config and detection)

    Returns:
        Dict with status, module, domain, profiles_updated, and skills_by_profile

    Raises:
        ModuleNotFoundError: If module not found
        DataNotFoundError: If data files not found
        ValueError: If domain is 'system' or not found
    """
    if domain_key == 'system':
        raise ValueError("Cannot add 'system' domain to modules")

    # Validate module exists
    derived = load_derived_data(project_dir)
    from _architecture_core import get_module, get_module_names

    modules = get_module_names(derived)
    if module_name not in modules:
        raise ModuleNotFoundError(f'Module not found: {module_name}', modules)

    module_data = get_module(derived, module_name)

    # Find extension for this domain (supports multi-domain extensions)
    from extension_discovery import discover_all_extensions  # type: ignore[import-not-found]

    extensions = discover_all_extensions()
    target_ext = None
    for ext_info in extensions:
        ext_module = ext_info.get('module')
        if not ext_module:
            continue
        try:
            # Check all domains from this extension
            all_domains = ext_module.get_skill_domains()
            for sd in all_domains:
                if sd.get('domain', {}).get('key') == domain_key:
                    target_ext = ext_module
                    break
            if target_ext:
                break
        except Exception:
            continue

    if target_ext is None:
        raise ValueError(f"Domain not found: {domain_key}")

    # Resolve active profiles (three-layer: CLI > config > signal detection)
    active = _resolve_active_profiles(domain_key, project_dir, profiles)

    # Get resolved skills from extension
    result = target_ext.applies_to_module(module_data, active_profiles=active)
    skills_by_profile = result.get('skills_by_profile', {})

    # Load current enriched data
    enriched = load_llm_enriched(project_dir)
    if 'modules' not in enriched:
        enriched['modules'] = {}
    if module_name not in enriched['modules']:
        enriched['modules'][module_name] = {}
    if 'skills_by_profile' not in enriched['modules'][module_name]:
        enriched['modules'][module_name]['skills_by_profile'] = {}

    current = enriched['modules'][module_name]['skills_by_profile']
    profiles_updated = []

    for profile_name, profile_data in skills_by_profile.items():
        new_skills: list[str] = []
        for entry in profile_data.get('defaults', []):
            skill_name = entry.get('skill', entry) if isinstance(entry, dict) else entry
            new_skills.append(skill_name)

        if include_optionals:
            for entry in profile_data.get('optionals', []):
                skill_name = entry.get('skill', entry) if isinstance(entry, dict) else entry
                new_skills.append(skill_name)

        if not new_skills:
            continue

        # Get existing skills for this profile
        existing = current.get(profile_name, {})
        existing_names = set(_extract_skill_names_from_profile(existing) if existing else [])

        # Merge into structured format: add new skills to defaults
        if not isinstance(existing, dict):
            existing = {'defaults': [], 'optionals': []}
        merged = dict(existing)
        if 'defaults' not in merged:
            merged['defaults'] = []
        for skill in new_skills:
            if skill not in existing_names:
                merged['defaults'].append(skill)
                existing_names.add(skill)

        current[profile_name] = merged
        profiles_updated.append(profile_name)

    enriched['modules'][module_name]['skills_by_profile'] = current

    # Append reasoning
    if reasoning:
        existing_reasoning = enriched['modules'][module_name].get('skills_by_profile_reasoning', '')
        if existing_reasoning:
            enriched['modules'][module_name]['skills_by_profile_reasoning'] = f'{existing_reasoning}; {reasoning}'
        else:
            enriched['modules'][module_name]['skills_by_profile_reasoning'] = reasoning

    save_llm_enriched(enriched, project_dir)

    return {
        'status': 'success',
        'module': module_name,
        'domain': domain_key,
        'profiles_updated': profiles_updated,
        'skills_by_profile': current,
    }


def enrich_skills_by_profile(
    module_name: str, skills_by_profile: dict, project_dir: str = '.', reasoning: str | None = None
) -> dict:
    """Update skills organized by profile.

    Format: {"profile": {"defaults": [{"skill": "...", "description": "..."}], "optionals": [...]}}

    Args:
        module_name: Module name
        skills_by_profile: Dict mapping profile names to structured dicts
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
    """Print skills_by_profile in TOON format.

    Args:
        skills_by_profile: Dict mapping profile names to structured skill dicts
    """
    print('skills_by_profile:')
    for profile, profile_data in skills_by_profile.items():
        print(f'  {profile}:')
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
        # Output skills_by_profile
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


def cmd_enrich_add_domain(args) -> int:
    """CLI handler for enrich add-domain command."""
    try:
        include_optionals = getattr(args, 'include_optionals', False)
        reasoning = getattr(args, 'reasoning', None)
        profiles_str = getattr(args, 'profiles', None)
        profiles = set(profiles_str.split(',')) if profiles_str else None
        result = enrich_add_domain(
            args.module, args.domain, args.project_dir, include_optionals, reasoning,
            profiles=profiles,
        )
        print(f'status\t{result["status"]}')
        print(f'module\t{result["module"]}')
        print(f'domain\t{result["domain"]}')
        print_toon_list('profiles_updated', result['profiles_updated'])
        _print_skills_by_profile(result['skills_by_profile'])
        return 0
    except ModuleNotFoundError:
        return _handle_module_not_found(args.module, args.project_dir)
    except (DataNotFoundError, ValueError) as e:
        print(f'error\t{e}')
        return 1
    except Exception as e:
        print('status\terror', file=sys.stderr)
        print(f'error\t{e}', file=sys.stderr)
        return 1
