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
    # ``main_dirty_files`` is a TOON list field (sorted, ``.plan/``-filtered
    # path set) captured every boundary as the layer-D drift baseline. Its
    # paired drift check lives in ``_handshake_commands._check_main_dirty_drift``
    # and raises ``MainCheckoutDirtiedDuringPlan`` on proper-superset drift
    # against the previous captured row. The scalar ``main_dirty`` column
    # immediately above stays for retrospective summaries (count signal);
    # ``main_dirty_files`` provides the path signal that drives the
    # structured ``main_checkout_dirtied_during_plan`` error payload.
    'main_dirty_files',
    'worktree_sha',
    'worktree_dirty',
    'references_valid',
    'task_state_hash',
    'qgate_open_count',
    'config_hash',
    'unfinished_tasks_count',
    'phase_steps_complete',
    'pending_findings_by_type',
    'pending_findings_blocking_count',
]

# Subset of :data:`HANDSHAKE_FIELDS` that store TOON list values rather
# than scalar strings. Persisting ``''`` for these would round-trip as a
# string and break the dedicated drift-check baselines that consume them
# via :func:`_handshake_commands._coerce_path_list`. New list-typed
# columns should be added here AND to ``HANDSHAKE_FIELDS``; the order in
# ``HANDSHAKE_FIELDS`` controls on-disk column order.
HANDSHAKE_LIST_FIELDS: frozenset[str] = frozenset({'main_dirty_files'})


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
    """Write all rows for ``plan_id`` using the canonical field order.

    Scalar columns default to ``''`` when missing from the row dict
    (preserving the previous on-disk contract for empty / not-applicable
    invariant captures). List-typed columns — currently only
    ``main_dirty_files``, flagged by :data:`HANDSHAKE_LIST_FIELDS` —
    default to ``[]`` so the captured TOON list shape survives the
    round-trip; persisting ``''`` for a list field would round-trip as
    a string and break :func:`_handshake_commands._coerce_path_list`'s
    baseline interpretation downstream.
    """
    path = handshake_path(plan_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized: list[dict[str, Any]] = []
    for row in rows:
        out: dict[str, Any] = {}
        for field in HANDSHAKE_FIELDS:
            if field in HANDSHAKE_LIST_FIELDS:
                value = row.get(field)
                if isinstance(value, list):
                    out[field] = [str(item) for item in value]
                else:
                    out[field] = []
            else:
                out[field] = row.get(field, '')
        normalized.append(out)
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
