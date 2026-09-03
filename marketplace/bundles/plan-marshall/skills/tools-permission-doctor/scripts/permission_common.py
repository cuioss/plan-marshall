#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared utilities for permission_doctor and permission_fix scripts.

Thin delegators over the platform-runtime layer for settings path-resolution,
JSON load/save, and the default permission set. The runtime owns all of it —
this module owns no settings-path segments (read preference and write
preference alike) and renders no permission grammar; it forwards to the active
runtime through the registry so there is a single home for that behaviour and
no runtime->script back-import.

Every delegator here resolves its runtime **through the platform-runtime
registry** (``platform_runtime._REGISTRY``), so the implementation honoured is
the one ``runtime.target`` names — Claude on a Claude project, an honest
decline on a non-Claude target. The module holds no direct import of
``claude_runtime``.
"""

import sys
from pathlib import Path
from typing import Any

# Bootstrap sys.path so the platform-runtime library resolves without the
# executor. Walk up to the skills/ root and append platform-runtime/scripts.
for _ancestor in Path(__file__).resolve().parents:
    if _ancestor.name == 'skills' and (_ancestor.parent / '.claude-plugin' / 'plugin.json').is_file():
        _rt_path = str(_ancestor / 'platform-runtime' / 'scripts')
        if _rt_path not in sys.path:
            sys.path.append(_rt_path)
        break

from platform_runtime import _runtime_for_target  # noqa: E402

# Exit codes
EXIT_SUCCESS = 0


def _active_runtime():
    """Resolve the active runtime through the platform-runtime registry.

    Reads ``runtime.target`` from the project's marshal.json like the router
    does, then looks the implementation up in the registry. Raises when the
    target is unknown or the runtime is absent so a caller never silently
    resolves to the wrong implementation.
    """
    return _runtime_for_target()


def load_settings(path: str | None) -> tuple[dict, str | None]:
    """Load settings from a JSON file.

    Args:
        path: Path to the settings JSON file. If None, returns empty dict with error.

    Returns:
        Tuple of (settings_dict, error_message). Error is None on success.

    Delegates the actual load to the active runtime's ``permission_load_settings``;
    this wrapper adds the not-found / parse-error string contract the
    doctor/fix callers expect.
    """
    if path is None:
        return {}, 'No settings path provided'

    settings_path = Path(path)

    if not settings_path.exists():
        return {}, f'Settings file not found: {path}'

    try:
        data = _active_runtime().permission_load_settings(str(settings_path))
    except RuntimeError:
        return {}, f'No permission settings available on this target: {path}'
    if 'error' in data:
        return {}, f'Invalid JSON in {path}: {data["error"]}'
    return data, None


def save_settings(path: str, settings: dict) -> bool:
    """Save settings to a JSON file. Delegates to the active runtime."""
    try:
        return _active_runtime().permission_save_settings(str(Path(path)), settings)
    except (TypeError, RuntimeError):
        return False


def load_settings_path(path: Path) -> dict[str, Any]:
    """Load settings from a Path, returning defaults if missing.

    Delegates to the active runtime's ``permission_load_settings`` (single home
    for the load behaviour). The runtime returns a defaulted skeleton on a
    missing or malformed file, including an ``error`` key on a JSON parse
    failure.
    """
    try:
        return _active_runtime().permission_load_settings(str(path))
    except RuntimeError:
        return {}


def get_global_settings_path() -> Path:
    """Get path to global settings file. Delegates to the active runtime."""
    return Path(_active_runtime().permission_settings_path('global', write=False))


def get_project_settings_path() -> Path:
    """Get path to project settings file (prefers settings.local.json if exists).

    Delegates to the active runtime's read-side path selector — the read-side
    twin of the resolver ``get_project_settings_path_for_write`` already
    delegates to, so BOTH preferences live in the runtime home and neither is
    spelled out here.
    """
    return Path(_active_runtime().permission_settings_path('project', write=False))


def get_project_settings_path_for_write(project_dir: Path | None = None) -> Path:
    """Get path for writing project settings (prefers settings.json if exists).

    Delegates to the active runtime's write-side path selector — the single
    home for project settings-path resolution.
    """
    project_str = str(project_dir) if project_dir is not None else None
    return Path(_active_runtime().permission_settings_path('project', write=True, project_dir=project_str))


def ensure_default_permissions(
    settings: dict[str, Any], settings_path: str | Path, dry_run: bool = False
) -> dict[str, Any]:
    """Ensure the default permission set, and let the runtime write it.

    Goal-based: the caller states the goal and receives normalized status —
    ``{'defaults_added': [semantic ids], 'defaults_added_count': int,
    'defaults_removed': [semantic ids], 'defaults_removed_count': int,
    'applied': bool}``. Ensuring is two-sided: the runtime also prunes rules it
    has retired as defaults. The permission grammar is rendered inside the
    runtime and never crosses back, so a caller cannot come to depend on one
    target's permission-string format — which is why a retirement is reported
    as a semantic id here and explained at the runtime's own declaration.

    The set it ensures is the active target's, not Claude's default — the
    delegation is to the registry runtime, so a non-Claude target either
    returns an honest decline or implements its own default set.
    """
    return _active_runtime().permission_ensure_defaults(
        settings, str(Path(settings_path)), dry_run
    )


def get_settings_path(target: str) -> Path:
    """Get settings path based on target ('global' or 'project')."""
    if target == 'global':
        return get_global_settings_path()
    return get_project_settings_path_for_write()


def resolve_scope_to_paths(scope: str) -> tuple[str | None, str | None]:
    """Resolve scope to global and local settings paths.

    Returns:
        Tuple of (global_path, local_path). For 'global' or 'project' scope,
        one will be None. For 'both', both paths are returned.

    A runtime that declines settings-path resolution (a platform with no
    permission backend, e.g. OpenCode) yields ``(None, None)``: the caller
    then reports the decline through its normal status path instead of letting
    the ``RuntimeError`` escape to the entry point and exit non-zero.
    """
    try:
        if scope == 'global':
            return str(get_global_settings_path()), None
        elif scope == 'project':
            return None, str(get_project_settings_path())
        elif scope == 'both':
            return str(get_global_settings_path()), str(get_project_settings_path())
    except RuntimeError:
        return None, None
    return None, None
