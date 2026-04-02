#!/usr/bin/env python3
"""Python module discovery command.

Discovers Python modules with metadata from pyprojectx project structure
and file system analysis. Implements the discover_modules() contract
from module-discovery.md.

Data Sources:
    FROM FILE SYSTEM:
        - Module directories containing test/ or tests/ subdirectories
        - Source files (*.py) in module directories
        - pyproject.toml / setup.cfg for metadata (if present)

Usage:
    python3 _python_cmd_discover.py discover --root /path/to/project [--format json]

Output:
    JSON array of module objects conforming to module-discovery.md contract.
"""

import argparse
import json
from pathlib import Path

from _build_discover import EXCLUDE_DIRS, find_readme
from _build_format import format_toon

# Python source extensions
PYTHON_EXTENSIONS = ['*.py']

# Directories that indicate a test module
TEST_DIR_NAMES = {'test', 'tests'}

# Directories to skip during module discovery (beyond EXCLUDE_DIRS)
PYTHON_EXCLUDE_DIRS = EXCLUDE_DIRS | {'.venv', 'venv', '.tox', '.mypy_cache', '.ruff_cache', '.pytest_cache', 'dist', 'egg-info'}


# =============================================================================
# Module Discovery
# =============================================================================


def discover_python_modules(project_root: str) -> list:
    """Discover all Python modules in a pyprojectx project.

    Modules are directories containing test/ or tests/ subdirectories,
    following the pyprojectx convention where ./pw module-tests {module}
    targets a specific module.

    Args:
        project_root: Absolute path to project root.

    Returns:
        List of module dicts conforming to module-discovery.md contract.
    """
    root = Path(project_root).resolve()
    modules = []

    # Find directories that contain test/ or tests/ subdirectories
    module_dirs = _find_module_dirs(root)

    for module_path, relative_path in module_dirs:
        module = _build_module(module_path, root, relative_path)
        if module:
            modules.append(module)

    return modules


def _find_module_dirs(root: Path) -> list[tuple[Path, str]]:
    """Find directories that qualify as Python modules.

    A directory qualifies if it contains a test/ or tests/ subdirectory.
    Searches one level deep from the project root (immediate subdirectories).

    Also includes the root itself if it has test directories.

    Args:
        root: Project root directory.

    Returns:
        List of (absolute_path, relative_path) tuples.
    """
    module_dirs: list[tuple[Path, str]] = []

    # Check root directory
    if _has_test_dir(root):
        module_dirs.append((root, '.'))

    # Check immediate subdirectories
    try:
        for entry in sorted(root.iterdir()):
            if not entry.is_dir():
                continue
            if entry.name in PYTHON_EXCLUDE_DIRS:
                continue
            if entry.name.startswith('.'):
                continue
            if _has_test_dir(entry):
                module_dirs.append((entry, entry.name))
    except PermissionError:
        pass

    return module_dirs


def _has_test_dir(directory: Path) -> bool:
    """Check if a directory contains test/ or tests/ subdirectory."""
    for test_name in TEST_DIR_NAMES:
        test_dir = directory / test_name
        if test_dir.is_dir():
            return True
    return False


# =============================================================================
# Module Building
# =============================================================================


def _build_module(module_path: Path, project_root: Path, relative_path: str) -> dict | None:
    """Build module dict from file system analysis.

    Args:
        module_path: Path to module directory.
        project_root: Project root path.
        relative_path: Path relative to project root.

    Returns:
        Module dict conforming to module-discovery.md, or None.
    """
    is_root = relative_path == '.'
    name = 'default' if is_root else module_path.name

    # Find source and test directories
    source_dirs = _find_python_source_dirs(module_path)
    test_dirs = _find_python_test_dirs(module_path)

    prefix = relative_path if not is_root else ''
    source_paths = [f'{prefix}/{s}' if prefix else s for s in source_dirs]
    test_paths = [f'{prefix}/{t}' if prefix else t for t in test_dirs]

    # Count files
    source_files = _count_python_files(module_path, source_dirs)
    test_files = _count_python_files(module_path, test_dirs)

    # README
    readme = find_readme(str(module_path))
    readme_path = f'{prefix}/{readme}' if readme and prefix else readme

    # Commands
    commands = _build_commands(name, relative_path, test_files > 0)

    return {
        'name': name,
        'build_systems': ['python'],
        'paths': {
            'module': relative_path,
            'sources': source_paths if source_paths else None,
            'tests': test_paths if test_paths else None,
            'readme': readme_path,
        },
        'stats': {'source_files': source_files, 'test_files': test_files},
        'commands': commands,
    }


