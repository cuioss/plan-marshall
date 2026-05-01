#!/usr/bin/env python3
"""Manage command handlers for architecture script.

Handles: discover, init, derived, derived-module

Persistence model: per-module on-disk layout under
``.plan/project-architecture/`` consisting of a top-level ``_project.json``
plus per-module ``derived.json``/``enriched.json`` files.
``api_discover()`` writes via the tmp+swap protocol so an interrupted
discover run never leaves a half-written tree behind.
"""

import shutil
from pathlib import Path

from _architecture_core import (
    DataNotFoundError,
    ModuleNotFoundInProjectError,
    _write_json,
    error_result_module_not_found,
    get_data_dir,
    get_module_derived_path,
    get_module_enriched_path,
    get_project_meta_path,
    get_tmp_data_dir,
    iter_modules,
    load_module_derived,
    load_module_enriched,
    load_module_enriched_or_empty,
    load_project_meta,
    require_project_meta_result,
    save_module_derived,
    save_module_enriched,
    save_project_meta,
    swap_data_dir,
)
from constants import (  # type: ignore[import-not-found]
    DIR_PER_MODULE_DERIVED,
    DIR_PER_MODULE_ENRICHED,
    FILE_PROJECT_META,
)

# =============================================================================
# API Functions
# =============================================================================


def _empty_module_enrichment() -> dict:
    """Return the canonical empty-module enrichment dict.

    Shared between ``api_discover`` (which seeds per-module ``enriched.json``
    stubs at discovery time) and ``api_init`` (which fills in the same shape
    for legacy callers).
    """
    return {
        'responsibility': '',
        'responsibility_reasoning': '',
        'purpose': '',
        'purpose_reasoning': '',
        'key_packages': {},
        'internal_dependencies': [],
        'key_dependencies': [],
        'key_dependencies_reasoning': '',
        'skills_by_profile': {},
        'skills_by_profile_reasoning': '',
        'tips': [],
        'insights': [],
        'best_practices': [],
    }


def api_discover(project_dir: str = '.', force: bool = False) -> dict:
    """Run extension API discovery and persist results per-module.

    Writes the entire layout into ``.plan/project-architecture.tmp/`` first,
    then atomically replaces ``.plan/project-architecture/`` with it via
    ``os.replace``. This is the single point of fan-out for the per-module
    layout. ``_project.json`` is the single source of truth for "which modules
    exist"; per-module ``derived.json`` holds the discovery output and
    ``enriched.json`` is seeded as an empty stub so downstream readers can
    treat it as present-by-default.

    Args:
        project_dir: Project directory path
        force: Overwrite existing ``project-architecture/`` tree

    Returns:
        Dict with status, modules_discovered, output_file (the new
        ``_project.json`` path)
    """
    real_dir = get_data_dir(project_dir)
    project_meta_path = get_project_meta_path(project_dir)

    if project_meta_path.exists() and not force:
        return {
            'status': 'exists',
            'file': str(project_meta_path),
            'message': 'Use --force to overwrite',
        }

    # Import extension API for discovery (PYTHONPATH set by executor)
    from extension_discovery import discover_project_modules  # type: ignore[import-not-found]

    project_path = Path(project_dir).resolve()
    result = discover_project_modules(project_path)
    modules: dict[str, dict] = result.get('modules', {}) or {}

    # Build the project-meta document. The ``modules`` index here is the
    # canonical list — clients iterate this, not the per-module directory
    # listing on disk.
    project_meta = {
        'name': project_path.name,
        'description': '',
        'description_reasoning': '',
        'extensions_used': result.get('extensions_used', []),
        'modules': {name: {} for name in sorted(modules.keys())},
    }

    # Stage the entire new layout under .tmp/ so the swap is atomic.
    tmp_dir = get_tmp_data_dir(project_dir)
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True, exist_ok=True)

    # Write _project.json via the shared helper to keep encoding/formatting
    # consistent with non-tmp paths.
    project_meta_tmp = tmp_dir / FILE_PROJECT_META
    _write_json(project_meta_tmp, project_meta)

    # Write per-module derived.json + empty enriched.json stubs via the shared
    # helper so all on-disk JSON in the architecture layout flows through one
    # writer (encoding, indent, key-sort).
    for module_name, module_data in modules.items():
        module_tmp = tmp_dir / module_name
        module_tmp.mkdir(parents=True, exist_ok=True)
        _write_json(module_tmp / DIR_PER_MODULE_DERIVED, module_data)
        _write_json(module_tmp / DIR_PER_MODULE_ENRICHED, _empty_module_enrichment())

    # Atomically swap the staged tree into place.
    swap_data_dir(tmp_dir, project_dir)

    return {
        'status': 'success',
        'modules_discovered': len(modules),
        'output_file': str(real_dir / FILE_PROJECT_META),
    }


