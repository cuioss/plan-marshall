#!/usr/bin/env python3
"""
Extension discovery library.

Single source of truth for discovering and loading extension.py files
from domain bundles. Used by project-structure and plan-marshall-config.

This module is a library - it has no CLI. Persistence goes through
project-structure, and reading goes through plan-marshall-config.
"""

import importlib.util
import os
import sys
from pathlib import Path
from typing import Any

# Direct import - executor sets up PYTHONPATH for cross-skill imports
from plan_logging import log_entry


def get_plugin_cache_path() -> Path:
    """Get the plugin cache path from environment or default."""
    env_path = os.environ.get('PLUGIN_CACHE_PATH')
    if env_path:
        return Path(env_path)
    return Path.home() / '.claude' / 'plugins' / 'cache' / 'plan-marshall'


def get_marketplace_bundles_path() -> Path:
    """Get the path to marketplace bundles directory.

    Searches for marketplace bundles in:
    1. Source: marketplace/bundles relative to script (development)
    2. Cache: ~/.claude/plugins/cache/plan-marshall (installed)

    Returns:
        Path to bundles directory
    """
    script_path = Path(__file__).resolve()

    # Walk up from script location to find bundles directory
    current = script_path.parent
    for _ in range(10):  # Safety limit
        candidate = current / 'bundles'
        if candidate.is_dir() and (candidate / 'plan-marshall').is_dir():
            return candidate
        if current.name == 'bundles' and (current / 'plan-marshall').is_dir():
            return current
        current = current.parent
        if current == current.parent:
            break

    # Fallback: check plugin cache
    cache_path = get_plugin_cache_path()
    if cache_path.is_dir():
        return cache_path

    return script_path.parent.parent.parent.parent.parent / 'bundles'


def get_extension_api_scripts_path() -> Path:
    """Get path to extension-api scripts directory."""
    return Path(__file__).parent


def load_extension_module(extension_path: Path, bundle_name: str):
    """Load an extension.py module and instantiate the Extension class.

    Args:
        extension_path: Path to extension.py file
        bundle_name: Name of the bundle for module naming

    Returns:
        Extension instance or None if failed
    """
    try:
        spec = importlib.util.spec_from_file_location(f'extension_{bundle_name}', extension_path)
        if spec is None or spec.loader is None:
            log_entry('script', 'global', 'WARN', f'[EXTENSION] Failed to create spec for {bundle_name}')
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Get the Extension class and instantiate it
        if hasattr(module, 'Extension'):
            return module.Extension()

        log_entry('script', 'global', 'WARN', f'[EXTENSION] No Extension class found in {bundle_name}')
        return None
    except Exception as e:
        log_entry('script', 'global', 'WARN', f'[EXTENSION] Failed to load extension from {bundle_name}: {e}')
        return None


def find_extension_path(bundle_dir: Path) -> Path | None:
    """Find extension.py path in a bundle directory.

    Handles both source and cache structures:
    - Source: bundles/{bundle}/skills/plan-marshall-plugin/extension.py
    - Cache: {cache}/{bundle}/skills/plan-marshall-plugin/extension.py
    - Cache versioned: {cache}/{bundle}/1.0.0/skills/plan-marshall-plugin/extension.py

    Args:
        bundle_dir: Path to the bundle directory

    Returns:
        Path to extension.py or None if not found
    """
    # Try direct path first (source structure)
    extension_path = bundle_dir / 'skills' / 'plan-marshall-plugin' / 'extension.py'
    if extension_path.exists():
        return extension_path

    # Try versioned path (cache structure from rsync)
    for version_dir in bundle_dir.iterdir():
        if version_dir.is_dir() and not version_dir.name.startswith('.'):
            versioned_path = version_dir / 'skills' / 'plan-marshall-plugin' / 'extension.py'
            if versioned_path.exists():
                return versioned_path

    return None


