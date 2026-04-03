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

from pathlib import Path

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:
    try:
        import tomli as tomllib  # type: ignore[no-redef]  # Fallback for Python < 3.11
    except ModuleNotFoundError:
        tomllib = None  # type: ignore[assignment]

from _build_commands import build_canonical_commands
from _build_discover import EXCLUDE_DIRS, count_source_files, discover_packages
from extension_base import build_module_base, find_readme
from plan_logging import log_entry

# Python file extensions for shared utilities
PY_EXTENSIONS: dict[str, str] = {'py': '*.py'}

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
    log_entry('script', 'global', 'INFO', f'[PYTHON-DISCOVER] Starting discovery in {project_root}')
    modules = []

    # Find directories that contain test/ or tests/ subdirectories
    module_dirs = _find_module_dirs(root)

    for module_path, relative_path in module_dirs:
        module = _build_module(module_path, root, relative_path)
        if module:
            modules.append(module)

    log_entry('script', 'global', 'INFO', f'[PYTHON-DISCOVER] Discovered {len(modules)} modules')
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

    Uses build_module_base() from extension-api when a descriptor file exists
    for consistent name/path/README resolution (at parity with Maven, Gradle,
    and npm discovery). Falls back to manual resolution when no descriptor is found.

    Args:
        module_path: Path to module directory.
        project_root: Project root path.
        relative_path: Path relative to project root.

    Returns:
        Module dict conforming to module-discovery.md, or None.
    """
    is_root = relative_path == '.'

    # Use build_module_base for consistent name/path/README when descriptor exists
    descriptor_file = _find_descriptor_file(module_path)
    if descriptor_file:
        base = build_module_base(str(project_root), str(descriptor_file))
        name = base.name
        readme_path = base.paths.readme
        descriptor = base.paths.descriptor
    else:
        name = 'default' if is_root else module_path.name
        readme = find_readme(str(module_path))
        prefix = relative_path if not is_root else ''
        readme_path = f'{prefix}/{readme}' if readme and prefix else readme
        descriptor = None

    # Find source and test directories
    source_dirs = _find_python_source_dirs(module_path)
    test_dirs = _find_python_test_dirs(module_path)

    prefix = relative_path if not is_root else ''
    source_paths = [f'{prefix}/{s}' if prefix else s for s in source_dirs]
    test_paths = [f'{prefix}/{t}' if prefix else t for t in test_dirs]

    # Count files (shared utility with Python extensions)
    source_files = count_source_files(module_path, source_dirs, extra_extensions=PY_EXTENSIONS)
    test_files = count_source_files(module_path, test_dirs, extra_extensions=PY_EXTENSIONS)

    # Packages (shared utility with Python extensions)
    packages = discover_packages(module_path, source_dirs, prefix, extra_extensions=PY_EXTENSIONS)
    test_packages = discover_packages(module_path, test_dirs, prefix, extra_extensions=PY_EXTENSIONS)

    # Metadata and dependencies from pyproject.toml
    pyproject_data = _parse_pyproject_metadata(module_path)
    metadata = pyproject_data['metadata']
    dependencies = pyproject_data['dependencies']

    # Commands
    commands = _build_commands(name, relative_path, test_files > 0)

    return {
        'name': name,
        'build_systems': ['python'],
        'paths': {
            'module': relative_path,
            'descriptor': descriptor,
            'sources': source_paths if source_paths else None,
            'tests': test_paths if test_paths else None,
            'readme': readme_path,
        },
        'metadata': metadata,
        'packages': packages,
        'test_packages': test_packages,
        'dependencies': dependencies,
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
                if entry.name.startswith('.') or entry.name.startswith('__'):
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


def _parse_pyproject_metadata(module_path: Path) -> dict:
    """Extract metadata and dependencies from pyproject.toml.

    Reads the [project] section for name, version, description, and dependencies.

    Args:
        module_path: Path to module directory.

    Returns:
        Dict with 'metadata' and 'dependencies' keys.
    """
    pyproject = module_path / 'pyproject.toml'
    metadata: dict = {}
    dependencies: list[str] = []

    if not pyproject.exists() or tomllib is None:
        return {'metadata': metadata, 'dependencies': dependencies}

    try:
        with open(pyproject, 'rb') as f:
            data = tomllib.load(f)
    except Exception:
        return {'metadata': metadata, 'dependencies': dependencies}

    project = data.get('project', {})
    if project.get('name'):
        metadata['name'] = project['name']
    if project.get('version'):
        metadata['version'] = project['version']
    if project.get('description'):
        metadata['description'] = project['description']
    if project.get('requires-python'):
        metadata['requires_python'] = project['requires-python']

    # Dependencies
    for dep in project.get('dependencies', []):
        # Extract package name (before version specifier)
        dep_name = dep.split('[')[0].split('<')[0].split('>')[0].split('=')[0].split('!')[0].split('~')[0].strip()
        if dep_name:
            dependencies.append(f'{dep_name}:runtime')

    # Dev dependencies from optional-dependencies
    for dep in project.get('optional-dependencies', {}).get('dev', []):
        dep_name = dep.split('[')[0].split('<')[0].split('>')[0].split('=')[0].split('!')[0].split('~')[0].strip()
        if dep_name:
            dependencies.append(f'{dep_name}:dev')

    return {'metadata': metadata, 'dependencies': dependencies}


def _find_descriptor_file(module_path: Path) -> Path | None:
    """Find Python project descriptor file as absolute Path.

    Args:
        module_path: Absolute path to module directory.

    Returns:
        Absolute path to descriptor file, or None.
    """
    for name in ('pyproject.toml', 'setup.cfg', 'setup.py'):
        candidate = module_path / name
        if candidate.exists():
            return candidate
    return None


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
    skill = 'plan-marshall:build-python:python_build'
    is_root = not relative_path or relative_path == '.'
    module_arg = '' if is_root else f' {module_name}'

    cmd_map: dict[str, str] = {
        'clean': 'clean',
        'compile': f'compile{module_arg}',
        'quality-gate': f'quality-gate{module_arg}',
        'verify': f'verify{module_arg}',
    }

    if has_tests:
        cmd_map['module-tests'] = f'module-tests{module_arg}'
        cmd_map['coverage'] = f'coverage{module_arg}'

    return build_canonical_commands(skill, cmd_map)


