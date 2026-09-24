#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared preamble for the ``orchestrator store`` test modules.

Holds the module-level loads, constants and helpers the modules beside it
import. The store under test is the per-concern epic ledger — a header
``status.json``, ``resume_anchor.md``, and one ``queue/{PLAN-ID}.json`` per row —
whose layout ``_orchestrator_ledger`` owns. Fixtures seed that layout through the
production module's own writer rather than hand-writing a document, so a layout
change reaches every fixture at once.

Covers:
- create/read/update-field/metadata round-trip under the orchestrator store
  (PLAN_BASE_DIR isolation via plan_context).
- kind=orchestrator header fields written on create, with no queue, anchor or
  ``updated`` key in the header.
- update-field validation: phase enum, workstreams requires a JSON array, the
  queue is not a field, unknown fields rejected.
- the ``legacy_layout`` refusal of a monolithic ``status.json`` on every verb.
- CLI boundary: the ``update-field`` verb and ``--store orchestrator`` flags
  driven through the manage-status.py entry point.
- Default-store regression: plans-store calls remain byte-identical with and
  without the explicit ``--store plans`` flag.
"""

import json
from argparse import Namespace
from pathlib import Path

from conftest import get_script_path, load_script_module

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-status', 'manage-status.py')


_core = load_script_module('plan-marshall', 'manage-status', '_status_core.py', '_status_core_orchestrator')


_ledger = load_script_module('plan-marshall', 'manage-status', '_orchestrator_ledger.py', '_orchestrator_ledger_store')


cmd_orchestrator_create = _core.cmd_orchestrator_create


cmd_orchestrator_read = _core.cmd_orchestrator_read


cmd_orchestrator_update_field = _core.cmd_orchestrator_update_field


cmd_orchestrator_metadata = _core.cmd_orchestrator_metadata


def _create_args(slug: str, title: str = 'Test Epic', force: bool = False) -> Namespace:
    return Namespace(plan_id=slug, title=title, force=force)


def _orchestrator_root(plan_context, slug: str) -> Path:
    return Path(plan_context.fixture_dir) / 'orchestrator' / slug


def _orchestrator_status_file(plan_context, slug: str) -> Path:
    """The epic HEADER ``status.json`` (the queue and the anchor live beside it)."""
    return _orchestrator_root(plan_context, slug) / 'status.json'


def _orchestrator_anchor_file(plan_context, slug: str) -> Path:
    return _orchestrator_root(plan_context, slug) / 'resume_anchor.md'


def _orchestrator_queue_dir(plan_context, slug: str) -> Path:
    return _orchestrator_root(plan_context, slug) / 'queue'


def _read_header(plan_context, slug: str) -> dict:
    header: dict = json.loads(_orchestrator_status_file(plan_context, slug).read_text(encoding='utf-8'))
    return header


def _row(plan_id: str, slug: str, status: str = 'staged', **extra) -> dict:
    """One queue row in the seed shape ``orchestrator queue --add-row`` writes."""
    row = {
        'id': plan_id,
        'slug': slug,
        'workstream': 'WS-01',
        'status': status,
        'plan_marshall_plan_id': '',
        'pr': '',
        'landing': '',
    }
    row.update(extra)
    return row


def _seed_ledger(root: Path, header: dict | None = None, anchor: str = '', rows: tuple = ()) -> None:
    """Materialise a per-concern ledger at ``root`` through the production writer.

    Rows without a ``seq`` take their position in ``rows`` (1-based), which is the
    same rule the monolithic-layout conversion applies.
    """
    seeded_header = {
        'kind': 'orchestrator',
        'title': 'Seeded Epic',
        'phase': 'orchestrating',
        'workstreams': [],
        'metadata': {},
        'created': '2020-01-01T00:00:00Z',
    }
    if header:
        seeded_header.update(header)
    seeded_rows = tuple({'seq': index + 1, **row} for index, row in enumerate(rows))
    _ledger.write_layout(root, seeded_header, anchor, seeded_rows)


def _legacy_document(**overrides) -> dict:
    """A monolithic-layout ``status.json`` document — the shape every verb refuses."""
    document = {
        'kind': 'orchestrator',
        'title': 'Legacy Epic',
        'phase': 'orchestrating',
        'workstreams': [],
        'plans': [],
        'resume_anchor': 'legacy anchor',
        'metadata': {},
        'created': '2020-01-01T00:00:00Z',
        'updated': '2020-01-01T00:00:00Z',
    }
    document.update(overrides)
    return document


def _write_legacy(root: Path, document: dict | None = None) -> Path:
    """Write a monolithic ``status.json`` at ``root`` and return its path."""
    root.mkdir(parents=True, exist_ok=True)
    path = root / 'status.json'
    path.write_text(json.dumps(document or _legacy_document(), indent=2), encoding='utf-8')
    return path
