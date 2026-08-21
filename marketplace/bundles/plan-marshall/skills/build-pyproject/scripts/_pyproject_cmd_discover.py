#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Pyproject module discovery command.

Discovers Python modules with metadata from pyprojectx project structure
and file system analysis. Implements the discover_modules() contract
from module-discovery.md.

Data Sources:
    FROM FILE SYSTEM:
        - Module directories containing test/ or tests/ subdirectories
        - Source files (*.py) in module directories
        - pyproject.toml / setup.cfg for metadata (if present)

Usage:
    python3 _pyproject_cmd_discover.py discover --root /path/to/project [--format json]

Output:
    JSON array of module objects conforming to module-discovery.md contract.
"""

import configparser
from pathlib import Path

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:
    try:
        import tomli as tomllib  # type: ignore[no-redef]  # Fallback for Python < 3.11
    except ModuleNotFoundError:
        tomllib = None  # type: ignore[assignment]

from _build_discover import (
    EXCLUDE_DIRS,
    PY_EXTENSIONS,
    build_module_base,
    count_source_files,
    discover_packages,
    find_readme,
)
from _build_shared import build_canonical_commands
from plan_logging import log_entry

# Bound once so the narrowed descriptor catch names a real exception class even
# on an interpreter where no TOML reader could be imported at all.
TOML_DECODE_ERROR: type[Exception] = getattr(tomllib, 'TOMLDecodeError', ValueError)

# Directories that indicate a test module
TEST_DIR_NAMES = {'test', 'tests'}

# Directories to skip during module discovery (beyond EXCLUDE_DIRS)
PYTHON_EXCLUDE_DIRS = EXCLUDE_DIRS | {
    '.venv',
    'venv',
    '.tox',
    '.mypy_cache',
    '.ruff_cache',
    '.pytest_cache',
    'dist',
    'egg-info',
}


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
    log_entry('script', 'global', 'DEBUG', f'[PYTHON-DISCOVER] Starting discovery in {project_root}')
    modules = []

    # Find directories that contain test/ or tests/ subdirectories
    module_dirs = _find_module_dirs(root)

    for module_path, relative_path in module_dirs:
        module = _build_module(module_path, root, relative_path)
        if module:
            modules.append(module)

    log_entry('script', 'global', 'DEBUG', f'[PYTHON-DISCOVER] Discovered {len(modules)} modules')
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


def requirement_name(requirement: str) -> str:
    """Return the bare distribution name from one PEP 508 requirement string.

    The order matters, and two of the three steps exist because the specifier
    chain alone silently mangles perfectly ordinary requirements:

    1. **Environment marker first.** ``m-core; python_version >= "3.11"``
       truncates at the first ``>`` if the specifier chain runs first, leaving
       ``m-core; python_version`` — a mangled key that survives PEP 503
       normalisation looking plausible, so nothing downstream can spot it.
    2. **Direct reference next, on the BARE ``@``.** PEP 508 spells the URL form
       ``urlspec = AT wsp* URI_reference``, so the whitespace around ``@`` is
       optional and ``m-core@file:///./core`` — the spelling ``pip freeze``
       emits — is as legal as the spaced one. Splitting on ``' @ '`` would fix
       only the spaced form. The bare ``@`` is safe to split on: it is not legal
       in a PEP 508 name, and an npm-style ``@scope/`` never appears in a Python
       requirement.
    3. **Extras and version specifiers last.**

    Args:
        requirement: One PEP 508 requirement string.

    Returns:
        The distribution name, or ``''`` when the string carries none.
    """
    head = requirement.split(';', 1)[0]
    head = head.split('@', 1)[0]
    for separator in ('[', '<', '>', '=', '!', '~'):
        head = head.split(separator)[0]
    return head.strip()


def _parse_pyproject_metadata(module_path: Path) -> dict:
    """Extract metadata and dependencies from the module's Python descriptor.

    Reads PEP 621 ``[project]`` first. When that table is absent or carries no
    ``name``, falls back to ``[tool.poetry]`` in the same file and then to
    ``setup.cfg`` — because a module whose descriptor this function cannot read
    is admitted to the module set anyway, stamped ``build_systems: ['python']``
    and given a real ``paths.descriptor``, and then contributes nothing. The
    seam reports that as ``status: ok, edge_count: 0``, which the shipped
    documentation defines as a real, positive result. It is not one: it is a
    descriptor nobody parsed.

    The fallbacks are **strict** — neither fires while ``[project]`` supplies a
    name — because ``metadata`` and ``dependencies`` are read by consumers
    beyond edge derivation, and a fallback that overrode a PEP 621 declaration
    would change what those consumers see.

    ``setup.py`` is deliberately not attempted: it is executable Python and not
    statically parseable in general. A ``setup.py``-only module keeps publishing
    no name, and ``doc/user/dependency-intelligence.adoc`` § Python specifics
    states that limit rather than leaving it silent.

    Args:
        module_path: Path to module directory.

    Returns:
        Dict with 'metadata' and 'dependencies' keys.
    """
    metadata: dict = {}
    dependencies: list[str] = []

    pyproject = module_path / 'pyproject.toml'
    if pyproject.exists() and tomllib is not None:
        data = _load_toml(pyproject)
        if data is not None:
            _read_pep621(data, metadata, dependencies)
            if not metadata.get('name'):
                _read_poetry(data, metadata, dependencies)
        if metadata.get('name'):
            return {'metadata': metadata, 'dependencies': dependencies}

    setup_cfg = module_path / 'setup.cfg'
    if not metadata.get('name') and setup_cfg.exists():
        _read_setup_cfg(setup_cfg, metadata, dependencies)

    return {'metadata': metadata, 'dependencies': dependencies}


def _load_toml(descriptor: Path) -> dict | None:
    """Parse a TOML descriptor, or log a WARNING naming the file and return None.

    The catch is narrowed to the three exceptions a *descriptor problem* raises.
    A bare ``except Exception`` made a malformed descriptor indistinguishable
    from one declaring nothing — and that silence kills the **dependent's**
    declared edge too, because the unparsed module published no name for the
    dependent's requirement to match. Anything outside this set is a defect in
    this code and propagates.
    """
    try:
        with open(descriptor, 'rb') as handle:
            data: dict = tomllib.load(handle)
    except (TOML_DECODE_ERROR, OSError, UnicodeDecodeError) as exc:
        log_entry(
            'script', 'global', 'WARNING',
            f'[PYTHON-DISCOVER] Unreadable descriptor {descriptor}: {type(exc).__name__}: {exc} — '
            f'the module publishes no name or dependencies, and any edge declared ON it is lost',
        )
        return None
    return data


def _read_pep621(data: dict, metadata: dict, dependencies: list[str]) -> None:
    """Read the PEP 621 ``[project]`` table into ``metadata`` / ``dependencies``."""
    project = data.get('project') or {}
    for key, field in (('name', 'name'), ('version', 'version'), ('description', 'description'),
                       ('requires-python', 'requires_python')):
        if project.get(key):
            metadata[field] = project[key]

    for dep in project.get('dependencies', []):
        name = requirement_name(dep)
        if name:
            dependencies.append(f'{name}:runtime')

    for dep in (project.get('optional-dependencies') or {}).get('dev', []):
        name = requirement_name(dep)
        if name:
            dependencies.append(f'{name}:dev')


def _read_poetry(data: dict, metadata: dict, dependencies: list[str]) -> None:
    """Read ``[tool.poetry]`` into ``metadata`` / ``dependencies``.

    A Poetry dependency's **value** may be a version string or an inline table
    (``{version = "^1.0", optional = true}``); only the key carries the name, so
    the value is not inspected. ``python`` is skipped — it is the interpreter
    constraint, not a package, and Poetry records it alongside the real ones.
    """
    poetry = (data.get('tool') or {}).get('poetry') or {}
    if not poetry:
        return
    for key, field in (('name', 'name'), ('version', 'version'), ('description', 'description')):
        if poetry.get(key):
            metadata[field] = poetry[key]

    for name in (poetry.get('dependencies') or {}):
        if name == 'python':
            continue
        dependencies.append(f'{requirement_name(name)}:runtime')

    dev_groups = (poetry.get('group') or {}).get('dev') or {}
    for name in (dev_groups.get('dependencies') or {}):
        if name == 'python':
            continue
        dependencies.append(f'{requirement_name(name)}:dev')


def _read_setup_cfg(descriptor: Path, metadata: dict, dependencies: list[str]) -> None:
    """Read a setuptools ``setup.cfg`` into ``metadata`` / ``dependencies``.

    ``[metadata]`` supplies name/version/description; ``[options]
    install_requires`` is a newline-separated requirement list, read at scope
    ``runtime`` through the same PEP 508 name extraction the TOML paths use.

    ⛔ **Every read is inside the guard**, because ``BasicInterpolation`` raises
    from ``get()`` — not from ``read()``. A bare ``%`` in a value
    (``description = 100% pure python``, a percent-encoded URL in
    ``install_requires``) therefore escaped a guard that wrapped only ``read()``,
    propagated out of ``discover_python_modules``, and took **every** module with
    it — including the ones whose descriptors parsed perfectly. One module's
    percent sign cost the whole capability, which is the exact failure this
    discoverer's narrowed ``_load_toml`` catch exists to prevent.

    ⚠ **Interpolation stays ON, deliberately, and the choice is not free.**
    setuptools reads ``setup.cfg`` with ``BasicInterpolation`` too: it resolves
    ``name = acme-%(version)s`` to ``acme-1.0`` and ``50%%`` to ``50%``, and it
    **rejects** ``100% pure python`` exactly as this does. Disabling
    interpolation would let that last value through — but at the price of
    publishing ``acme-%(version)s`` where the ecosystem publishes ``acme-1.0``,
    in the very field edge derivation joins on, silently making the module an
    unreachable edge target. Agreeing with setuptools on **all three** matters
    more than reading one of them: a descriptor setuptools refuses is one this
    module is right to skip, and skipping it now costs that module alone.
    """
    parser = configparser.ConfigParser()
    read_metadata: dict[str, str] = {}
    try:
        parser.read(descriptor, encoding='utf-8')

        # ⛔ Collected into a LOCAL and committed only once every read has
        # succeeded. Writing straight into ``metadata`` published whatever was
        # read before the failure — a module whose ``name`` parsed and whose
        # ``description`` raised kept the name while losing its dependencies,
        # so it became a valid edge TARGET that declares no outbound edges,
        # under a warning saying it "publishes no name or dependencies". The
        # partial state contradicted the message announcing it.
        for key, field in (('name', 'name'), ('version', 'version'), ('description', 'description')):
            value = parser.get('metadata', key, fallback='').strip()
            if value:
                read_metadata[field] = value

        requires = parser.get('options', 'install_requires', fallback='')
    except (configparser.Error, OSError, UnicodeDecodeError) as exc:
        log_entry(
            'script', 'global', 'WARNING',
            f'[PYTHON-DISCOVER] Unreadable descriptor {descriptor}: {type(exc).__name__}: {exc} — '
            f'the module publishes no name or dependencies, and any edge declared ON it is lost',
        )
        return

    metadata.update(read_metadata)
    for line in requires.splitlines():
        name = requirement_name(line)
        if name:
            dependencies.append(f'{name}:runtime')


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
    skill = 'plan-marshall:build-pyproject:pyproject_build'
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
