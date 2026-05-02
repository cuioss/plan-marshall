#!/usr/bin/env python3
"""Shared utilities for architecture scripts.

Persists project architecture data using a per-module on-disk layout under
``.plan/project-architecture/``:

- ``_project.json`` — top-level project metadata; the ``modules`` field is the
  single source of truth for "which modules exist". Per-module directory
  presence on disk is NOT a substitute for the index — half-written
  directories must be ignored.
- ``{module}/derived.json`` — deterministic discovery output for one module
  (paths, packages, dependencies).
- ``{module}/enriched.json`` — LLM-augmented fields for one module
  (responsibility, purpose, key_packages, skills_by_profile, …).

Atomic writes use a tmp-then-swap pattern: callers build the new layout under
``project-architecture.tmp/`` and call ``swap_data_dir(tmp_dir)`` which
``os.replace``s it onto the real path. A forced interruption mid-write leaves
either the old layout or the new layout intact, never half-written state.
"""

import json
import os
import shutil
from pathlib import Path
from typing import Any, NoReturn

from constants import (  # type: ignore[import-not-found]
    DIR_ARCHITECTURE,
    DIR_PER_MODULE_DERIVED,
    DIR_PER_MODULE_ENRICHED,
    FILE_PROJECT_META,
)

# Data sub-directory for architecture files (appended to base dir / project_dir)
_ARCHITECTURE_SUBDIR = DIR_ARCHITECTURE

# project-architecture/ lives under the *tracked* .plan/ directory in the repo,
# not the runtime base dir — it is checked in alongside marshal.json.
_TRACKED_CONFIG_SUBDIR = '.plan'

# Tmp suffix used for the atomic tmp+swap protocol on `discover --force`.
_TMP_SUFFIX = '.tmp'


# =============================================================================
# Exceptions
# =============================================================================


class ArchitectureError(Exception):
    """Base exception for architecture errors."""

    pass


class DataNotFoundError(ArchitectureError):
    """Raised when required data files are missing."""

    pass


class ModuleNotFoundInProjectError(ArchitectureError):
    """Raised when a module is not found in the data."""

    pass


class CommandNotFoundError(ArchitectureError):
    """Raised when a command is not found for a module."""

    pass


# =============================================================================
# Path Helpers
# =============================================================================


# Relative sub-path for project-architecture inside a repo checkout. Kept
# relative (not absolute) so callers can compose it with project_dir.
DATA_DIR = Path(_TRACKED_CONFIG_SUBDIR) / _ARCHITECTURE_SUBDIR


def get_data_dir(project_dir: str = '.') -> Path:
    """Get the project-architecture data directory path.

    project-architecture/ lives under the tracked .plan/ directory of the
    repository — the same location as marshal.json. The project_dir
    parameter identifies which repo root to look in (tests pass a tmp dir).
    """
    return Path(project_dir) / DATA_DIR


def get_tmp_data_dir(project_dir: str = '.') -> Path:
    """Get the tmp staging directory used for atomic ``discover --force`` writes.

    Resolves to ``{project_dir}/.plan/project-architecture.tmp/``. Callers build
    the new layout here, then call ``swap_data_dir(tmp_dir)`` to atomically
    replace the real directory.
    """
    real = get_data_dir(project_dir)
    return real.with_name(real.name + _TMP_SUFFIX)


def get_project_meta_path(project_dir: str = '.') -> Path:
    """Path to the top-level ``_project.json`` file."""
    return get_data_dir(project_dir) / FILE_PROJECT_META


def get_module_dir(module_name: str, project_dir: str = '.') -> Path:
    """Path to a module's directory under project-architecture."""
    return get_data_dir(project_dir) / module_name


def get_module_derived_path(module_name: str, project_dir: str = '.') -> Path:
    """Path to a module's ``derived.json``."""
    return get_module_dir(module_name, project_dir) / DIR_PER_MODULE_DERIVED


def get_module_enriched_path(module_name: str, project_dir: str = '.') -> Path:
    """Path to a module's ``enriched.json``."""
    return get_module_dir(module_name, project_dir) / DIR_PER_MODULE_ENRICHED


# =============================================================================
# Load / Save Operations
# =============================================================================


def _read_json(path: Path) -> dict[str, Any]:
    with open(path, encoding='utf-8') as f:
        result: dict[str, Any] = json.load(f)
        return result


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, sort_keys=True)


def load_project_meta(project_dir: str = '.') -> dict[str, Any]:
    """Load ``_project.json`` — the source of truth for module discovery.

    Raises:
        DataNotFoundError: If ``_project.json`` does not exist.
    """
    path = get_project_meta_path(project_dir)
    if not path.exists():
        raise DataNotFoundError(
            f"Project metadata not found. Run 'architecture.py discover' first. Expected: {path}"
        )
    return _read_json(path)


def save_project_meta(meta: dict[str, Any], project_dir: str = '.') -> Path:
    """Save ``_project.json``."""
    path = get_project_meta_path(project_dir)
    _write_json(path, meta)
    return path


