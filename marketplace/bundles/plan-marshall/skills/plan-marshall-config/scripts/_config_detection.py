"""
Project detection functions for plan-marshall-config.

Auto-detects build systems, domains, and modules from project files.
"""

import fnmatch
import json
import xml.etree.ElementTree as ET
from pathlib import Path

from _config_defaults import (
    BUILD_SYSTEM_DEFAULTS,
)


def detect_build_systems() -> list:
    """Auto-detect build systems from project files.

    Returns:
        List of build system configs with system and skill (detection reference only).
    """
    detected = []
    project_root = Path('.')

    # Maven
    if (project_root / 'pom.xml').exists():
        defaults = BUILD_SYSTEM_DEFAULTS['maven']
        detected.append({'system': 'maven', 'skill': defaults['skill']})

    # Gradle
    if (project_root / 'build.gradle').exists() or (project_root / 'build.gradle.kts').exists():
        defaults = BUILD_SYSTEM_DEFAULTS['gradle']
        detected.append({'system': 'gradle', 'skill': defaults['skill']})

    # npm
    if (project_root / 'package.json').exists():
        defaults = BUILD_SYSTEM_DEFAULTS['npm']
        detected.append({'system': 'npm', 'skill': defaults['skill']})

    return detected


def detect_domains() -> list:
    """Auto-detect technical domains from project files.

    Returns:
        List of detected domain keys (e.g., ['java', 'javascript']).
        Callers should use discovery to get actual domain configurations
        from bundle manifests.
    """
    detected = []
    project_root = Path('.')

    # Java detection: pom.xml or build.gradle
    if (
        (project_root / 'pom.xml').exists()
        or (project_root / 'build.gradle').exists()
        or (project_root / 'build.gradle.kts').exists()
    ):
        detected.append('java')

    # JavaScript detection: package.json
    if (project_root / 'package.json').exists():
        detected.append('javascript')

    return detected


def _parse_pom_modules(pom_path: Path) -> list:
    """Parse <modules> section from a pom.xml file.

    Args:
        pom_path: Path to pom.xml file

    Returns:
        List of module directory names from <modules> section
    """
    if not pom_path.exists():
        return []

    try:
        tree = ET.parse(pom_path)
        root = tree.getroot()

        # Handle namespace
        ns = {'m': 'http://maven.apache.org/POM/4.0.0'}

        # Try with namespace first
        modules_elem = root.find('m:modules', ns)
        if modules_elem is None:
            # Try without namespace
            modules_elem = root.find('modules')

        if modules_elem is not None:
            return [m.text for m in modules_elem if m.text]
    except ET.ParseError:
        pass

    return []


def _discover_maven_modules_recursive(base_path: Path, parent_name: str | None = None, path_prefix: str = '') -> list:
    """Recursively discover Maven modules starting from a directory.

    Args:
        base_path: Directory containing pom.xml to scan
        parent_name: Name of parent module (None for root)
        path_prefix: Path prefix for nested modules (e.g., "parent-dir/")

    Returns:
        List of module info dicts with name, path, and parent fields
    """
    modules: list[dict[str, str]] = []
    pom_path = base_path / 'pom.xml'

    if not pom_path.exists():
        return modules

    # Get modules declared in this pom.xml
    declared_modules = _parse_pom_modules(pom_path)

    for mod_dir in declared_modules:
        mod_path = base_path / mod_dir
        if not mod_path.is_dir():
            continue

        # Build the full relative path from project root
        full_path = f'{path_prefix}{mod_dir}' if path_prefix else mod_dir

        # Use directory name as module name
        mod_name = mod_dir

        module_info = {'name': mod_name, 'path': full_path}
        if parent_name:
            module_info['parent'] = parent_name

        modules.append(module_info)

        # Recursively discover nested modules
        nested = _discover_maven_modules_recursive(
            base_path=mod_path, parent_name=mod_name, path_prefix=f'{full_path}/'
        )
        modules.extend(nested)

    return modules


def detect_maven_modules() -> list:
    """Detect Maven modules from pom.xml recursively.

    Scans the root pom.xml and recursively follows <modules> entries
    to discover all nested modules in the project.

    Returns:
        List of module info dicts with:
        - name: Module directory name
        - path: Relative path from project root
        - parent: Parent module name (only for nested modules)
    """
    return _discover_maven_modules_recursive(Path('.'))


def _expand_workspace_pattern(base_path: Path, pattern: str) -> list:
    """Expand a workspace pattern to matching directories.

    Handles patterns like "packages/*" or "apps/frontend".

    Args:
        base_path: Base directory to search from
        pattern: Workspace pattern (may include * glob)

    Returns:
        List of matching directory paths relative to base_path
    """
    if '*' not in pattern:
        # Direct path, check if it exists
        target = base_path / pattern
        if target.is_dir() and (target / 'package.json').exists():
            return [pattern]
        return []

    # Pattern with glob - find matching directories
    # Split pattern to get the directory part and the glob part
    parts = pattern.split('/')
    glob_index = next((i for i, p in enumerate(parts) if '*' in p), -1)

    if glob_index == -1:
        return []

    # Build prefix path and glob pattern
    prefix = '/'.join(parts[:glob_index]) if glob_index > 0 else ''
    glob_part = parts[glob_index]

    search_dir = base_path / prefix if prefix else base_path
    if not search_dir.is_dir():
        return []

    matches = []
    for entry in search_dir.iterdir():
        if entry.is_dir() and fnmatch.fnmatch(entry.name, glob_part):
            # Check if it has a package.json
            if (entry / 'package.json').exists():
                rel_path = f'{prefix}/{entry.name}' if prefix else entry.name
                matches.append(rel_path)

    return matches


def detect_npm_workspaces() -> list:
    """Detect npm workspaces from package.json.

    Parses the root package.json for workspaces configuration and
    discovers all workspace packages.

    Returns:
        List of module info dicts with:
        - name: Package name from package.json (or directory name)
        - path: Relative path from project root
    """
    modules: list[dict[str, str]] = []
    pkg_path = Path('package.json')

    if not pkg_path.exists():
        return modules

    try:
        pkg_data = json.loads(pkg_path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return modules

    # Get workspaces config
    workspaces = pkg_data.get('workspaces', [])

    # Handle both array and object formats
    # Array: ["packages/*", "apps/*"]
    # Object: {"packages": ["packages/*"]}
    if isinstance(workspaces, dict):
        workspaces = workspaces.get('packages', [])

    if not isinstance(workspaces, list):
        return modules

    # Expand each workspace pattern
    base_path = Path('.')
    for pattern in workspaces:
        if not isinstance(pattern, str):
            continue

        matched_dirs = _expand_workspace_pattern(base_path, pattern)

        for rel_path in matched_dirs:
            pkg_json_path = base_path / rel_path / 'package.json'
            if pkg_json_path.exists():
                try:
                    workspace_pkg = json.loads(pkg_json_path.read_text(encoding='utf-8'))
                    name = workspace_pkg.get('name', rel_path.split('/')[-1])
                except (OSError, json.JSONDecodeError):
                    name = rel_path.split('/')[-1]
            else:
                name = rel_path.split('/')[-1]

            modules.append({'name': name, 'path': rel_path})

    return modules
