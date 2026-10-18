#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""PLAN-LB-70 D3 — the seal and the snapshot are bound outside the files they protect.

Four behaviours:

* a verdict edited and re-sealed by recomputing its in-file digest is refused;
* a deleted snapshot on a plan whose status record says "frozen" is refused;
* a re-freeze after a phase rollback without a logged decision is refused;
* a new plan cannot leave ``3-outline`` without a snapshot.

The digests are recorded in the plan's status record by the verb that writes the
artifact; the checks compare against that record.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import _criteria_snapshot as _snap
import _review_support_attribution as _attr
import review_support

from conftest import load_script_module

PLAN_ID = 'lb70-criteria-binding-d3'
_lifecycle = load_script_module('plan-marshall', 'manage-status', '_cmd_lifecycle.py', '_lb70_d3_lifecycle')


def _outline(criteria: list[str]) -> str:
    body = '\n'.join(f'- {text}' for text in criteria)
    return (
        '# Solution: binding\n\n## Deliverables\n\n### 1. Deliver the change\n\n'
        '**Affected files:**\n- `src/parser.py` (write-new)\n\n'
        f'**Success Criteria:**\n{body}\n'
    )


def _status(plan_dir: Path, *, created: str = '2026-10-18T00:00:00+00:00', phase: str = '3-outline') -> None:
    status = {
        'title': 'fixture',
        'phases': [{'name': '3-outline', 'status': 'in_progress'}, {'name': '4-plan', 'status': 'pending'}],
        'current_phase': phase,
        'created': created,
        'metadata': {'use_worktree': False},
    }
    (plan_dir / 'status.json').write_text(json.dumps(status), encoding='utf-8')


def _plan(
    plan_context: Any, criteria: list[str], *, freeze: bool = False, created: str = '2026-10-18T00:00:00+00:00'
) -> Path:
    plan_dir = Path(plan_context.plan_dir_for(PLAN_ID))
    (plan_dir / 'references.json').write_text(json.dumps({'base_branch': 'main'}), encoding='utf-8')
    _status(plan_dir, created=created)
    (plan_dir / 'solution_outline.md').write_text(_outline(criteria), encoding='utf-8')
    if freeze:
        assert _snap.write_snapshot(PLAN_ID)['status'] == 'success'
    return plan_dir


def _verdict(criteria: list[str]) -> dict[str, Any]:
    return {
        'deliverables': [
            {
                'number': 1,
                'verdict': 'met',
                'criteria': [
                    {'criterion': text, 'status': 'met', 'evidence': ['src/parser.py:1']} for text in criteria
                ],
            }
        ],
        'unrequested_changes': [],
        'self_reports': [],
        'files_read': ['src/parser.py'],
    }


def _seal(plan_dir: Path, tmp_path: Path, criteria: list[str]) -> Path:
    path = tmp_path / 'verdict.json'
    path.write_text(json.dumps(_verdict(criteria)), encoding='utf-8')
    assert review_support.run_author_verdict(PLAN_ID, 'functional', str(path))['status'] == 'success'
    return path


# --- D3 (a): a verdict re-sealed by recomputing its in-file digest is refused ---------------


def test_verdict_resealed_by_recomputing_its_digest_is_refused(plan_context, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(_attr, 'resolve_live_worktree', lambda _plan_id: None)
    criteria = ['parser accepts input']
    _plan(plan_context, criteria, freeze=True)
    path = _seal(Path(plan_context.plan_dir_for(PLAN_ID)), tmp_path, criteria)

    edited = json.loads(path.read_text(encoding='utf-8'))
    edited['deliverables'][0]['criteria'][0]['status'] = 'not_met'
    body = {key: value for key, value in edited.items() if key != 'authored'}
    edited['authored']['digest'] = hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    ).hexdigest()
    path.write_text(json.dumps(edited), encoding='utf-8')

    payload = review_support.run_validate(PLAN_ID, 'functional', str(path), None)

    assert payload['valid'] is False
    assert any('modified after the reviewer wrote it' in error for error in payload['errors'])


# --- D3 (b): a deleted snapshot on a frozen plan is refused ---------------------------------


def test_deleted_snapshot_on_a_frozen_plan_is_refused(plan_context, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(_attr, 'resolve_live_worktree', lambda _plan_id: None)
    criteria = ['parser accepts input']
    plan_dir = _plan(plan_context, criteria, freeze=True)
    path = _seal(plan_dir, tmp_path, criteria)
    _snap.snapshot_path(PLAN_ID).unlink()

    payload = review_support.run_validate(PLAN_ID, 'functional', str(path), None)

    assert payload['status'] == 'error'
    assert payload['error'] == 'frozen_snapshot_deleted'


# --- D3 (c): a re-freeze after a phase rollback without a decision is refused ---------------


def test_refreeze_after_set_phase_without_a_decision_is_refused(plan_context, tmp_path) -> None:
    plan_dir = _plan(plan_context, ['parser accepts input'], freeze=True)
    # A phase rollback alone (set-phase 3-outline) does not permit a re-freeze.
    status = json.loads((plan_dir / 'status.json').read_text(encoding='utf-8'))
    status['current_phase'] = '3-outline'
    (plan_dir / 'status.json').write_text(json.dumps(status), encoding='utf-8')

    result = _snap.write_snapshot(PLAN_ID)

    assert result['status'] == 'error'
    assert result['error'] == 'refreeze_requires_decision'


def test_refreeze_with_a_logged_decision_is_allowed(plan_context, tmp_path) -> None:
    _plan(plan_context, ['parser accepts input'], freeze=True)
    assert _snap.authorize_refreeze(PLAN_ID, 'operator: approve the refined criteria')['status'] == 'success'

    assert _snap.write_snapshot(PLAN_ID)['status'] == 'success'


# --- D3 (d): a new plan cannot leave 3-outline without a snapshot ---------------------------


def _transition(monkeypatch: Any, completed: str) -> dict[str, Any]:
    monkeypatch.setattr(_lifecycle, 'assert_finalize_findings_clean', lambda *_a, **_k: 0)
    monkeypatch.setattr(_lifecycle, 'log_entry', lambda *_a, **_k: None)
    monkeypatch.setattr(_lifecycle, '_surface_drive', lambda *_a, **_k: None)
    result = _lifecycle.cmd_transition(
        argparse.Namespace(plan_id=PLAN_ID, completed=completed, allow_bare_transition=False, bare_reason=None)
    )
    assert result is not None
    return result


def test_new_plan_cannot_leave_outline_without_a_snapshot(plan_context, monkeypatch) -> None:
    _plan(plan_context, ['parser accepts input'], created='2026-10-18T00:00:00+00:00')

    result = _transition(monkeypatch, '3-outline')

    assert result['status'] == 'error'
    assert result['error'] == 'outline_snapshot_missing'


def test_legacy_plan_is_exempt_from_the_snapshot_requirement(plan_context, monkeypatch) -> None:
    _plan(plan_context, ['parser accepts input'], created='2020-01-01T00:00:00+00:00')

    result = _transition(monkeypatch, '3-outline')

    assert result['status'] == 'success', result