def load_module_derived(module_name: str, project_dir: str = '.') -> dict[str, Any]:
    """Load one module's ``derived.json``.

    Raises:
        DataNotFoundError: If the file does not exist.
    """
    path = get_module_derived_path(module_name, project_dir)
    if not path.exists():
        raise DataNotFoundError(
            f"Derived data not found for module '{module_name}'. "
            f"Run 'architecture.py discover' first. Expected: {path}"
        )
    return _read_json(path)


def save_module_derived(module_name: str, data: dict[str, Any], project_dir: str = '.') -> Path:
    """Save one module's ``derived.json``."""
    path = get_module_derived_path(module_name, project_dir)
    _write_json(path, data)
    return path


def load_module_enriched(module_name: str, project_dir: str = '.') -> dict[str, Any]:
    """Load one module's ``enriched.json``.

    Raises:
        DataNotFoundError: If the file does not exist.
    """
    path = get_module_enriched_path(module_name, project_dir)
    if not path.exists():
        raise DataNotFoundError(
            f"Enrichment data not found for module '{module_name}'. "
            f"Run 'architecture.py init' first. Expected: {path}"
        )
    return _read_json(path)


def load_module_enriched_or_empty(module_name: str, project_dir: str = '.') -> dict[str, Any]:
    """Load one module's ``enriched.json`` or return an empty dict.

    Use this when callers want to tolerate missing enrichment (e.g. read paths
    after ``discover`` but before ``init``).
    """
    path = get_module_enriched_path(module_name, project_dir)
    if not path.exists():
        return {}
    return _read_json(path)


def save_module_enriched(module_name: str, data: dict[str, Any], project_dir: str = '.') -> Path:
    """Save one module's ``enriched.json``."""
    path = get_module_enriched_path(module_name, project_dir)
    _write_json(path, data)
    return path


def iter_modules(project_dir: str = '.') -> list[str]:
    """Iterate module names from ``_project.json``'s ``modules`` index.

    The index is the canonical answer to "which modules exist"; per-module
    directory presence on disk is not consulted because half-written
    directories from interrupted writes must be ignored.

    Returns:
        Sorted list of module names. Empty list when the project has no
        modules defined yet.

    Raises:
        DataNotFoundError: If ``_project.json`` does not exist.
    """
    meta = load_project_meta(project_dir)
    modules = meta.get('modules', {}) or {}
    return sorted(modules.keys())


def swap_data_dir(tmp_dir: Path, project_dir: str = '.') -> Path:
    """Atomically replace ``project-architecture/`` with the contents of ``tmp_dir``.

    Implements the tmp-then-swap pattern that gives ``discover --force`` its
    atomicity guarantee: callers build the entire new layout under ``tmp_dir``
    (typically the path returned by ``get_tmp_data_dir()``), then this function
    swaps it into place using a backup-rename so the data directory is never
    absent on disk:

        1. Clean any stale ``project-architecture.old/`` left over from a
           previously interrupted swap.
        2. Rename the existing ``project-architecture/`` to
           ``project-architecture.old/`` (atomic on the same filesystem).
        3. ``os.replace`` ``tmp_dir`` onto the real path.
        4. Delete the backup.

    Compared to the older rmtree-then-replace flow, this closes the window where
    the data directory does not exist on disk: between steps 2 and 3 the backup
    is the canonical layout, and the rename in step 2 is atomic. A forced
    interruption either before, during, or after the rename leaves the project
    in a consistent state — the next ``discover --force`` will pick up the
    leftover ``.old/`` and clean it in step 1.

    Args:
        tmp_dir: Source directory containing the new layout. Must exist.
        project_dir: Project directory path.

    Returns:
        The final ``project-architecture/`` path.

    Raises:
        FileNotFoundError: If ``tmp_dir`` does not exist.
    """
    tmp_dir = Path(tmp_dir)
    if not tmp_dir.exists():
        raise FileNotFoundError(f'tmp data dir does not exist: {tmp_dir}')

    real = get_data_dir(project_dir)
    real.parent.mkdir(parents=True, exist_ok=True)

    backup = real.with_name(real.name + '.old')

    # Step 1: Clean any stale backup left over from a previously interrupted swap.
    if backup.exists():
        shutil.rmtree(backup)

    # Step 2: Move the current layout aside (atomic rename on same filesystem).
    if real.exists():
        os.replace(real, backup)

    # Step 3: Move the staged layout into place.
    os.replace(tmp_dir, real)

    # Step 4: Delete the backup now that the new layout is live.
    if backup.exists():
        shutil.rmtree(backup)

    return real


# =============================================================================
# Module Helpers
# =============================================================================


def get_root_module(project_dir: str = '.') -> str | None:
    """Get the root module name (the module sitting at the project root).

    Determined by:
        1. Module whose ``paths.module`` is ``"."`` or empty (project root).
        2. Fallback: first module in ``_project.json``'s ``modules`` index.

    Returns:
        Module name, or None if the project has no modules.
    """
    try:
        names = iter_modules(project_dir)
    except DataNotFoundError:
        return None
    if not names:
        return None
    for name in names:
        try:
            data = load_module_derived(name, project_dir)
        except DataNotFoundError:
            continue
        paths = data.get('paths', {})
        module_path = paths.get('module', '')
        if module_path in ('.', ''):
            return name
    return names[0]