def api_init(project_dir: str = '.', check: bool = False, force: bool = False) -> dict:
    """Initialize per-module ``enriched.json`` stubs for every module.

    With the per-module layout, ``api_discover()`` already seeds empty stubs,
    but ``api_init`` is preserved as an explicit-reset / repair entry point.

    Args:
        project_dir: Project directory path
        check: Only report status; do not write
        force: Overwrite existing per-module ``enriched.json`` stubs

    Returns:
        Dict with status and file info
    """
    project_meta_path = get_project_meta_path(project_dir)

    if check:
        if not project_meta_path.exists():
            return {'status': 'missing', 'file': str(project_meta_path)}
        try:
            module_names = iter_modules(project_dir)
        except DataNotFoundError as e:
            return {'status': 'error', 'error': str(e)}
        present = sum(
            1 for name in module_names if get_module_enriched_path(name, project_dir).exists()
        )
        return {
            'status': 'exists',
            'file': str(project_meta_path),
            'modules_enriched': present,
        }

    if not project_meta_path.exists():
        return {
            'status': 'error',
            'error': "Project metadata missing. Run 'architecture.py discover' first.",
        }

    try:
        module_names = iter_modules(project_dir)
    except DataNotFoundError as e:
        return {'status': 'error', 'error': str(e)}

    initialised = 0
    for module_name in module_names:
        path = get_module_enriched_path(module_name, project_dir)
        if path.exists() and not force:
            continue
        save_module_enriched(module_name, _empty_module_enrichment(), project_dir)
        initialised += 1

    return {
        'status': 'success',
        'modules_initialized': initialised,
        'output_file': str(project_meta_path),
    }


def api_get_derived(project_dir: str = '.') -> dict:
    """Get raw discovered data assembled across all modules.

    Re-assembles the legacy ``{project, modules, extensions_used}`` shape from
    the per-module layout so downstream callers (CLI ``derived`` command,
    legacy tooling) continue to receive the dict shape they expect.
    """
    meta = load_project_meta(project_dir)
    modules: dict[str, dict] = {}
    for module_name in iter_modules(project_dir):
        try:
            modules[module_name] = load_module_derived(module_name, project_dir)
        except DataNotFoundError:
            # _project.json lists a module but its derived.json is missing —
            # treat as empty so callers get a stable shape.
            modules[module_name] = {}
    return {
        'project': {
            'name': meta.get('name', ''),
            'description': meta.get('description', ''),
            'description_reasoning': meta.get('description_reasoning', ''),
        },
        'modules': modules,
        'extensions_used': meta.get('extensions_used', []),
    }


def api_get_derived_module(module_name: str, project_dir: str = '.') -> dict:
    """Get raw discovered data for a single module.

    Raises:
        ModuleNotFoundInProjectError: If module not in ``_project.json``
        DataNotFoundError: If ``_project.json`` itself is missing
    """
    available = iter_modules(project_dir)
    if module_name not in available:
        raise ModuleNotFoundInProjectError(f'Module not found: {module_name}', available)
    try:
        return load_module_derived(module_name, project_dir)
    except DataNotFoundError:
        # Module is in the index but its derived.json is gone — surface as
        # missing data, not "module not found".
        raise


def list_modules(project_dir: str = '.') -> list:
    """List module names from ``_project.json``."""
    return iter_modules(project_dir)


# =============================================================================
# CLI Handlers
# =============================================================================


def cmd_discover(args) -> dict:
    """CLI handler for discover command."""
    try:
        return api_discover(args.project_dir, args.force)
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


def cmd_init(args) -> dict:
    """CLI handler for init command."""
    try:
        return api_init(args.project_dir, args.check, args.force)
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


def cmd_derived(args) -> dict:
    """CLI handler for derived command."""
    try:
        derived = api_get_derived(args.project_dir)
        return {'status': 'success', **derived}
    except DataNotFoundError:
        return require_project_meta_result(args.project_dir)
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


def cmd_derived_module(args) -> dict:
    """CLI handler for derived-module command."""
    try:
        module = api_get_derived_module(args.module, args.project_dir)
        return {'status': 'success', 'module_name': args.module, 'module': module}
    except DataNotFoundError:
        return require_project_meta_result(args.project_dir)
    except ModuleNotFoundInProjectError:
        try:
            modules = iter_modules(args.project_dir)
        except Exception:
            modules = []
        return error_result_module_not_found(args.module, modules)
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


# Imports kept at end of file but referenced above; left in place so the
# module-level public surface remains stable for tests that introspect
# ``_cmd_manage`` (e.g. patched callable lookups).
__all__ = [
    'api_discover',
    'api_init',
    'api_get_derived',
    'api_get_derived_module',
    'list_modules',
    'cmd_discover',
    'cmd_init',
    'cmd_derived',
    'cmd_derived_module',
]


# Suppress unused-import lint warnings — a few helpers are imported solely so
# downstream tests can ``from _cmd_manage import ...`` them without bouncing
# through ``_architecture_core``.
_ = (
    get_module_derived_path,
    load_module_enriched,
    load_module_enriched_or_empty,
    save_project_meta,
    save_module_derived,
)
