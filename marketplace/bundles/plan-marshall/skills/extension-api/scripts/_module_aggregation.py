#!/usr/bin/env python3
"""Module aggregation and hybrid module merging utilities.

Handles merging modules discovered by multiple extensions (e.g., Maven + npm)
into unified hybrid module structures with proper command nesting.

Usage:
    from module_aggregation import discover_project_modules

    result = discover_project_modules(Path("/path/to/project"))
    # result = {"modules": {...}, "extensions_used": [...]}
"""

import sys
from pathlib import Path

# Direct import - executor sets up PYTHONPATH for cross-skill imports
from plan_logging import log_entry


def _merge_commands(existing: dict, new: dict, existing_tech: str, new_tech: str) -> dict:
    """Merge commands from two modules, nesting by build system for conflicts.

    When both extensions provide the same command, nest by build system.
    When only one provides a command, keep as string.

    Args:
        existing: Commands dict from first module
        new: Commands dict from second module
        existing_tech: Technology name of first module (e.g., "maven")
        new_tech: Technology name of second module (e.g., "npm")

    Returns:
        Merged commands dict with nested structure for conflicts.

    Example:
        existing = {"module-tests": "mvn test", "coverage": "mvn jacoco"}
        new = {"module-tests": "npm test", "lint": "npm lint"}
        result = {
            "module-tests": {"maven": "mvn test", "npm": "npm test"},
            "coverage": "mvn jacoco",
            "lint": "npm lint"
        }
    """
    result = {}
    all_keys = set(existing.keys()) | set(new.keys())

    for key in all_keys:
        if key in existing and key in new:
            # Both provide same command - nest by build system
            result[key] = {
                existing_tech: existing[key],
                new_tech: new[key]
            }
        elif key in existing:
            result[key] = existing[key]
        else:
            result[key] = new[key]

    return result


def _get_technology(module: dict) -> str:
    """Extract primary build system from module dict.

    Args:
        module: Module dict from discover_modules()

    Returns:
        Primary build system name (e.g., "maven", "npm") or "unknown"
    """
    build_systems = module.get('build_systems', [])
    if build_systems:
        return build_systems[0]
    return 'unknown'


def _merge_hybrid_module(existing: dict, new: dict) -> dict:
    """Merge two module dicts for hybrid modules (e.g., Maven + npm).

    When the same module path is discovered by multiple extensions (Java and npm),
    this function merges the data into a single comprehensive module dict.

    Merge strategy:
    - name: Prefer existing (Maven artifactId typically more canonical)
    - build_systems: Combined from both technologies
    - paths: Merge sources/tests lists, combine descriptors
    - metadata: First non-null value wins (Maven typically more detailed)
    - packages: Combine dicts
    - dependencies: Combine lists
    - stats: Sum counts
    - commands: Nest by build system for conflicts (via _merge_commands)

    Args:
        existing: First module dict
        new: Second module dict

    Returns:
        Merged module dict with build_systems list and nested commands.
    """
    merged = existing.copy()

    # Determine technologies for command merging
    existing_tech = _get_technology(existing)
    new_tech = _get_technology(new)

    # Collect build systems from both modules
    existing_systems = set(existing.get('build_systems', []))
    new_systems = set(new.get('build_systems', []))

    merged['build_systems'] = sorted(existing_systems | new_systems)

    # Merge paths
    existing_paths = existing.get('paths', {})
    new_paths = new.get('paths', {})
    merged_paths = {
        'module': existing_paths.get('module') or new_paths.get('module'),
        'sources': list(set(existing_paths.get('sources', []) + new_paths.get('sources', []))),
        'tests': list(set(existing_paths.get('tests', []) + new_paths.get('tests', []))),
    }
    # Merge descriptors into list
    descriptors = []
    for p in [existing_paths, new_paths]:
        desc = p.get('descriptor')
        if desc and desc not in descriptors:
            descriptors.append(desc)
    if descriptors:
        merged_paths['descriptors'] = descriptors
    # Preserve readme from either
    readme = existing_paths.get('readme') or new_paths.get('readme')
    if readme:
        merged_paths['readme'] = readme
    merged['paths'] = merged_paths

    # Merge metadata (first non-null wins)
    existing_meta = existing.get('metadata', {})
    new_meta = new.get('metadata', {})
    merged_meta = {}
    for key in set(existing_meta.keys()) | set(new_meta.keys()):
        merged_meta[key] = existing_meta.get(key) or new_meta.get(key)
    if merged_meta:
        merged['metadata'] = merged_meta

    # Merge packages (combine dicts)
    existing_pkgs = existing.get('packages', {})
    new_pkgs = new.get('packages', {})
    if existing_pkgs or new_pkgs:
        merged['packages'] = {**existing_pkgs, **new_pkgs}

    # Merge dependencies (combine lists)
    existing_deps = existing.get('dependencies', [])
    new_deps = new.get('dependencies', [])
    if existing_deps or new_deps:
        merged['dependencies'] = existing_deps + new_deps

    # Merge stats (sum counts)
    existing_stats = existing.get('stats', {})
    new_stats = new.get('stats', {})
    merged['stats'] = {
        'source_files': existing_stats.get('source_files', 0) + new_stats.get('source_files', 0),
        'test_files': existing_stats.get('test_files', 0) + new_stats.get('test_files', 0),
    }

    # Merge commands (nest by build system for conflicts)
    existing_cmds = existing.get('commands', {})
    new_cmds = new.get('commands', {})
    if existing_cmds or new_cmds:
        merged['commands'] = _merge_commands(existing_cmds, new_cmds, existing_tech, new_tech)

    return merged


