#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared utilities for permission_doctor and permission_fix scripts.

Thin delegators over the platform-runtime layer for settings path-resolution,
JSON load/save, and the default permission set. The runtime
(``claude_runtime.py``) owns all of it — this module owns no settings-path
segments (read preference and write preference alike) and renders no permission
grammar; it forwards to the runtime helpers so there is a single home for that
behaviour and no runtime->script back-import.
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

from claude_runtime import (  # noqa: E402
    _claude_global_settings_path,
    _claude_project_settings_path,
    _claude_project_settings_read_path,
    _load_settings,
    _save_settings,
)
from claude_runtime import (  # noqa: E402
    ensure_default_permissions as _runtime_ensure_default_permissions,
)

# Exit codes
EXIT_SUCCESS = 0


def load_settings(path: str | None) -> tuple[dict, str | None]:
    """Load settings from a JSON file.

    Args:
        path: Path to the settings JSON file. If None, returns empty dict with error.

    Returns:
        Tuple of (settings_dict, error_message). Error is None on success.

    Delegates the actual load to the runtime's ``_load_settings``; this wrapper
    adds the not-found / parse-error string contract the doctor/fix callers
    expect.
    """
    if path is None:
        return {}, 'No settings path provided'

    settings_path = Path(path)

    if not settings_path.exists():
        return {}, f'Settings file not found: {path}'

    data = _load_settings(settings_path)
    if 'error' in data:
        return {}, f'Invalid JSON in {path}: {data["error"]}'
    return data, None


def save_settings(path: str, settings: dict) -> bool:
    """Save settings to a JSON file. Delegates to the runtime's save helper."""
    try:
        return _save_settings(Path(path), settings)
    except TypeError:
        return False


def load_settings_path(path: Path) -> dict[str, Any]:
    """Load settings from a Path, returning defaults if missing.

    Delegates to the runtime's ``_load_settings`` (single home for the
    load behaviour). The runtime returns a defaulted skeleton on a missing or
    malformed file, including an ``error`` key on a JSON parse failure.
    """
    return _load_settings(path)


def get_global_settings_path() -> Path:
    """Get path to global settings file. Delegates to the runtime."""
    return _claude_global_settings_path()


def get_project_settings_path() -> Path:
    """Get path to project settings file (prefers settings.local.json if exists).

    Delegates to the runtime's ``_claude_project_settings_read_path`` — the
    read-side twin of the resolver ``get_project_settings_path_for_write``
    already delegates to, so BOTH preferences live in the single runtime home
    and neither is spelled out here.
    """
    return _claude_project_settings_read_path()


def get_project_settings_path_for_write(project_dir: Path | None = None) -> Path:
    """Get path for writing project settings (prefers settings.json if exists).

    Delegates to the runtime's ``_claude_project_settings_path`` — the single
    home for Claude project settings-path resolution.
    """
    return _claude_project_settings_path(str(project_dir) if project_dir is not None else None)


def ensure_default_permissions(
    settings: dict[str, Any], settings_path: str | Path, dry_run: bool = False
) -> dict[str, Any]:
    """Ensure the target's default permission set, and let the runtime write it.

    Goal-based: the caller states the goal and receives normalized status —
    ``{'defaults_added': [semantic ids], 'defaults_added_count': int,
    'applied': bool}``. The permission grammar is rendered inside the runtime
    and never crosses back, so a caller cannot come to depend on one target's
    permission-string format.
    """
    return _runtime_ensure_default_permissions(settings, Path(settings_path), dry_run)


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
    """
    if scope == 'global':
        return str(get_global_settings_path()), None
    elif scope == 'project':
        return None, str(get_project_settings_path())
    elif scope == 'both':
        return str(get_global_settings_path()), str(get_project_settings_path())
    return None, None
