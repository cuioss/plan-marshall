#!/usr/bin/env python3
"""Suggest command handler for architecture script.

Handles: suggest-domains
Thin orchestrator that delegates domain applicability to extension.py implementations.

Persistence model: per-module on-disk layout under
``.plan/project-architecture/``. Loads the module's ``derived.json`` lazily
from ``_project.json``'s index — no monolithic file is ever read.
"""

from typing import Any

from _architecture_core import (
    DataNotFoundError,
    ModuleNotFoundInProjectError,
    handle_module_not_found_result,
    iter_modules,
    load_module_derived,
    require_project_meta_result,
)

# =============================================================================
# API Functions
# =============================================================================


def suggest_domains(module_name: str, project_dir: str = '.') -> dict[str, Any]:
    """Suggest applicable skill domains for a module.

    Loads all extensions, calls applies_to_module() on each, and returns
    applicable domains with confidence and signals.

    Args:
        module_name: Module name from ``_project.json``
        project_dir: Project directory path

    Returns:
        Dict with status, module, and list of applicable domains

    Raises:
        ModuleNotFoundInProjectError: If module not in ``_project.json``
        DataNotFoundError: If ``_project.json`` itself is missing
    """
    available = iter_modules(project_dir)
    if module_name not in available:
        raise ModuleNotFoundInProjectError(f'Module not found: {module_name}', available)

    module_data = load_module_derived(module_name, project_dir)

    # Discover all extensions
    from extension_discovery import discover_all_extensions  # type: ignore[import-not-found]

    extensions = discover_all_extensions()

    domains: list[dict[str, Any]] = []
    applicable_keys: set[str] = set()

    # First pass: collect all applicable domains
    for ext_info in extensions:
        ext_module = ext_info.get('module')
        if not ext_module:
            continue

        # Get all domain keys from extension (supports multi-domain)
        try:
            all_skill_domains = ext_module.get_skill_domains()
        except Exception as e:
            from plan_logging import log_entry  # type: ignore[import-not-found]

            log_entry('script', 'global', 'WARNING', f'[SUGGEST] get_skill_domains() failed for extension: {e}')
            continue

        domain_keys = [
            sd.get('domain', {}).get('key', '')
            for sd in all_skill_domains
            if sd.get('domain', {}).get('key', '') != 'system'
        ]

        if not domain_keys:
            continue

        # Call applies_to_module once per extension
        try:
            result = ext_module.applies_to_module(module_data)
        except Exception as e:
            from plan_logging import log_entry  # type: ignore[import-not-found]

            log_entry('script', 'global', 'WARNING', f'[SUGGEST] applies_to_module() failed for extension: {e}')
            continue

        if result.get('applicable'):
            for dk in domain_keys:
                applicable_keys.add(dk)
            skill_count = sum(
                len(p.get('defaults', [])) + len(p.get('optionals', []))
                for p in result.get('skills_by_profile', {}).values()
            )
            # Report each non-empty domain separately
            for dk in domain_keys:
                # Find the domain's profiles
                dk_profiles = {}
                for sd in all_skill_domains:
                    if sd.get('domain', {}).get('key') == dk:
                        dk_profiles = sd.get('profiles', {})
                        break
                # Skip domains with no profiles (e.g., build domain)
                if not dk_profiles and len(domain_keys) > 1:
                    continue
                domains.append(
                    {
                        'domain': dk,
                        'confidence': result.get('confidence', 'unknown'),
                        'signals': result.get('signals', []),
                        'additive_to': result.get('additive_to'),
                        'skill_count': skill_count,
                        'skills_by_profile': result.get('skills_by_profile', {}),
                    }
                )

    # Second pass: filter additive domains whose parent is not applicable
    filtered_domains = []
    for d in domains:
        parent = d.get('additive_to')
        if parent and parent not in applicable_keys:
            continue
        filtered_domains.append(d)

    return {
        'status': 'success',
        'module': module_name,
        'domains': filtered_domains,
    }


# =============================================================================
# CLI Handler
# =============================================================================


def cmd_suggest_domains(args) -> dict:
    """CLI handler for suggest-domains command."""
    try:
        return suggest_domains(args.module, args.project_dir)
    except ModuleNotFoundInProjectError:
        return handle_module_not_found_result(args.module, args.project_dir)
    except DataNotFoundError:
        return require_project_meta_result(args.project_dir)
    except Exception as e:
        return {'status': 'error', 'error': str(e)}
