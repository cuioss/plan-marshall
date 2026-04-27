#!/usr/bin/env python3
"""
Extension discovery library.

Single source of truth for discovering and loading extension.py files
from domain bundles. Used by project-structure and manage-config.

Extension discovery library with CLI for configuration operations.
"""

import importlib.util
import os
import sys
from pathlib import Path
from typing import Any

# Direct import - executor sets up PYTHONPATH for cross-skill imports
from marketplace_bundles import resolve_bundles_root  # type: ignore[import-not-found]
from plan_logging import log_entry
from toon_parser import serialize_toon  # type: ignore[import-not-found]


def get_plugin_cache_path() -> Path:
    """Get the plugin cache path from environment or default."""
    env_path = os.environ.get('PLUGIN_CACHE_PATH')
    if env_path:
        return Path(env_path)
    return Path.home() / '.claude' / 'plugins' / 'cache' / 'plan-marshall'


def get_marketplace_bundles_path() -> Path:
    """Get the path to marketplace bundles directory.

    Resolves via ``resolve_bundles_root`` (walks parents looking for a
    plan-marshall bundle ancestor). If no source-tree ancestor exists
    (e.g. running outside the marketplace checkout), falls back to the
    plugin cache.

    Returns:
        Path to bundles directory
    """
    try:
        return resolve_bundles_root(Path(__file__))
    except RuntimeError:
        cache_path = get_plugin_cache_path()
        if cache_path.is_dir():
            return cache_path
        raise


def get_extension_api_scripts_path() -> Path:
    """Get path to extension scripts directory (where extension_base.py lives).

    This helper assumes the script is located three levels deep within a skill
    directory (e.g., skills/extension-api/scripts/) to resolve the shared path.
    Extension base classes live in script-shared/scripts/extension/ while this
    discovery script lives in extension-api/scripts/.
    """
    return Path(__file__).resolve().parent.parent.parent / 'script-shared' / 'scripts' / 'extension'


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
            log_entry('script', 'global', 'WARNING', f'[EXTENSION] Failed to create spec for {bundle_name}')
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Get the Extension class and instantiate it
        if hasattr(module, 'Extension'):
            return module.Extension()

        log_entry('script', 'global', 'WARNING', f'[EXTENSION] No Extension class found in {bundle_name}')
        return None
    except Exception as e:
        log_entry('script', 'global', 'WARNING', f'[EXTENSION] Failed to load extension from {bundle_name}: {e}')
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
    """Discover all extension.py files in bundles — returns every extension regardless
    of whether it applies to the current project.

    Use this for configuration operations (skill domains, workflow extensions)
    where all extensions need to be queried. For project-specific discovery
    that filters by applicability, use discover_applicable_extensions() instead.

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


def discover_applicable_extensions(project_root: Path) -> list[dict[str, Any]]:
    """Discover extensions that apply to a specific project — filters by
    whether discover_modules() finds modules in the given project root.

    Use this for project-specific operations (module discovery, architecture).
    For querying all extensions regardless of applicability, use
    discover_all_extensions() instead.

    Args:
        project_root: Path to the project root

    Returns:
        List of dicts with extension info: {bundle, path, module, discovered_modules}
    """
    all_extensions = discover_all_extensions()
    applicable: list[dict[str, Any]] = []

    for ext in all_extensions:
        module = ext.get('module')
        if module:
            try:
                discovered = module.discover_modules(project_root)
                if discovered:  # Only include if modules were found
                    ext['discovered_modules'] = discovered
                    applicable.append(ext)
            except Exception as e:
                log_entry(
                    'script',
                    'global',
                    'WARNING',
                    f'[EXTENSION] discover_modules() failed for {ext.get("bundle", "unknown")}: {e}',
                )

    return applicable


def get_skill_domains_from_extensions(extensions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Get skill domains from extensions.

    Each extension's get_skill_domains() returns a list of domain dicts,
    supporting both single-domain and multi-domain extensions.

    Args:
        extensions: List of extension info dicts

    Returns:
        List of domain info dicts: {domain, profiles, bundle}
    """
    domains: list[dict[str, Any]] = []

    for ext in extensions:
        module = ext.get('module')
        if not module:
            continue

        try:
            all_domains = module.get_skill_domains()
            for domain_info in all_domains:
                if domain_info and domain_info.get('domain'):
                    # Copy to avoid mutating the extension's data
                    entry = dict(domain_info)
                    entry['bundle'] = ext['bundle']
                    domains.append(entry)
        except Exception as e:
            log_entry('script', 'global', 'WARNING', f'[EXTENSION] get_skill_domains() failed for {ext["bundle"]}: {e}')

    return domains


