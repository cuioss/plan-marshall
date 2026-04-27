"""Shared fixture builders for plan-retrospective script tests.

Module-level helpers (not pytest fixtures) so test files can call them
from inside pytest's ``tmp_path`` fixture closures. This avoids introducing
a sibling ``conftest.py`` that would shadow the top-level ``conftest``
module — the existing test tree (see ``test/plan-marshall/manage-lessons``)
never uses sub-conftests.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# The summarize-invariants script now reads ``<plan_dir>/handshakes.toon``
# (canonical phase_handshake storage) instead of ``status.metadata.phase_handshake``.
# Fixtures must materialize that file with the same TOON serialization the
# production code path uses (file_ops.serialize_toon).
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_TOON_DIR = (
    _PROJECT_ROOT
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-files'
    / 'scripts'
)
if str(_TOON_DIR) not in sys.path:
    sys.path.insert(0, str(_TOON_DIR))

from toon_parser import serialize_toon  # type: ignore[import-not-found]  # noqa: E402

# Mirrors HANDSHAKE_FIELDS in
# marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/_handshake_store.py.
# Kept in lock-step on purpose: if the column list drifts, fixtures stop
# matching production rows and the retrospective tests would falsely pass.
_HANDSHAKE_FIELDS = [
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
    'pending_tasks_count',
    'phase_steps_complete',
]


def write_handshakes(plan_dir: Path, plan_id: str, rows: list[dict]) -> Path:
    """Serialize ``rows`` to ``<plan_dir>/handshakes.toon`` in canonical shape.

    Each row is normalized to the full HANDSHAKE_FIELDS schema (missing
    columns become empty strings), matching how
    ``_handshake_store.save_rows`` writes the file in production.
    """
    plan_dir.mkdir(parents=True, exist_ok=True)
    normalized = [
        {field: row.get(field, '') for field in _HANDSHAKE_FIELDS} for row in rows
    ]
    payload = {'plan_id': plan_id, 'handshakes': normalized}
    path = plan_dir / 'handshakes.toon'
    path.write_text(serialize_toon(payload) + '\n', encoding='utf-8')
    return path


_HAPPY_HANDSHAKE_ROWS = [
    {
        'phase': '1-init',
        'captured_at': '2026-04-17T10:00:00Z',
        'worktree_applicable': False,
        'override': False,
        'override_reason': '',
        'main_sha': 'abc123',
        'main_dirty': '0',
        'task_state_hash': 'hash1',
        'qgate_open_count': '0',
        'config_hash': 'cfg1',
        'pending_tasks_count': '0',
        'phase_steps_complete': 'sha-init',
    },
    {
        'phase': '6-finalize',
        'captured_at': '2026-04-17T11:00:00Z',
        'worktree_applicable': False,
        'override': False,
        'override_reason': '',
        'main_sha': 'abc123',
        'main_dirty': '0',
        'task_state_hash': 'hash1',
        'qgate_open_count': '0',
        'config_hash': 'cfg1',
        'pending_tasks_count': '0',
        'phase_steps_complete': 'sha-final',
    },
]

_HAPPY_OUTLINE = """# Solution: Demo
plan_id: demo

## Summary

Demo plan used by plan-retrospective tests.

## Overview

Overview text goes here.

## Deliverables

### 1. Deliverable one

**Affected files:**
- `src/foo.py`
- `src/bar.py`

### 2. Deliverable two

