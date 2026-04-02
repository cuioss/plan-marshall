#!/usr/bin/env python3
"""npm module discovery command.

Discovers npm modules (workspaces) with metadata from package.json files
and file system analysis. Implements the discover_modules() contract
from module-discovery.md.

Data Sources:
    FROM PACKAGE.JSON:
        - name, version, description
        - scripts (available npm scripts)
        - workspaces (monorepo workspace definitions)
        - dependencies, devDependencies

Usage:
    python3 _npm_cmd_discover.py discover --root /path/to/project [--format json]

Output:
    JSON array of module objects conforming to module-discovery.md contract.
"""

import argparse
import json
from pathlib import Path

# Direct imports - executor sets up PYTHONPATH for cross-skill imports
from extension_base import (
    count_source_files,
    discover_packages,
    discover_sources,
    find_readme,
)


# =============================================================================
# Module Discovery
# =============================================================================


def discover_npm_modules(project_root: str) -> list:
    """Discover all npm modules (workspaces) with metadata.

    Reads root package.json for workspace definitions, then collects
    metadata from each workspace's package.json.

    Args:
        project_root: Absolute path to project root.

    Returns:
        List of module dicts conforming to module-discovery.md contract.
    """
    root = Path(project_root).resolve()
    root_pkg = root / 'package.json'

    if not root_pkg.exists():
        return []

    root_data = _load_package_json(root_pkg)
    if root_data is None:
        return []

    modules = []

    # Discover workspace directories
    workspace_dirs = _resolve_workspaces(root, root_data)

    if workspace_dirs:
        # Monorepo: root + each workspace
        root_module = _build_module(root, root, root_data, is_root=True)
        if root_module:
            modules.append(root_module)
        for ws_dir in workspace_dirs:
            ws_pkg = ws_dir / 'package.json'
            if ws_pkg.exists():
                ws_data = _load_package_json(ws_pkg)
                if ws_data:
                    module = _build_module(ws_dir, root, ws_data, is_root=False)
                    if module:
                        modules.append(module)
    else:
        # Single-package project
        module = _build_module(root, root, root_data, is_root=True)
        if module:
            modules.append(module)

    return modules


# =============================================================================
# Workspace Resolution
# =============================================================================


def _resolve_workspaces(root: Path, root_data: dict) -> list[Path]:
    """Resolve workspace directories from package.json workspaces field.

    Supports:
    - Array of glob patterns: ["packages/*", "apps/*"]
    - Object with packages field: {"packages": ["packages/*"]}

    Args:
        root: Project root directory.
        root_data: Parsed root package.json.

    Returns:
        List of resolved workspace directory paths.
    """
    workspaces = root_data.get('workspaces', [])

    # Handle object format: {"packages": [...]}
    if isinstance(workspaces, dict):
        workspaces = workspaces.get('packages', [])

    if not isinstance(workspaces, list):
        return []

    dirs: list[Path] = []
    for pattern in workspaces:
        if not isinstance(pattern, str):
            continue
        # Glob patterns like "packages/*"
        for match in sorted(root.glob(pattern)):
            if match.is_dir() and (match / 'package.json').exists():
                dirs.append(match)

    return dirs


# =============================================================================
# Module Building
# =============================================================================


