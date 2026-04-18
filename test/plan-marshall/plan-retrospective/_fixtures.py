"""Shared fixture builders for plan-retrospective script tests.

Module-level helpers (not pytest fixtures) so test files can call them
from inside pytest's ``tmp_path`` fixture closures. This avoids introducing
a sibling ``conftest.py`` that would shadow the top-level ``conftest``
module — the existing test tree (see ``test/plan-marshall/manage-lessons``)
never uses sub-conftests.
"""

from __future__ import annotations

import json
from pathlib import Path

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
    'metadata': {
        'phase_handshake': {
            '1-init': {
                'main_sha': 'abc123',
                'main_dirty': '0',
                'task_state_hash': 'hash1',
                'qgate_open_count': '0',
                'config_hash': 'cfg1',
                'phase_steps_complete': 'sha-init',
            },
            '6-finalize': {
                'main_sha': 'abc123',
                'main_dirty': '0',
                'task_state_hash': 'hash1',
                'qgate_open_count': '0',
                'config_hash': 'cfg1',
                'phase_steps_complete': 'sha-final',
            },
        },
    },
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
    (logs_dir / 'work.log').write_text(
        '2026-04-17T10:00:00Z INFO [STATUS] (plan-marshall:phase-1-init) Starting\n'
        '2026-04-17T10:01:00Z INFO [ARTIFACT] (plan-marshall:phase-3-outline) created\n'
        '2026-04-17T10:02:00Z WARN [STATUS] (plan-marshall:phase-5-execute) slow\n',
        encoding='utf-8',
    )
    (logs_dir / 'decision.log').write_text(
        '2026-04-17T10:00:30Z INFO (plan-marshall:phase-3-outline) picked option A\n',
        encoding='utf-8',
    )
    (logs_dir / 'script.log').write_text(
        '2026-04-17T10:00:01Z INFO plan-marshall:manage-tasks:manage-tasks add (0.12s)\n'
        '2026-04-17T10:00:05Z INFO plan-marshall:manage-status:manage_status read (2.5s)\n'
        '2026-04-17T10:00:10Z ERROR plan-marshall:manage-files:manage-files add (0.05s)\n',
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
