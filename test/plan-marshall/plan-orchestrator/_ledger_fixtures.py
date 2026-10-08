#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared ledger seeding for the plan-orchestrator test modules.

The epic ledger is per-concern — a header ``status.json``, ``resume_anchor.md``,
and one ``queue/{PLAN-ID}.json`` per row — and ``manage-status``'s
``_orchestrator_ledger`` module owns that layout. Test modules here keep their
fixture dicts in the familiar legacy shape (``{'phase': ..., 'plans': [...],
'resume_anchor': ...}``) because that shape is the one the assembled view hands
back, and :func:`write_ledger` materialises such a dict into the per-concern
files through the PRODUCTION conversion, so a layout change reaches every
fixture at once and no test hand-writes a queue into ``status.json``.

:func:`write_epic_tree` builds a whole epic — header, rows and one spec file per
row — from a compact description, for fixtures that need several epics across
both store roots.

:func:`write_legacy_status` is the deliberate exception: it writes the retired
monolithic document verbatim, for the ``legacy_layout`` refusal controls and the
negative arms that must reproduce the old layout on purpose.
"""

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from conftest import load_script_module

_ledger = load_script_module(
    'plan-marshall', 'manage-status', '_orchestrator_ledger.py', '_orchestrator_ledger_fixtures'
)

#: The layout module itself, for tests that assert through the production reader.
ledger = _ledger


def write_ledger(root: Path, doc: Mapping[str, Any]) -> Path:
    """Materialise a legacy-shaped fixture dict into the per-concern layout at ``root``.

    Every header field in ``doc`` lands in the header ``status.json``, the
    ``resume_anchor`` text in ``resume_anchor.md``, and each ``plans[]`` row in its
    own ``queue/{PLAN-ID}.json`` carrying a ``seq`` taken from its array position
    — the same rule ``orchestrator migrate-layout`` applies. ``updated`` is
    dropped. Returns the header path.

    Raises:
        ValueError: when a ``plans[]`` entry cannot become a row file (a
            non-mapping entry, or an id outside the plan-id grammar). A fixture
            that silently lost a row would test a queue other than the one it
            declares, so the refusal is loud.
    """
    migrated = _ledger.migrate_document(dict(doc))
    if migrated.rejected_rows:
        raise ValueError(f'fixture rows cannot become row files: {list(migrated.rejected_rows)}')
    root.mkdir(parents=True, exist_ok=True)
    _ledger.write_layout(root, migrated.header, migrated.anchor, migrated.rows)
    header_file: Path = _ledger.header_path(root)
    return header_file


def epic_spec_name(plan_id: str, slug: str) -> str:
    """The spec file name :func:`write_epic_tree` writes for ``plan_id`` in epic ``slug``."""
    return f'{plan_id}-{slug}.md'


def write_epic_tree(
    store_root: Path,
    slug: str,
    *,
    phase: str,
    plans: Sequence[tuple[str, str, Sequence[str]]],
) -> Path:
    """Materialise one epic tree under ``store_root`` from a compact description.

    ``store_root`` is the active or the archived orchestrator store root, and
    the epic lands at ``store_root / slug`` with ``phase`` as its header phase.
    Each ``plans`` entry is ``(plan_id, row_status, surface_lines)``: the row is
    seeded through :func:`write_ledger`, and one spec file named by
    :func:`epic_spec_name` is written beside it under ``plans/``, carrying
    ``surface_lines`` as the body of its ``## Expected Surface`` section.

    The builder decides nothing about the population it writes: how many epics,
    which statuses and which surfaces are the caller's. Returns the epic tree.
    """
    epic_dir = store_root / slug
    rows = [
        {
            'id': plan_id,
            'slug': plan_id.lower(),
            'workstream': 'WS-01',
            'status': status,
            'plan_marshall_plan_id': '',
            'pr': '',
            'landing': '',
        }
        for plan_id, status, _ in plans
    ]
    write_ledger(
        epic_dir,
        {
            'kind': 'orchestrator',
            'title': slug,
            'phase': phase,
            'workstreams': ['WS-01'],
            'plans': rows,
            'resume_anchor': 'fixture',
            'metadata': {},
            'created': '2020-01-01T00:00:00Z',
        },
    )
    plans_dir = epic_dir / 'plans'
    plans_dir.mkdir(parents=True, exist_ok=True)
    for plan_id, _, surface_lines in plans:
        lines = [
            f'# {plan_id}: Fixture',
            '',
            '## Objective',
            '',
            'Fixture objective.',
            '',
            '## Claim Labels',
            '',
            '- OBSERVED: a claim — read at `a.py` § `f`',
            '',
            '## Expected Surface',
            '',
            *surface_lines,
        ]
        (plans_dir / epic_spec_name(plan_id, slug)).write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return epic_dir


def write_legacy_status(root: Path, doc: Mapping[str, Any]) -> Path:
    """Write the retired MONOLITHIC ``status.json`` verbatim at ``root``.

    Only the ``legacy_layout`` controls and the negative arms use this: they need
    the old layout on disk precisely to prove it is refused (or, for a negative
    arm, that it collides). Returns the path written.
    """
    root.mkdir(parents=True, exist_ok=True)
    path = root / 'status.json'
    path.write_text(json.dumps(dict(doc), indent=2), encoding='utf-8')
    return path


def read_rows(root: Path) -> list[dict[str, Any]]:
    """The queue rows at ``root`` as the production reader returns them, in ``(seq, id)`` order."""
    return [dict(row) for row in _ledger.read_rows(root).rows]


def read_row(root: Path, plan_id: str) -> dict[str, Any]:
    """One row file, parsed, addressed through the production path resolver."""
    row: dict[str, Any] = json.loads(_ledger.row_path(root, plan_id).read_text(encoding='utf-8'))
    return row
