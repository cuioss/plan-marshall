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

import json
import re
from pathlib import Path

# Direct imports - executor sets up PYTHONPATH for cross-skill imports
from _build_discover import (
    JS_EXTENSIONS,
    build_module_base,
    count_source_files,
    discover_js_sources,
    discover_packages,
)
from _build_shared import build_canonical_commands, build_chained_commands
from plan_logging import log_entry

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
    log_entry('script', 'global', 'INFO', f'[NPM-DISCOVER] Starting discovery in {project_root}')
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

    log_entry('script', 'global', 'INFO', f'[NPM-DISCOVER] Discovered {len(modules)} modules')
    return modules


def discover_standalone_npm_module(project_root: str, module_path: str) -> dict | None:
    """Discover a standalone npm module at a specific path.

    Used for nested package.json files found inside modules of other build
    systems (e.g., Playwright e2e tests inside a Maven project). These
    modules are not part of any npm workspace configuration.

    Args:
        project_root: Absolute path to project root.
        module_path: Absolute path to directory containing package.json.

    Returns:
        Module dict conforming to module-discovery.md contract, or None.
    """
    mod_dir = Path(module_path).resolve()
    root = Path(project_root).resolve()
    pkg_json = mod_dir / 'package.json'

    if not pkg_json.exists():
        return None

    pkg_data = _load_package_json(pkg_json)
    if pkg_data is None:
        return None

    log_entry('script', 'global', 'INFO', f'[NPM-DISCOVER] Standalone module at {module_path}')
    return _build_module(mod_dir, root, pkg_data, is_root=False, standalone=True)


# =============================================================================
# Workspace Resolution
# =============================================================================


