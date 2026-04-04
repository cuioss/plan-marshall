#!/usr/bin/env python3
"""Shared utilities for permission_doctor and permission_fix scripts.

Provides settings loading, path resolution, and exit code constants
used by both read-only analysis and write operations.
"""

import json
from pathlib import Path
from typing import Any

# Exit codes
EXIT_SUCCESS = 0
EXIT_ERROR = 1


def load_settings(path: str | None) -> tuple[dict, str | None]:
    """Load settings from a JSON file.

    Args:
        path: Path to the settings JSON file. If None, returns empty dict with error.

    Returns:
        Tuple of (settings_dict, error_message). Error is None on success.
    """
    if path is None:
        return {}, 'No settings path provided'

    settings_path = Path(path)

    if not settings_path.exists():
        return {}, f'Settings file not found: {path}'

    try:
        with open(settings_path) as f:
            data = json.load(f)

        if 'permissions' not in data:
            data['permissions'] = {}
        for key in ['allow', 'deny', 'ask']:
            if key not in data['permissions']:
                data['permissions'][key] = []

        return data, None
    except json.JSONDecodeError as e:
        return {}, f'Invalid JSON in {path}: {e}'


def save_settings(path: str, settings: dict) -> bool:
    """Save settings to a JSON file."""
    try:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            json.dump(settings, f, indent=2)
        return True
    except Exception:
        return False


def load_settings_path(path: Path) -> dict[str, Any]:
    """Load settings from a Path, returning defaults if missing."""
    if not path.exists():
        return {'permissions': {'allow': [], 'deny': [], 'ask': []}}

    try:
        with open(path) as f:
            data: dict[str, Any] = json.load(f)
        if 'permissions' not in data:
            data['permissions'] = {}
        for key in ['allow', 'deny', 'ask']:
            if key not in data['permissions']:
                data['permissions'][key] = []
        return data
    except json.JSONDecodeError as e:
        return {'error': f'Invalid JSON: {e}', 'permissions': {'allow': [], 'deny': [], 'ask': []}}


def get_global_settings_path() -> Path:
    """Get path to global settings file."""
    return Path.home() / '.claude' / 'settings.json'


def get_project_settings_path() -> Path:
    """Get path to project settings file (prefers settings.local.json if exists)."""
    project_dir = Path.cwd()
    settings_local = project_dir / '.claude' / 'settings.local.json'
    if settings_local.exists():
        return settings_local
    return project_dir / '.claude' / 'settings.json'


def get_project_settings_path_for_write(project_dir: Path | None = None) -> Path:
    """Get path for writing project settings (prefers settings.json if exists)."""
    if project_dir is None:
        project_dir = Path.cwd()

    settings_json = project_dir / '.claude' / 'settings.json'
    if settings_json.exists():
        return settings_json

    return project_dir / '.claude' / 'settings.local.json'


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