def discover_all_extensions() -> list[dict[str, Any]]:
    """Discover all extension.py files in bundles (no applicability check).

    Scans all bundles for extension.py files in skills/plan-marshall-plugin/

    Returns:
        List of dicts with extension info: {bundle, path, module}
    """
    extensions: list[dict[str, Any]] = []
    bundles_path = get_marketplace_bundles_path()

    if not bundles_path.is_dir():
        return extensions

    for bundle_dir in bundles_path.iterdir():
        if not bundle_dir.is_dir() or bundle_dir.name.startswith('.'):
            continue

        extension_path = find_extension_path(bundle_dir)
        if not extension_path:
            continue

        module = load_extension_module(extension_path, bundle_dir.name)
        if module:
            extensions.append({'bundle': bundle_dir.name, 'path': str(extension_path), 'module': module})

    return extensions


def discover_extensions(project_root: Path) -> list[dict[str, Any]]:
    """Discover applicable extensions for a project.

    Scans all bundles for extension.py files. Extensions are included if
    they have a discover_modules() method that can find modules in the project.

    Args:
        project_root: Path to the project root

    Returns:
        List of dicts with extension info: {bundle, path, module}
    """
    all_extensions = discover_all_extensions()
    applicable: list[dict[str, Any]] = []

    for ext in all_extensions:
        module = ext.get('module')
        if module and hasattr(module, 'discover_modules'):
            # Actually call discover_modules to check applicability
            try:
                discovered = module.discover_modules(project_root)
                if discovered:  # Only include if modules were found
                    applicable.append(ext)
            except Exception:
                # Skip extensions that fail during discovery
                pass

    return applicable


def get_build_systems_from_extensions(extensions: list[dict[str, Any]], project_root: Path | None = None) -> list[str]:
    """Get build systems provided by extensions.

    Args:
        extensions: List of extension info dicts from discover_extensions()
        project_root: Optional project root for dynamic detection.
                     If provided, uses get_applicable_build_systems().
                     If not, uses static provides_build_systems().

    Returns:
        List of build system names (e.g., ["maven", "gradle", "npm"])
    """
    build_systems = set()

    for ext in extensions:
        module = ext.get('module')
        if not module:
            continue

        try:
            # Prefer dynamic detection if project_root provided and function exists
            if project_root and hasattr(module, 'get_applicable_build_systems'):
                systems = module.get_applicable_build_systems(str(project_root))
            elif hasattr(module, 'provides_build_systems'):
                systems = module.provides_build_systems()
            else:
                continue

            build_systems.update(systems)
        except Exception as e:
            log_entry('script', 'global', 'WARN', f'[EXTENSION] Build system detection failed for {ext["bundle"]}: {e}')

    return list(build_systems)