def merge_module_data(module_name: str, project_dir: str = '.') -> dict[str, Any]:
    """Merge derived and enriched data for a single module.

    Loads ``{module}/derived.json`` and ``{module}/enriched.json`` (the latter
    treated as empty when missing), then overlays enriched fields onto derived
    data. Enriched values that are falsy do NOT overwrite derived values — this
    matches the legacy semantics that downstream callers depend on.

    Raises:
        DataNotFoundError: If ``derived.json`` is missing for the named module.
    """
    derived = load_module_derived(module_name, project_dir)
    enriched = load_module_enriched_or_empty(module_name, project_dir)

    merged = dict(derived)
    for key, value in enriched.items():
        if value:
            merged[key] = value
    return merged


# =============================================================================
# Error Handling
# =============================================================================


def error_exit(message: str, context: dict[str, Any] | None = None) -> 'NoReturn':
    """Print error in TOON format and raise ArchitectureError.

    CLI-boundary helper — only call from command handlers, not library functions.
    For library code, raise ArchitectureError or DataNotFoundError instead.
    """
    from toon_parser import serialize_toon  # type: ignore[import-not-found]

    error_data: dict[str, Any] = {'status': 'error', 'error': 'architecture_error', 'message': message}
    if context:
        error_data.update(context)
    print(serialize_toon(error_data))
    raise ArchitectureError(message)


def error_module_not_found(module_name: str, available: list):
    error_exit('Module not found', {'module': module_name, 'available': available})


def error_command_not_found(module_name: str, command_name: str, available: list):
    error_exit('Command not found', {'module': module_name, 'command': command_name, 'available': available})


def error_data_not_found(expected_file: str, resolution: str):
    error_exit('Data not found', {'expected_file': expected_file, 'resolution': resolution})


def require_project_meta(project_dir: str = '.') -> dict[str, Any]:
    """Load ``_project.json`` or exit with a structured error.

    Convenience wrapper that replaces repeated try/except DataNotFoundError
    blocks in CLI handlers. On success it returns the loaded dict; on failure
    it prints the standard error message and raises ArchitectureError.
    """
    try:
        return load_project_meta(project_dir)
    except DataNotFoundError:
        error_data_not_found(
            str(get_project_meta_path(project_dir)),
            "Run 'architecture.py discover' first",
        )
        raise  # unreachable – error_data_not_found raises ArchitectureError


def handle_module_not_found(module_name: str, project_dir: str) -> int:
    """Print module-not-found error with available modules list and return 1."""
    from toon_parser import serialize_toon  # type: ignore[import-not-found]

    try:
        modules = iter_modules(project_dir)
    except Exception:
        modules = []

    error_data: dict[str, Any] = {
        'status': 'error',
        'error': 'architecture_error',
        'message': 'Module not found',
        'module': module_name,
        'available': modules,
    }
    print(serialize_toon(error_data))
    return 1


def error_result_module_not_found(module_name: str, available: list) -> dict:
    return {
        'status': 'error',
        'error': 'architecture_error',
        'message': 'Module not found',
        'module': module_name,
        'available': available,
    }


def error_result_command_not_found(module_name: str, command_name: str, available: list) -> dict:
    return {
        'status': 'error',
        'error': 'architecture_error',
        'message': 'Command not found',
        'module': module_name,
        'command': command_name,
        'available': available,
    }


def require_project_meta_result(project_dir: str = '.') -> dict:
    """Return ``_project.json`` not found error dict."""
    return {
        'status': 'error',
        'error': 'data_not_found',
        'expected_file': str(get_project_meta_path(project_dir)),
        'resolution': "Run 'architecture.py discover' first",
    }


def handle_module_not_found_result(module_name: str, project_dir: str) -> dict:
    """Return module-not-found error dict with available modules list."""
    try:
        modules = iter_modules(project_dir)
    except Exception:
        modules = []

    return {
        'status': 'error',
        'error': 'architecture_error',
        'message': 'Module not found',
        'module': module_name,
        'available': modules,
    }


def print_skills_by_profile(skills_by_profile: dict) -> None:
    """Print skills_by_profile in TOON format."""
    print('skills_by_profile:')
    for profile, profile_data in skills_by_profile.items():
        print(f'  {profile}:')
        defaults = profile_data.get('defaults', [])
        optionals = profile_data.get('optionals', [])
        if defaults:
            print(f'    defaults[{len(defaults)}]{{skill,description}}:')
            for entry in defaults:
                if isinstance(entry, dict):
                    skill = entry.get('skill', '')
                    desc = entry.get('description', '')
                    print(f'      - {skill},"{desc}"')
                else:
                    print(f'      - {entry}')
        if optionals:
            print(f'    optionals[{len(optionals)}]{{skill,description}}:')
            for entry in optionals:
                if isinstance(entry, dict):
                    skill = entry.get('skill', '')
                    desc = entry.get('description', '')
                    print(f'      - {skill},"{desc}"')
                else:
                    print(f'      - {entry}')