def _find_python_source_dirs(module_path: Path) -> list[str]:
    """Find Python source directories in a module.

    Looks for directories containing .py files, excluding test directories
    and common non-source directories.
    """
    source_dirs: list[str] = []

    # Check for src/ layout
    src_dir = module_path / 'src'
    if src_dir.is_dir():
        source_dirs.append('src')
    else:
        # Check for package directories (dirs with __init__.py)
        try:
            for entry in sorted(module_path.iterdir()):
                if not entry.is_dir():
                    continue
                if entry.name in PYTHON_EXCLUDE_DIRS or entry.name in TEST_DIR_NAMES:
                    continue
                if entry.name.startswith('.') or entry.name.startswith('_'):
                    continue
                if (entry / '__init__.py').exists() or any(entry.glob('*.py')):
                    source_dirs.append(entry.name)
        except PermissionError:
            pass

    return source_dirs


def _find_python_test_dirs(module_path: Path) -> list[str]:
    """Find Python test directories in a module."""
    test_dirs: list[str] = []
    for test_name in sorted(TEST_DIR_NAMES):
        test_dir = module_path / test_name
        if test_dir.is_dir():
            test_dirs.append(test_name)
    return test_dirs


def _count_python_files(module_path: Path, dirs: list[str]) -> int:
    """Count Python files in the given directories."""
    count = 0
    for d in dirs:
        dir_path = module_path / d
        if dir_path.exists():
            count += len(list(dir_path.rglob('*.py')))
    return count


# =============================================================================
# Commands
# =============================================================================


def _build_commands(module_name: str, relative_path: str, has_tests: bool) -> dict:
    """Build commands object with resolved canonical command strings.

    Args:
        module_name: Module name.
        relative_path: Path relative to project root.
        has_tests: Whether module has test files.
    """
    base = 'python3 .plan/execute-script.py plan-marshall:build-python:python_build run'

    is_root = not relative_path or relative_path == '.'
    module_arg = '' if is_root else f' {module_name}'

    commands: dict[str, str] = {
        'clean': f'{base} --command-args "clean"',
        'compile': f'{base} --command-args "compile{module_arg}"',
        'quality-gate': f'{base} --command-args "quality-gate{module_arg}"',
        'verify': f'{base} --command-args "verify{module_arg}"',
    }

    if has_tests:
        commands['module-tests'] = f'{base} --command-args "module-tests{module_arg}"'
        commands['coverage'] = f'{base} --command-args "coverage{module_arg}"'

    return commands


# =============================================================================
# CLI
# =============================================================================


def main():
    parser = argparse.ArgumentParser(description='Python module discovery')
    subparsers = parser.add_subparsers(dest='command', required=True)

    discover_parser = subparsers.add_parser('discover', help='Discover Python modules')
    discover_parser.add_argument('--root', required=True, help='Project root directory')
    discover_parser.add_argument('--format', choices=['toon', 'json'], default='toon', help='Output format')

    args = parser.parse_args()

    if args.command == 'discover':
        modules = discover_python_modules(args.root)
        result = {'status': 'success', 'modules': modules, 'count': len(modules)}
        if args.format == 'json':
            print(json.dumps(result, indent=2))
        else:
            print(format_toon(result))


if __name__ == '__main__':
    main()