def get_skill_domains_from_extensions(extensions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Get skill domains from extensions.

    Args:
        extensions: List of extension info dicts

    Returns:
        List of domain info dicts: {domain, profiles, bundle}
    """
    domains: list[dict[str, Any]] = []

    for ext in extensions:
        module = ext.get('module')
        if module and hasattr(module, 'get_skill_domains'):
            try:
                domain_info = module.get_skill_domains()
                if domain_info and domain_info.get('domain'):
                    domain_info['bundle'] = ext['bundle']
                    domains.append(domain_info)
            except Exception as e:
                log_entry(
                    'script', 'global', 'WARN', f'[EXTENSION] get_skill_domains() failed for {ext["bundle"]}: {e}'
                )

    return domains


def get_workflow_extensions_from_extensions(extensions: list[dict[str, Any]]) -> dict[str, dict[str, str]]:
    """Get workflow extensions (triage, outline) from extensions.

    Args:
        extensions: List of extension info dicts

    Returns:
        Dict mapping bundle to {triage: skill_ref, outline: skill_ref}
    """
    workflow_extensions: dict[str, dict[str, str]] = {}

    for ext in extensions:
        module = ext.get('module')
        if not module:
            continue

        ext_info: dict[str, str] = {}

        if hasattr(module, 'provides_triage'):
            try:
                triage = module.provides_triage()
                if triage:
                    ext_info['triage'] = triage
            except Exception:
                pass

        if hasattr(module, 'provides_outline'):
            try:
                outline = module.provides_outline()
                if outline:
                    ext_info['outline'] = outline
            except Exception:
                pass

        if ext_info:
            workflow_extensions[ext['bundle']] = ext_info

    return workflow_extensions


def apply_config_defaults(project_root: Path) -> dict[str, Any]:
    """Apply config_defaults() callback for all discovered extensions.

    Called during initialization to let extensions set project-specific
    defaults in run-configuration.json. Each extension's config_defaults()
    method is called with write-once semantics.

    Args:
        project_root: Path to the project root

    Returns:
        Dict with results: {
            "extensions_called": int,
            "extensions_skipped": int,
            "errors": list[str]
        }
    """
    extensions = discover_all_extensions()
    results: dict[str, Any] = {'extensions_called': 0, 'extensions_skipped': 0, 'errors': []}

    for ext in extensions:
        module = ext.get('module')
        bundle = ext.get('bundle', 'unknown')

        if not module:
            results['extensions_skipped'] += 1
            continue

        if hasattr(module, 'config_defaults'):
            try:
                module.config_defaults(str(project_root))
                results['extensions_called'] += 1
            except Exception as e:
                results['errors'].append(f'{bundle}: {e}')
        else:
            results['extensions_skipped'] += 1

    return results


# =============================================================================
# Module Discovery and Merging (thin wrapper)
# =============================================================================


def discover_project_modules(project_root: Path) -> dict[str, Any]:
    """Discover all modules and merge hybrid modules.

    Single entry point for module discovery. Handles:
    - Extension discovery (which bundles apply)
    - Module discovery per extension
    - Hybrid module merging (same path from multiple extensions)
    - Command merging (nest by build system for conflicts)

    Args:
        project_root: Path to project root

    Returns:
        {
            "modules": {
                "module-name": {
                    "name": "...",
                    "build_systems": ["maven", "npm"],  # list for hybrid
                    "paths": {...},
                    "metadata": {...},
                    "commands": {
                        "module-tests": {"maven": "...", "npm": "..."},
                        "lint": "..."  # string if only one provides it
                    },
                    ...
                }
            },
            "extensions_used": ["pm-dev-java", "pm-dev-frontend"]
        }
    """
    from _module_aggregation import discover_project_modules as _discover_project_modules

    return _discover_project_modules(project_root, discover_extensions)


# =============================================================================
# CLI Interface
# =============================================================================


def cmd_apply_config_defaults(args) -> int:
    """CLI handler for apply-config-defaults command."""
    project_root = Path(args.project_dir).resolve()

    if not project_root.exists():
        log_entry('script', 'global', 'ERROR', f'[EXTENSION] Project directory not found: {project_root}')
        print(f'error\tProject directory not found: {project_root}', file=sys.stderr)
        return 1

    results = apply_config_defaults(project_root)

    # Output in TOON format
    print('status\tsuccess')
    print(f'extensions_called\t{results["extensions_called"]}')
    print(f'extensions_skipped\t{results["extensions_skipped"]}')
    print(f'errors_count\t{len(results["errors"])}')

    if results['errors']:
        for error in results['errors']:
            print(f'error\t{error}')

    return 0 if not results['errors'] else 1


def main() -> int:
    """CLI entry point for extension discovery operations."""
    import argparse

    parser = argparse.ArgumentParser(description='Extension discovery and configuration operations')
    subparsers = parser.add_subparsers(dest='command', required=True)

    # apply-config-defaults subcommand
    defaults_parser = subparsers.add_parser(
        'apply-config-defaults', help='Apply config_defaults() callback for all extensions'
    )
    defaults_parser.add_argument('--project-dir', default='.', help='Project directory (default: current directory)')
    defaults_parser.set_defaults(func=cmd_apply_config_defaults)

    args = parser.parse_args()
    result: int = args.func(args)
    return result


if __name__ == '__main__':
    sys.exit(main())
