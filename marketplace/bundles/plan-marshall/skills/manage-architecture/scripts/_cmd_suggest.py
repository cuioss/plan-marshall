#!/usr/bin/env python3
"""Suggest command handler for architecture script.

Handles: suggest-domains
Thin orchestrator that delegates domain applicability to extension.py implementations.
"""

import sys  # noqa: I001
from typing import Any

from _architecture_core import (
    DataNotFoundError,
    ModuleNotFoundError,
    get_module,
    load_derived_data,
    print_toon_list,
    print_toon_table,
)


# =============================================================================
# API Functions
# =============================================================================


def suggest_domains(module_name: str, project_dir: str = '.') -> dict[str, Any]:
    """Suggest applicable skill domains for a module.

    Loads all extensions, calls applies_to_module() on each, and returns
    applicable domains with confidence and signals.

    Args:
        module_name: Module name from derived-data.json
        project_dir: Project directory path

    Returns:
        Dict with status, module, and list of applicable domains:
        {
            'status': 'success',
            'module': str,
            'domains': [
                {
                    'domain': str,
                    'confidence': str,
                    'signals': list[str],
                    'additive_to': str | None,
                    'skill_count': int,
                }
            ]
        }

    Raises:
        ModuleNotFoundError: If module not found
        DataNotFoundError: If derived-data.json not found
    """
    derived = load_derived_data(project_dir)
    module_data = get_module(derived, module_name)

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

        # Get domain key to skip 'system'
        try:
            skill_domains = ext_module.get_skill_domains()
            domain_key = skill_domains.get('domain', {}).get('key', '')
        except Exception:
            continue

        if domain_key == 'system':
            continue

        # Call applies_to_module
        try:
            result = ext_module.applies_to_module(module_data)
        except Exception:
            continue

        if result.get('applicable'):
            applicable_keys.add(domain_key)
            skill_count = sum(
                len(p.get('defaults', [])) + len(p.get('optionals', []))
                for p in result.get('skills_by_profile', {}).values()
            )
            domains.append({
                'domain': domain_key,
                'confidence': result.get('confidence', 'unknown'),
                'signals': result.get('signals', []),
                'additive_to': result.get('additive_to'),
                'skill_count': skill_count,
                'skills_by_profile': result.get('skills_by_profile', {}),
            })

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


def cmd_suggest_domains(args) -> int:
    """CLI handler for suggest-domains command."""
    try:
        result = suggest_domains(args.module, args.project_dir)
        print(f'status\t{result["status"]}')
        print(f'module\t{result["module"]}')

        domains = result['domains']
        items = []
        for d in domains:
            items.append({
                'domain': d['domain'],
                'confidence': d['confidence'],
                'signals': ','.join(d.get('signals', [])),
                'additive_to': d.get('additive_to') or '',
                'skill_count': str(d.get('skill_count', 0)),
            })

        print_toon_table('domains', items, ['domain', 'confidence', 'signals', 'additive_to', 'skill_count'])
        return 0
    except ModuleNotFoundError:
        from _architecture_core import get_module_names

        try:
            derived = load_derived_data(args.project_dir)
            modules = get_module_names(derived)
        except Exception:
            modules = []
        print('error: Module not found')
        print(f'module: {args.module}')
        print_toon_list('available', modules)
        return 1
    except DataNotFoundError:
        from _architecture_core import get_derived_path

        print('error: Derived data not found')
        print(f'expected_file: {get_derived_path(args.project_dir)}')
        print("resolution: Run 'architecture.py discover' first")
        return 1
    except Exception as e:
        print('status\terror', file=sys.stderr)
        print(f'error\t{e}', file=sys.stderr)
        return 1
