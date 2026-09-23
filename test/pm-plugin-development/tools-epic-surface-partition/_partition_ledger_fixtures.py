#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Per-concern epic-ledger fixtures for the epic-surface partition suites.

The partition's lifecycle input is the epic ledger, read through
``manage-status``'s layout owner (``_orchestrator_ledger``). These helpers seed
that ledger through the SAME module's writers — :func:`create_ledger` for the
header and :func:`create_row` for each queue row — so a fixture can never encode
a second model of where the queue lives, and a layout change surfaces here as a
failing fixture rather than as a suite quietly reading a shape production no
longer writes.

Helpers live in this bundle's own test tree and import nothing from
``test/plan-marshall/``. The module name is prefixed so it cannot shadow the
plan-orchestrator suites' ``_ledger_fixtures`` when both trees run in one session.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

# PLAIN import, deliberately — the partition module imports the layout owner the
# same way, so the name is bound once and mypy sees the real module.
import _orchestrator_ledger as ledger_mod

#: The header's ``created`` value. Fixed, so two fixture ledgers built from the
#: same rows are byte-identical and a reproducibility run compares like with like.
FIXTURE_CREATED = '2026-01-01T00:00:00Z'

#: The header's ``title``.
FIXTURE_TITLE = 'fixture epic'


def write_ledger(epic_dir: Path, rows: Mapping[str, object]) -> Path:
    """Seed a per-concern ledger carrying one queue row per ``plan_id -> status``.

    Rows are staged in mapping order, so each one's allocated ``seq`` reproduces
    that order and the assembled view lists them as written. ``status`` is passed
    through untouched, so a fixture can seed a value the vocabulary does not
    cover (or a non-string) and observe the reader's refusal. Returns the header
    path, the one file a reader reports as ``ledger_path``.
    """
    epic_dir.mkdir(parents=True, exist_ok=True)
    ledger_mod.create_ledger(epic_dir, FIXTURE_TITLE, FIXTURE_CREATED)
    for plan_id, status in rows.items():
        outcome = ledger_mod.create_row(epic_dir, {'id': plan_id, 'slug': plan_id.lower(), 'status': status})
        assert 'row' in outcome, f'fixture row {plan_id!r} was not staged: {outcome}'
    return ledger_mod.header_path(epic_dir)


def write_raw_row(epic_dir: Path, plan_id: str, body: str) -> Path:
    """Write one row file's raw text, bypassing the row writer.

    For the controls that need a row the writer would never produce — one with no
    ``id``, one that does not parse, one that is not an object. The path still
    goes through :func:`_orchestrator_ledger.row_path`, so the file lands exactly
    where the reader lists.
    """
    path = ledger_mod.row_path(epic_dir, plan_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding='utf-8')
    return path


def write_raw_header(epic_dir: Path, body: str) -> Path:
    """Write the header's raw text, for the controls on an unreadable header."""
    epic_dir.mkdir(parents=True, exist_ok=True)
    path = ledger_mod.header_path(epic_dir)
    path.write_text(body, encoding='utf-8')
    return path


def write_legacy_ledger(epic_dir: Path, rows: Mapping[str, str]) -> Path:
    """Write a MONOLITHIC-layout ledger: one ``status.json`` carrying ``plans[]``.

    The shape every ledger had before the per-concern split. It exists for the
    one control proving the reader REFUSES that shape rather than reading it, so
    it is the only fixture that writes a ``plans`` array into the header.
    """
    payload = {'plans': [{'id': plan_id, 'status': status} for plan_id, status in rows.items()]}
    return write_raw_header(epic_dir, json.dumps(payload))
