#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""A missing declared worktree blocks a code review, and a lost digest rolls the snapshot back.

Two behaviours:

* a code review of a plan that DECLARES a worktree which no longer resolves gets a
  blocking ``test_integrity_not_run`` finding and ``may_close: false``, while a
  plan with no worktree keeps the exemption;
* a snapshot whose digest cannot be recorded in the status record is removed
  again, so no frozen snapshot exists without its outside-the-file binding.

Every test drives the real ``run_validate`` / ``write_snapshot`` code paths over a
sandboxed plan directory.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import _criteria_snapshot as _snap
import review_support

PLAN_ID = 'lb74-integrity-d1'
TITLE = 'Freeze the criteria'


def _outline(criteria: list[str]) -> str:
    body = '\n'.join(f'- {text}' for text in criteria)
    return (
        '# Solution: integrity fixes\n\n## Deliverables\n\n'
        f'### 1. {TITLE}\n\n**Affected files:**\n- `src/parser.py` (write-new)\n\n'
        f'**Success Criteria:**\n{body}\n'
    )


def _plan(plan_context: Any, *, use_worktree: bool) -> Path:
    plan_dir = Path(plan_context.plan_dir_for(PLAN_ID))
    status = {
        'title': 'fixture',
        'phases': [{'name': '6-finalize', 'status': 'in_progress'}],
        'current_phase': '6-finalize',
        'metadata': {'use_worktree': use_worktree},
    }
    (plan_dir / 'status.json').write_text(json.dumps(status), encoding='utf-8')
    (plan_dir / 'solution_outline.md').write_text(_outline(['parser accepts input']), encoding='utf-8')
    return plan_dir


def _code_verdict(tmp_path: Path) -> str:
    path = tmp_path / 'code-verdict.json'
    path.write_text(
        json.dumps({'findings': [], 'domains_reviewed': ['python'], 'files_read': ['src/parser.py']}),
        encoding='utf-8',
    )
    return str(path)


def _missing_worktree(plan_id: str) -> dict[str, Any]:
    return {'status': 'error', 'error': 'worktree_unresolved'}


def test_a_missing_declared_worktree_blocks_the_code_review(plan_context, tmp_path, monkeypatch) -> None:
    _plan(plan_context, use_worktree=True)
    monkeypatch.setattr(review_support, 'compute_test_integrity', _missing_worktree)

    payload = review_support.run_validate(PLAN_ID, 'code', _code_verdict(tmp_path), None)

    finding = next((item for item in payload['findings'] if item['kind'] == 'test_integrity_not_run'), None)
    assert finding is not None, payload['findings']
    assert finding['severity'] == 'blocking'
    assert payload['may_close'] is False


def test_a_plan_without_a_worktree_keeps_the_exemption(plan_context, tmp_path, monkeypatch) -> None:
    _plan(plan_context, use_worktree=False)
    monkeypatch.setattr(review_support, 'compute_test_integrity', _missing_worktree)

    payload = review_support.run_validate(PLAN_ID, 'code', _code_verdict(tmp_path), None)

    assert [item for item in payload['findings'] if item['kind'] == 'test_integrity_not_run'] == []


def test_a_scored_snapshot_is_rolled_back_when_the_digest_is_not_recorded(plan_context, monkeypatch) -> None:
    plan_dir = _plan(plan_context, use_worktree=False)
    monkeypatch.setattr(_snap, 'record_integrity', lambda *_args, **_kwargs: False)

    result = _snap.write_snapshot(PLAN_ID)

    assert result['status'] == 'error'
    assert result['error'] == 'snapshot_integrity_unrecorded'
    assert not (plan_dir / 'work' / 'criteria-snapshot.json').exists()