**Affected files:**
- `src/baz.py`
"""

_HAPPY_REFERENCES = {
    # ``check-artifact-consistency.py`` reads ``modified_files`` (the field
    # actually populated by ``manage-references add-file``). The legacy
    # ``affected_files`` key is no longer consulted; the fixture must match
    # the production-shape so the recall check finds the declared files.
    'modified_files': ['src/foo.py', 'src/bar.py', 'src/baz.py'],
    'domains': ['plan-marshall-plugin-dev'],
}

_HAPPY_STATUS = {
    'title': 'Demo',
    'current_phase': 'complete',
    'phases': [
        {'name': '1-init', 'status': 'done'},
        {'name': '2-refine', 'status': 'done'},
        {'name': '3-outline', 'status': 'done'},
        {'name': '4-plan', 'status': 'done'},
        {'name': '5-execute', 'status': 'done'},
        {'name': '6-finalize', 'status': 'done'},
    ],
    # Phase-handshake values now live in ``handshakes.toon`` (canonical
    # storage); ``status.metadata`` only retains row-level context such as
    # ``worktree_path`` for ``expected_invariants`` resolution.
    'metadata': {},
}


def build_happy_plan_dir(plan_dir: Path) -> Path:
    """Populate ``plan_dir`` with a full happy-path plan layout."""
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / 'solution_outline.md').write_text(_HAPPY_OUTLINE, encoding='utf-8')
    (plan_dir / 'references.json').write_text(
        json.dumps(_HAPPY_REFERENCES), encoding='utf-8'
    )
    (plan_dir / 'status.json').write_text(
        json.dumps(_HAPPY_STATUS), encoding='utf-8'
    )
    # Phase-handshake captures now live in handshakes.toon (canonical storage
    # owned by plan-marshall:plan-marshall:phase_handshake). Mirrors the rows
    # the real cmd_capture would have written.
    write_handshakes(
        plan_dir,
        plan_id=plan_dir.name,
        rows=[dict(row) for row in _HAPPY_HANDSHAKE_ROWS],
    )
    (plan_dir / 'metrics.md').write_text('# Metrics\n\ntotal: 100s\n', encoding='utf-8')
    (plan_dir / 'request.md').write_text('Original request\n', encoding='utf-8')

    tasks_dir = plan_dir / 'tasks'
    tasks_dir.mkdir()
    (tasks_dir / 'TASK-001.json').write_text(
        json.dumps({'number': 1, 'deliverable': 1, 'status': 'done'}),
        encoding='utf-8',
    )
    (tasks_dir / 'TASK-002.json').write_text(
        json.dumps({'number': 2, 'deliverable': 2, 'status': 'done'}),
        encoding='utf-8',
    )

    logs_dir = plan_dir / 'logs'
    logs_dir.mkdir()
    # Production log shape emitted by ``manage-logging``:
    # ``[ts] [LEVEL] [hash] [CATEGORY] (caller) msg`` — every bracketed
    # token is required so ``analyze-logs`` extractors are exercised
    # against the real format, not a fixture-only one.
    (logs_dir / 'work.log').write_text(
        '[2026-04-17T10:00:00Z] [INFO] [aaaaaa] [STATUS] '
        '(plan-marshall:phase-1-init) Starting\n'
        '[2026-04-17T10:01:00Z] [INFO] [bbbbbb] [ARTIFACT] '
        '(plan-marshall:phase-3-outline) created\n'
        '[2026-04-17T10:02:00Z] [WARN] [cccccc] [STATUS] '
        '(plan-marshall:phase-5-execute) slow\n',
        encoding='utf-8',
    )
    (logs_dir / 'decision.log').write_text(
        '[2026-04-17T10:00:30Z] [INFO] [dddddd] '
        '(plan-marshall:phase-3-outline) picked option A\n',
        encoding='utf-8',
    )
    # ``manage-logging`` emits to ``script-execution.log`` (not ``script.log``);
    # ``analyze-logs.py`` reads the same filename. The fixture must match so the
    # script_entries / errors_script counters land non-zero.
    (logs_dir / 'script-execution.log').write_text(
        '[2026-04-17T10:00:01Z] [INFO] [eeeeee] '
        'plan-marshall:manage-tasks:manage-tasks add (0.12s)\n'
        '[2026-04-17T10:00:05Z] [INFO] [ffffff] '
        'plan-marshall:manage-status:manage_status read (2.5s)\n'
        '[2026-04-17T10:00:10Z] [ERROR] [111111] '
        'plan-marshall:manage-files:manage-files add (0.05s)\n',
        encoding='utf-8',
    )
    return plan_dir


def build_broken_plan_dir(plan_dir: Path) -> Path:
    """Populate ``plan_dir`` with a fault-injected layout.

    - solution_outline.md lacks Overview and Deliverables sections.
    - status.json has an empty metadata dict (no phase_handshake).
    - No metrics.md, no references.json, no logs/, no tasks/.
    """
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / 'solution_outline.md').write_text(
        '# Solution: Broken\n\n## Summary\n\nBroken plan.\n',
        encoding='utf-8',
    )
    (plan_dir / 'status.json').write_text(
        json.dumps({'metadata': {}}), encoding='utf-8'
    )
    return plan_dir


def setup_live_plan(tmp_path: Path, monkeypatch, plan_id: str = 'retro-happy') -> tuple[str, Path]:
    """Create a happy-path live plan under ``tmp_path`` and set PLAN_BASE_DIR."""
    base = tmp_path / 'base'
    base.mkdir()
    plan_dir = base / 'plans' / plan_id
    build_happy_plan_dir(plan_dir)
    monkeypatch.setenv('PLAN_BASE_DIR', str(base))
    return plan_id, plan_dir


def setup_broken_plan(tmp_path: Path, monkeypatch, plan_id: str = 'retro-broken') -> tuple[str, Path]:
    """Create a fault-injected live plan under ``tmp_path`` and set PLAN_BASE_DIR."""
    base = tmp_path / 'base'
    base.mkdir()
    plan_dir = base / 'plans' / plan_id
    build_broken_plan_dir(plan_dir)
    monkeypatch.setenv('PLAN_BASE_DIR', str(base))
    return plan_id, plan_dir


def setup_archived_plan(tmp_path: Path, name: str = '2026-04-17-retro-happy') -> Path:
    """Create a happy-path archived plan directory under ``tmp_path``."""
    plan_dir = tmp_path / name
    build_happy_plan_dir(plan_dir)
    return plan_dir
