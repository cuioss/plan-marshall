#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Matching by criterion id, and an atomic snapshot rollback.

Two behaviours, each driving the real code path over a sandboxed plan directory:

* a verdict row that carries an explicit ``criterion_id`` answers only the
  criterion that id names — it is never matched by its text against a different
  criterion;
* a rollback restores the prior snapshot bytes via write-and-replace, so a
  failure injected during that write cannot leave a truncated snapshot behind.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import _criteria_snapshot as _snap
import review_support

PLAN_ID = 'lb77-graded-and-rollback-d3'
FROZEN = ['parser rejects garbage', 'parser accepts input']


def _outline(criteria: list[str]) -> str:
    body = '\n'.join(f'- {text}' for text in criteria)
    return (
        '# Solution: graded status\n\n## Deliverables\n\n### 1. Deliver the parser\n\n'
        '**Affected files:**\n- `src/parser.py` (write-new)\n\n'
        f'**Success Criteria:**\n{body}\n'
    )


def _plan(plan_context: Any) -> Path:
    plan_dir = Path(plan_context.plan_dir_for(PLAN_ID))
    status = {'title': 'fixture', 'phases': [], 'current_phase': '6-finalize', 'metadata': {'use_worktree': False}}
    (plan_dir / 'status.json').write_text(json.dumps(status), encoding='utf-8')
    (plan_dir / 'solution_outline.md').write_text(_outline(FROZEN), encoding='utf-8')
    assert _snap.write_snapshot(PLAN_ID)['status'] == 'success'
    return plan_dir


def _seal_into_plan(plan_dir: Path, tmp_path: Path, rows: list[dict[str, Any]]) -> None:
    document = {
        'deliverables': [{'number': 1, 'verdict': 'met', 'criteria': rows}],
        'unrequested_changes': [],
        'self_reports': [],
        'files_read': ['src/parser.py'],
    }
    path = tmp_path / 'verdict.json'
    path.write_text(json.dumps(document), encoding='utf-8')
    result = review_support.run_author_verdict(PLAN_ID, 'functional', str(path))
    assert result['status'] == 'success', result
    work = plan_dir / 'work'
    work.mkdir(parents=True, exist_ok=True)
    (work / 'functional-review-verdict.json').write_text(path.read_text(encoding='utf-8'), encoding='utf-8')


def _assert_only_the_first_criterion_is_open(payload: dict[str, Any]) -> None:
    assert payload['open_count'] == 1, payload
    assert payload['open'][0]['criterion'] == FROZEN[0]
    assert payload['open'][0]['status'] == 'ungraded'


def test_an_id_qualified_row_does_not_grade_another_criterion_by_text(plan_context, tmp_path) -> None:
    plan_dir = _plan(plan_context)
    _seal_into_plan(
        plan_dir,
        tmp_path,
        [{'criterion': FROZEN[0], 'criterion_id': 'C2', 'status': 'met', 'evidence': ['src/parser.py:2']}],
    )

    _assert_only_the_first_criterion_is_open(_snap.open_criteria(PLAN_ID))


def test_a_deliverable_qualified_id_refused_by_the_id_arm_does_not_match_by_text(plan_context, tmp_path) -> None:
    plan_dir = _plan(plan_context)
    _seal_into_plan(
        plan_dir,
        tmp_path,
        [{'criterion': FROZEN[0], 'criterion_id': 'D1.C2', 'status': 'met', 'evidence': ['src/parser.py:2']}],
    )

    _assert_only_the_first_criterion_is_open(_snap.open_criteria(PLAN_ID))


def test_a_failure_injected_during_the_rollback_write_keeps_the_prior_bytes(plan_context, monkeypatch) -> None:
    """A rollback that fails at the write leaves valid prior bytes, never a truncation.

    The injection sabotages the non-atomic ``Path`` write primitives a regression
    would reach for, truncating the file before raising. The atomic write path
    does not use them, so it completes and the target holds the prior bytes; a
    ``Path.write_bytes``/``write_text`` rollback would leave ``b'{ truncated'``.
    """
    plan_dir = _plan(plan_context)
    snapshot_file = plan_dir / 'work' / 'criteria-snapshot.json'
    before = snapshot_file.read_bytes()

    def _truncate_bytes_then_fail(self: Path, data: bytes) -> int:
        with self.open('wb') as handle:
            handle.write(b'{ truncated')
        raise OSError('injected write failure')

    def _truncate_text_then_fail(self: Path, data: str, *args: Any, **kwargs: Any) -> int:
        with self.open('w', encoding='utf-8') as handle:
            handle.write('{ truncated')
        raise OSError('injected write failure')

    monkeypatch.setattr(Path, 'write_bytes', _truncate_bytes_then_fail)
    monkeypatch.setattr(Path, 'write_text', _truncate_text_then_fail)
    monkeypatch.setattr(_snap, 'record_integrity', lambda *_args, **_kwargs: False)

    result = _snap.authorize_change(PLAN_ID, 1, FROZEN[0], 'operator: approve the wording')

    assert result['status'] == 'error', result
    assert result['error'] == 'snapshot_integrity_unrecorded'
    assert snapshot_file.read_bytes() == before