def _resolve_workspaces(root: Path, root_data: dict) -> list[Path]:
    """Resolve workspace directories from package.json or pnpm-workspace.yaml.

    Supports:
    - npm/yarn: Array of glob patterns: ["packages/*", "apps/*"]
    - npm/yarn: Object with packages field: {"packages": ["packages/*"]}
    - pnpm: pnpm-workspace.yaml with packages field

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

    # If no workspaces in package.json, check pnpm-workspace.yaml
    if not workspaces:
        workspaces = _resolve_pnpm_workspaces(root)

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


def _resolve_pnpm_workspaces(root: Path) -> list[str]:
    """Resolve workspace patterns from pnpm-workspace.yaml.

    Args:
        root: Project root directory.

    Returns:
        List of workspace glob patterns, or empty list.
    """
    pnpm_ws = root / 'pnpm-workspace.yaml'
    if not pnpm_ws.exists():
        return []

    try:
        content = pnpm_ws.read_text(encoding='utf-8')
        # Simple YAML parsing for packages list (avoids PyYAML dependency)
        # Format:
        #   packages:
        #     - 'packages/*'
        #     - 'apps/*'
        packages: list[str] = []
        in_packages = False
        for line in content.split('\n'):
            stripped = line.strip()
            if stripped.startswith('packages:'):
                in_packages = True
                continue
            if in_packages:
                match = re.match(r"^\s*-\s*['\"]?([^'\"]+)['\"]?\s*$", line)
                if match:
                    packages.append(match.group(1).strip())
                elif stripped and not stripped.startswith('#') and not stripped.startswith('-'):
                    break  # New top-level key
        return packages
    except OSError:
        return []


# =============================================================================
# Module Building
# =============================================================================


def _build_module(module_path: Path, project_root: Path, pkg_data: dict, *, is_root: bool, standalone: bool = False) -> dict | None:
    """Build module dict from package.json data and file system analysis.

    Uses build_module_base() from extension-api for consistent name/path/README
    resolution, then enriches with npm-specific metadata.

    Args:
        module_path: Path to module directory.
        project_root: Project root path.
        pkg_data: Parsed package.json data.
        is_root: Whether this is the root module.
        standalone: Whether this is a standalone nested module (uses --prefix).

    Returns:
        Module dict conforming to module-discovery.md, or None.
    """
    pkg_json_path = module_path / 'package.json'
    base = build_module_base(str(project_root), str(pkg_json_path))

    # Override name from package.json if available
    name = pkg_data.get('name', base.name)
    if is_root and not pkg_data.get('name'):
        name = 'default'

    relative_path = base.paths.module

    # Source directories (JS-aware discovery for JS/TS projects)
    sources = discover_js_sources(module_path)
    prefix = relative_path if relative_path != '.' else ''
    source_paths = [f'{prefix}/{s}' if prefix else s for s in sources['main']]
    test_paths = [f'{prefix}/{t}' if prefix else t for t in sources['test']]

    # Packages via shared discovery (with JS extensions)
    packages = discover_packages(module_path, sources.get('main', []), prefix, extra_extensions=JS_EXTENSIONS)
    test_packages = discover_packages(module_path, sources.get('test', []), prefix, extra_extensions=JS_EXTENSIONS)

    # Stats via shared counting (with JS extensions)
    source_files = count_source_files(module_path, sources['main'], extra_extensions=JS_EXTENSIONS)
    test_files = count_source_files(module_path, sources['test'], extra_extensions=JS_EXTENSIONS)

    # Scripts from package.json
    scripts = pkg_data.get('scripts', {})

    # Dependencies
    dependencies = _extract_dependencies(pkg_data)

    # Commands
    commands = _build_commands(name, scripts, relative_path, standalone=standalone)

    return {
        'name': name,
        'build_systems': ['npm'],
        'paths': {
            'module': relative_path,
            'descriptor': base.paths.descriptor,
            'sources': source_paths if source_paths else None,
            'tests': test_paths if test_paths else None,
            'readme': base.paths.readme,
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


def _build_commands(module_name: str, scripts: dict, relative_path: str, *, standalone: bool = False) -> dict:
    """Build commands object with resolved canonical command strings.

    Commands are only generated for scripts that exist in package.json.

    Args:
        module_name: Module name.
        scripts: package.json scripts object.
        relative_path: Path relative to project root.
        standalone: Whether this is a standalone nested module (uses --prefix).
    """
    skill = 'plan-marshall:build-npm:npm'
    is_root = not relative_path or relative_path == '.'
    if standalone and not is_root:
        ws_arg = f' --prefix={relative_path}'
    elif is_root:
        ws_arg = ''
    else:
        ws_arg = f' --workspace={module_name}'

    cmd_map: dict[str, str] = {}

    # install is always available for npm
    cmd_map['install'] = f'install{ws_arg}'

    if 'clean' in scripts:
        cmd_map['clean'] = f'run clean{ws_arg}'

    if 'build' in scripts:
        cmd_map['compile'] = f'run build{ws_arg}'
    elif 'typecheck' in scripts:
        cmd_map['compile'] = f'run typecheck{ws_arg}'
    elif 'type-check' in scripts:
        cmd_map['compile'] = f'run type-check{ws_arg}'

    if 'lint' in scripts:
        cmd_map['quality-gate'] = f'run lint{ws_arg}'
    elif 'check' in scripts:
        cmd_map['quality-gate'] = f'run check{ws_arg}'

    if 'test' in scripts:
        cmd_map['module-tests'] = f'run test{ws_arg}'

    if 'test:coverage' in scripts:
        cmd_map['coverage'] = f'run test:coverage{ws_arg}'
    elif 'coverage' in scripts:
        cmd_map['coverage'] = f'run coverage{ws_arg}'

    commands = build_canonical_commands(skill, cmd_map)

    # verify: chained build + test if both exist, otherwise just test
    if 'build' in scripts and 'test' in scripts:
        commands['verify'] = build_chained_commands(skill, [f'run build{ws_arg}', f'run test{ws_arg}'])
    elif 'test' in scripts:
        commands['verify'] = build_canonical_commands(skill, {'verify': f'run test{ws_arg}'})['verify']

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
        data: dict = json.loads(path.read_text(encoding='utf-8'))
        return data
    except (OSError, json.JSONDecodeError):
        return None