def discover_project_modules(project_root: Path, discover_extensions_fn) -> dict:
    """Discover all modules and merge hybrid modules.

    Single entry point for module discovery. Handles:
    - Extension discovery (which bundles apply)
    - Module discovery per extension
    - Hybrid module merging (same path from multiple extensions)
    - Command merging (nest by build system for conflicts)

    Args:
        project_root: Path to project root
        discover_extensions_fn: Function to discover applicable extensions.
            Should return list of dicts with 'module' and 'bundle' keys.

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
    if isinstance(project_root, str):
        project_root = Path(project_root)

    # Discover applicable extensions
    extensions = discover_extensions_fn(project_root)
    extensions_used = []

    # Collect modules from all extensions, keyed by path for merging
    modules_by_path = {}  # {path: module_dict}

    for ext in extensions:
        ext_module = ext.get("module")
        bundle_name = ext.get("bundle", "unknown")

        if not ext_module or not hasattr(ext_module, 'discover_modules'):
            continue

        try:
            ext_modules = ext_module.discover_modules(str(project_root))
            if ext_modules:
                extensions_used.append(bundle_name)

            for mod in ext_modules:
                # Get module path for deduplication/merging
                paths = mod.get('paths', {})
                mod_path = paths.get('module') or mod.get('path', '.')

                if mod_path in modules_by_path:
                    # Merge hybrid module (same path from different extensions)
                    modules_by_path[mod_path] = _merge_hybrid_module(
                        modules_by_path[mod_path], mod
                    )
                else:
                    modules_by_path[mod_path] = mod

        except Exception as e:
            log_entry('script', 'global', 'WARN', f"[MODULE-AGGREGATION] discover_modules() failed for {bundle_name}: {e}")

    # Convert modules_by_path to modules_by_name, with root module first
    # Sort paths so "." (root module) comes first, then alphabetically
    def path_sort_key(path: str) -> tuple:
        """Sort key: root module first, then alphabetically."""
        if path == "." or path == "":
            return (0, "")  # Root module always first
        return (1, path.lower())

    sorted_paths = sorted(modules_by_path.keys(), key=path_sort_key)

    modules_by_name = {}
    for path in sorted_paths:
        mod = modules_by_path[path]
        name = mod.get('name', '')
        if name:
            modules_by_name[name] = mod

    return {
        "modules": modules_by_name,
        "extensions_used": sorted(set(extensions_used))
    }