def get_workflow_extensions_from_extensions(extensions: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Get workflow extensions (triage, outline_skill) from extensions.

    Args:
        extensions: List of extension info dicts

    Returns:
        Dict mapping bundle to {triage: skill_ref, outline_skill: skill_ref}
    """
    workflow_extensions: dict[str, dict[str, Any]] = {}

    for ext in extensions:
        module = ext.get('module')
        if not module:
            continue

        ext_info: dict[str, Any] = {}

        try:
            triage = module.provides_triage()
            if triage:
                ext_info['triage'] = triage
        except Exception:
            pass

        try:
            outline_skill = module.provides_outline_skill()
            if outline_skill:
                ext_info['outline_skill'] = outline_skill
        except Exception:
            pass

        try:
            verify_steps = module.provides_verify_steps()
            if verify_steps:
                ext_info['verify_steps'] = verify_steps
        except Exception:
            pass

        if ext_info:
            workflow_extensions[ext['bundle']] = ext_info

    return workflow_extensions


def apply_config_defaults(project_root: Path, pre_discovered: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Apply config_defaults() callback for applicable extensions only.

    Called during initialization to let extensions set project-specific
    defaults in marshal.json. Only extensions whose discover_modules()
    finds modules in the project are called, preventing non-applicable extensions
    from writing config (e.g., Maven settings in non-Java projects).

    Args:
        project_root: Path to the project root
        pre_discovered: Optional list of already-discovered extensions
            (from discover_applicable_extensions()). Avoids expensive double discovery.

    Returns:
        Dict with results: {
            "extensions_called": int,
            "extensions_skipped": int,
            "errors": list[str]
        }
    """
    if pre_discovered is not None:
        # Use pre-discovered extensions (already filtered by applicability)
        extensions = pre_discovered
    else:
        extensions = discover_all_extensions()

    results: dict[str, Any] = {'extensions_called': 0, 'extensions_skipped': 0, 'errors': []}

    for ext in extensions:
        module = ext.get('module')
        bundle = ext.get('bundle', 'unknown')

        if not module:
            results['extensions_skipped'] += 1
            continue

        # When using pre-discovered extensions, skip applicability check
        # (they were already filtered). Otherwise, check discover_modules.
        if pre_discovered is None and hasattr(module, 'discover_modules'):
            try:
                discovered = module.discover_modules(project_root)
                if not discovered:
                    results['extensions_skipped'] += 1
                    continue
            except Exception:
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
    """Discover all modules and split multi-technology paths into virtual modules.

    Delegates to _module_aggregation.discover_project_modules() which:
    - Calls discover_modules() on each applicable extension
    - Splits directories with multiple build systems into virtual modules
      (e.g., a dir with both pom.xml and package.json becomes two modules)
    - Returns a deduplicated, sorted module dict

    Args:
        project_root: Path to project root

    Returns:
        Dict with 'modules' (name -> module dict) and 'extensions_used' (list of bundle names).
    """
    from _module_aggregation import discover_project_modules as _discover_project_modules

    return _discover_project_modules(project_root, discover_applicable_extensions)


# =============================================================================
# CLI Interface
# =============================================================================


def cmd_apply_config_defaults(args) -> int:
    """CLI handler for apply-config-defaults command."""
    project_root = Path(args.project_dir).resolve()

    if not project_root.exists():
        log_entry('script', 'global', 'ERROR', f'[EXTENSION] Project directory not found: {project_root}')
        print(serialize_toon({'status': 'error', 'error': f'Project directory not found: {project_root}'}))
        return 0

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

    parser = argparse.ArgumentParser(
        description='Extension discovery and configuration operations', allow_abbrev=False
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    # apply-config-defaults subcommand
    defaults_parser = subparsers.add_parser(
        'apply-config-defaults',
        help='Apply config_defaults() callback for all extensions',
        allow_abbrev=False,
    )
    defaults_parser.add_argument('--project-dir', default='.', help='Project directory (default: current directory)')
    defaults_parser.set_defaults(func=cmd_apply_config_defaults)

    args = parser.parse_args()
    result: int = args.func(args)
    return result


if __name__ == '__main__':
    sys.exit(main())
