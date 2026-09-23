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

:func:`write_legacy_status` is the deliberate exception: it writes the retired
monolithic document verbatim, for the ``legacy_layout`` refusal controls and the
negative arms that must reproduce the old layout on purpose.
"""

import json
from collections.abc import Mapping
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