def _build_module(module_path: Path, project_root: Path, pkg_data: dict, *, is_root: bool) -> dict | None:
    """Build module dict from package.json data and file system analysis.

    Args:
        module_path: Path to module directory.
        project_root: Project root path.
        pkg_data: Parsed package.json data.
        is_root: Whether this is the root module.

    Returns:
        Module dict conforming to module-discovery.md, or None.
    """
    try:
        relative_path = str(module_path.relative_to(project_root))
    except ValueError:
        relative_path = '.'
    if relative_path == '.':
        relative_path = '.'

    name = pkg_data.get('name', module_path.name)
    if is_root and not pkg_data.get('name'):
        name = 'default'

    # Source directories (shared multi-language discovery)
    sources = discover_sources(module_path)
    prefix = relative_path if relative_path != '.' else ''
    source_paths = [f'{prefix}/{s}' if prefix else s for s in sources['main']]
    test_paths = [f'{prefix}/{t}' if prefix else t for t in sources['test']]

    # Packages via shared discovery
    packages = discover_packages(module_path, sources.get('main', []), prefix)
    test_packages = discover_packages(module_path, sources.get('test', []), prefix)

    # Stats via shared counting
    source_files = count_source_files(module_path, sources['main'])
    test_files = count_source_files(module_path, sources['test'])

    # README
    readme = find_readme(str(module_path))
    readme_path = f'{prefix}/{readme}' if readme and prefix else readme

    # Scripts from package.json
    scripts = pkg_data.get('scripts', {})

    # Dependencies
    dependencies = _extract_dependencies(pkg_data)

    # Commands
    commands = _build_commands(name, scripts, relative_path)

    return {
        'name': name,
        'build_systems': ['npm'],
        'paths': {
            'module': relative_path,
            'descriptor': f'{prefix}/package.json' if prefix else 'package.json',
            'sources': source_paths if source_paths else None,
            'tests': test_paths if test_paths else None,
            'readme': readme_path,
        },
        'metadata': {
            'description': pkg_data.get('description'),
            'version': pkg_data.get('version'),
            'scripts': list(scripts.keys()) if scripts else [],
        },
        'packages': packages,
        'test_packages': test_packages,
        'dependencies': dependencies,
        'stats': {'source_files': source_files, 'test_files': test_files},
        'commands': commands,
    }


def _extract_dependencies(pkg_data: dict) -> list[str]:
    """Extract dependencies as compact strings.

    Args:
        pkg_data: Parsed package.json data.

    Returns:
        List of dependency strings in format 'name:scope'.
    """
    deps: list[str] = []
    for name in pkg_data.get('dependencies', {}):
        deps.append(f'{name}:runtime')
    for name in pkg_data.get('devDependencies', {}):
        deps.append(f'{name}:dev')
    return deps


# =============================================================================
# Commands
# =============================================================================


def _build_commands(module_name: str, scripts: dict, relative_path: str) -> dict:
    """Build commands object with resolved canonical command strings.

    Commands are only generated for scripts that exist in package.json.

    Args:
        module_name: Module name.
        scripts: package.json scripts object.
        relative_path: Path relative to project root.
    """
    base = 'python3 .plan/execute-script.py plan-marshall:build-npm:npm run'

    is_root = not relative_path or relative_path == '.'
    ws_arg = '' if is_root else f' --workspace={module_name}'

    commands: dict[str, str] = {}

    # clean: only if script exists
    if 'clean' in scripts:
        commands['clean'] = f'{base} --command-args "run clean{ws_arg}"'

    # compile / build
    if 'build' in scripts:
        commands['compile'] = f'{base} --command-args "run build{ws_arg}"'

    # quality-gate / lint
    if 'lint' in scripts:
        commands['quality-gate'] = f'{base} --command-args "run lint{ws_arg}"'

    # module-tests / test
    if 'test' in scripts:
        commands['module-tests'] = f'{base} --command-args "run test{ws_arg}"'

    # verify: build + test if both exist, otherwise just test
    if 'build' in scripts and 'test' in scripts:
        commands['verify'] = f'{base} --command-args "run build{ws_arg}" && {base} --command-args "run test{ws_arg}"'
    elif 'test' in scripts:
        commands['verify'] = f'{base} --command-args "run test{ws_arg}"'

    return commands


# =============================================================================
# Helpers
# =============================================================================


def _load_package_json(path: Path) -> dict | None:
    """Load and parse a package.json file.

    Args:
        path: Path to package.json.

    Returns:
        Parsed dict, or None on error.
    """
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return None


# =============================================================================
# CLI
# =============================================================================


def main():
    parser = argparse.ArgumentParser(description='npm module discovery')
    subparsers = parser.add_subparsers(dest='command', required=True)

    discover_parser = subparsers.add_parser('discover', help='Discover npm modules')
    discover_parser.add_argument('--root', required=True, help='Project root directory')
    discover_parser.add_argument('--format', choices=['json'], default='json', help='Output format')

    args = parser.parse_args()

    if args.command == 'discover':
        modules = discover_npm_modules(args.root)
        print(json.dumps(modules, indent=2))


if __name__ == '__main__':
    main()
