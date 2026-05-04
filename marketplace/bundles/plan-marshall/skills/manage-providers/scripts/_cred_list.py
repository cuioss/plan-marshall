"""
List configured credential skills by scanning CREDENTIALS_DIR.

Outputs metadata only — never includes credential values.
"""

import json

from _providers_core import CREDENTIALS_DIR, get_project_name
from file_ops import output_toon  # type: ignore[import-not-found]


def _read_entry(path, scope: str) -> dict | None:
    """Read credential file and return non-secret metadata entry.

    Returns None if the file is not valid JSON.
    """
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None

    skill = data.get('skill') or path.stem
    return {
        'skill': skill,
        'scope': scope,
        'auth_type': data.get('auth_type', 'none'),
        'verified_at': data.get('verified_at', 'never'),
    }


def _scan_dir(directory, scope: str) -> list[dict]:
    """Scan directory for *.json credential files (non-recursive)."""
    if not directory.exists() or not directory.is_dir():
        return []
    entries: list[dict] = []
    for path in sorted(directory.glob('*.json')):
        if not path.is_file():
            continue
        entry = _read_entry(path, scope)
        if entry is not None:
            entries.append(entry)
    return entries


def run_list(args) -> int:
    """Execute the list subcommand."""
    scope = args.scope

    entries: list[dict] = []
    if scope in ('global', 'all'):
        entries.extend(_scan_dir(CREDENTIALS_DIR, 'global'))
    if scope in ('project', 'all'):
        project_name = get_project_name()
        if project_name:
            project_dir = CREDENTIALS_DIR / project_name
            entries.extend(_scan_dir(project_dir, 'project'))

    entries.sort(key=lambda e: (e['scope'], e['skill']))

    output_toon(
        {
            'status': 'success',
            'count': len(entries),
            'credentials': entries,
        }
    )
    return 0
