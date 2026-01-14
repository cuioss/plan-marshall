#!/usr/bin/env python3
"""Module aggregation and virtual module splitting utilities.

Handles splitting modules discovered by multiple extensions (e.g., Maven + npm)
at the same path into separate virtual modules with technology suffixes.

Usage:
    from module_aggregation import discover_project_modules

    result = discover_project_modules(Path("/path/to/project"))
    # result = {"modules": {...}, "extensions_used": [...]}
"""

from pathlib import Path

# Direct import - executor sets up PYTHONPATH for cross-skill imports
from plan_logging import log_entry


def _get_technology(module: dict) -> str:
    """Extract primary build system from module dict.

    Args:
        module: Module dict from discover_modules()

    Returns:
        Primary build system name (e.g., "maven", "npm") or "unknown"
    """
    build_systems: list[str] = module.get('build_systems', [])
    if build_systems:
        primary: str = build_systems[0]
        return primary
    return 'unknown'


def _split_to_virtual_modules(modules: list[dict]) -> list[dict]:
    """Split modules at same path into separate virtual modules.

    When multiple extensions discover modules at the same directory path
    (e.g., pom.xml + package.json), create separate virtual modules with
    technology suffixes instead of merging them.

    Args:
        modules: List of module dicts discovered at the same path

    Returns:
        List of virtual module dicts, one per original module with:
        - name: "{base_name}-{technology}" (e.g., "my-module-maven")
        - virtual_module: {physical_path, technology, sibling_modules}
        - Single build_systems entry
        - String commands (not nested)
    """
    if len(modules) < 2:
        # Single module - no splitting needed
        return modules

    # Get the physical path from first module
    first_paths = modules[0].get('paths', {})
    physical_path = first_paths.get('module') or '.'

    # Determine base name (prefer Maven artifactId as most canonical)
    base_name = None
    for mod in modules:
        tech = _get_technology(mod)
        if tech == 'maven':
            base_name = mod.get('name')
            break
    if not base_name:
        base_name = modules[0].get('name', 'module')

    # Build list of sibling virtual module names
    technologies = [_get_technology(mod) for mod in modules]
    sibling_names = [f"{base_name}-{tech}" for tech in technologies]

    virtual_modules = []
    for i, mod in enumerate(modules):
        tech = technologies[i]
        virtual_name = f"{base_name}-{tech}"

        # Create virtual module by copying and modifying
        virtual = mod.copy()
        virtual['name'] = virtual_name
        virtual['virtual_module'] = {
            'physical_path': physical_path,
            'technology': tech,
            'sibling_modules': [s for s in sibling_names if s != virtual_name]
        }

        virtual_modules.append(virtual)

    return virtual_modules


def discover_project_modules(project_root: Path, discover_extensions_fn) -> dict:
    """Discover all modules and split multi-technology paths into virtual modules.

    Single entry point for module discovery. Handles:
    - Extension discovery (which bundles apply)
    - Module discovery per extension
    - Virtual module splitting (same path from multiple extensions)

    Args:
        project_root: Path to project root
        discover_extensions_fn: Function to discover applicable extensions.
            Should return list of dicts with 'module' and 'bundle' keys.

    Returns:
        {
            "modules": {
                "module-name": {
                    "name": "...",
                    "build_systems": ["maven"],  # single technology
                    "paths": {...},
                    "metadata": {...},
                    "commands": {...},  # string commands, not nested
                    "virtual_module": {  # only for split modules
                        "physical_path": "...",
                        "technology": "maven",
                        "sibling_modules": ["module-name-npm"]
                    }
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

    # Collect modules from all extensions, keyed by path
    # Value is a list of modules (for splitting)
    modules_by_path: dict[str, list[dict]] = {}

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
                # Get module path for deduplication/splitting
                paths = mod.get('paths', {})
                mod_path = paths.get('module') or mod.get('path', '.')

                if mod_path not in modules_by_path:
                    modules_by_path[mod_path] = []
                modules_by_path[mod_path].append(mod)

        except Exception as e:
            log_entry('script', 'global', 'WARN', f"[MODULE-AGGREGATION] discover_modules() failed for {bundle_name}: {e}")

    # Sort paths so "." (root module) comes first, then alphabetically
    def path_sort_key(path: str) -> tuple:
        """Sort key: root module first, then alphabetically."""
        if path == "." or path == "":
            return (0, "")  # Root module always first
        return (1, path.lower())

    sorted_paths = sorted(modules_by_path.keys(), key=path_sort_key)

    # Process modules: split multi-technology paths into virtual modules
    modules_by_name = {}
    for path in sorted_paths:
        path_modules = modules_by_path[path]

        # Split if multiple technologies at same path
        result_modules = _split_to_virtual_modules(path_modules)

        for mod in result_modules:
            name = mod.get('name', '')
            if name:
                modules_by_name[name] = mod

    return {
        "modules": modules_by_name,
        "extensions_used": sorted(set(extensions_used))
    }
