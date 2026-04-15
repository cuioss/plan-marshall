"""Flat TOON storage for phase handshake captures.

One file per plan at ``<base>/plans/{plan_id}/handshakes.toon`` with one row
per phase. Re-capturing a phase replaces its existing row.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from file_ops import base_path  # type: ignore[import-not-found]
from toon_parser import parse_toon, serialize_toon  # type: ignore[import-not-found]

HANDSHAKE_FILE = 'handshakes.toon'

HANDSHAKE_FIELDS = [
    'phase',
    'captured_at',
    'worktree_applicable',
    'override',
    'override_reason',
    'main_sha',
    'main_dirty',
    'worktree_sha',
    'worktree_dirty',
    'task_state_hash',
    'qgate_open_count',
    'config_hash',
    'phase_steps_complete',
]


def handshake_path(plan_id: str) -> Path:
    return base_path('plans', plan_id, HANDSHAKE_FILE)


def load_rows(plan_id: str) -> list[dict[str, Any]]:
    """Return all handshake rows for ``plan_id`` (empty list if no file)."""
    path = handshake_path(plan_id)
    if not path.exists():
        return []
    try:
        parsed = parse_toon(path.read_text())
    except Exception:
        return []
    rows = parsed.get('handshakes') or []
    if not isinstance(rows, list):
        return []
    return rows


def save_rows(plan_id: str, rows: list[dict[str, Any]]) -> None:
    """Write all rows for ``plan_id`` using the canonical field order."""
    path = handshake_path(plan_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = [
        {field: row.get(field, '') for field in HANDSHAKE_FIELDS} for row in rows
    ]
    payload = {'plan_id': plan_id, 'handshakes': normalized}
    path.write_text(serialize_toon(payload) + '\n')


def upsert_row(plan_id: str, row: dict[str, Any]) -> list[dict[str, Any]]:
    """Replace the row for ``row['phase']`` or append it."""
    rows = load_rows(plan_id)
    phase = row.get('phase')
    rows = [r for r in rows if r.get('phase') != phase]
    rows.append(row)
    save_rows(plan_id, rows)
    return rows


def get_row(plan_id: str, phase: str) -> dict[str, Any] | None:
    for row in load_rows(plan_id):
        if row.get('phase') == phase:
            return row
    return None


def remove_row(plan_id: str, phase: str) -> bool:
    rows = load_rows(plan_id)
    new_rows = [r for r in rows if r.get('phase') != phase]
    if len(new_rows) == len(rows):
        return False
    save_rows(plan_id, new_rows)
    return True
