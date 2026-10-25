#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Matching by criterion id, and an atomic snapshot rollback.

Two behaviours, each driving the real code path over a sandboxed plan directory:

* a verdict row that carries an explicit ``criterion_id`` answers only the
  criterion that id names — it is never matched by its text against a different
  criterion, and the validator's ``unmatched_criterion`` check names the row the
  gate leaves open;
* a rollback restores the prior snapshot bytes via write-and-replace, so a fault
  injected into that replace cannot silently truncate the snapshot, and a
  ``write_snapshot`` whose digest cannot be recorded puts the prior bytes back.

Every test here is written so it can fail: the fault is injected into the
primitive the fixed code actually calls (``os.replace``), not into a primitive a
regression would reach for.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import _criteria_snapshot as _snap
import plan_logging
import review_support

PLAN_ID = 'lb77-graded-and-rollback-d3'
FROZEN = ['parser rejects garbage', 'parser accepts input']
REWORDED = 'parser rejects garbage input'


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


def test_an_id_bearing_row_whose_text_equals_another_frozen_criterion_is_reported(plan_context) -> None:
    """The gate leaves criterion 1 open AND the validator names the row that caused it.

    The row is graded ``C9`` and its text is criterion 1's frozen text. The gate
    refuses to read it as criterion 1's grade (an explicit id answers only its own
    position), so criterion 1 stays open — and ``report_unmatched_rows`` must say
    WHICH row the freeze could not bind. Before the two predicates agreed, the
    validator matched this row by text, reported nothing, and left the author with
    an open criterion and no finding pointing at it.

    Driven at the validator's own seam. ``run_author_verdict`` refuses an
    out-of-range id when it SEALS a new verdict (``_unknown_criterion_ids``), so a
    verdict carrying this row cannot be author-sealed today; the validator's
    contract is what this asserts, and the two readers of one verdict must agree on
    it. The outline passed in is reworded relative to the freeze so the row's text
    is not a CURRENT criterion, which ``report_unmatched_rows`` excludes as the
    author grading the outline as it now reads.
    """
    _plan(plan_context)
    row = {'criterion': FROZEN[0], 'criterion_id': 'C9', 'status': 'met', 'evidence': ['src/parser.py:2']}
    verdict = {'deliverables': [{'number': 1, 'verdict': 'met', 'criteria': [row]}]}

    assert _snap.verdict_row_matches(row, FROZEN[0], 1, 1) is False
    assert _snap._graded_status([row], FROZEN[0], 1, 1) == 'ungraded'

    grading = review_support.Grading()
    snapshot = _snap.read_snapshot(PLAN_ID)
    assert snapshot is not None
    reported = review_support.report_unmatched_rows(
        grading,
        verdict,
        snapshot,
        [{'number': 1, 'success_criteria': [REWORDED]}],
    )

    assert reported == 1
    assert [(finding['kind'], finding['ref']) for finding in grading.findings] == [('unmatched_criterion', 'D1.C1')]


def test_a_deliverable_qualified_id_answers_only_inside_its_deliverable() -> None:
    """``D1.C2`` answers position 2 of deliverable 1 — and nothing of deliverable 2.

    Driven against the predicate directly so the deliverable arm is exercised
    rather than bypassed: a row whose position matches but whose deliverable does
    not must be refused, while the same row still answers when the caller supplies
    its own deliverable or none at all.
    """
    row = {'criterion': FROZEN[1], 'criterion_id': 'D1.C2', 'status': 'met', 'evidence': ['src/parser.py:2']}

    assert _snap.verdict_row_matches(row, FROZEN[1], 2, 2) is False
    assert _snap.verdict_row_matches(row, FROZEN[1], 2, 1) is True
    assert _snap.verdict_row_matches(row, FROZEN[1], 2, None) is True


def test_a_fault_at_the_atomic_replace_leaves_the_committed_bytes_and_says_so(plan_context, monkeypatch) -> None:
    """The restore is the thing that fails, and the snapshot afterwards is asserted.

    The fault is injected into ``os.replace`` — the primitive the atomic restore
    actually uses — so the restore itself fails: the authorized bytes stay, the
    caller reports that the rollback did NOT complete, and nothing is truncated. A
    regression to a raw ``os.write`` replacement never reaches ``os.replace``, so
    the restore succeeds and this test fails on the bytes it asserts.
    """
    plan_dir = _plan(plan_context)
    snapshot_file = plan_dir / 'work' / 'criteria-snapshot.json'
    before = snapshot_file.read_bytes()
    real_replace = os.replace
    replacements = {'count': 0}

    def _fail_the_second_snapshot_replace(src: Any, dst: Any, *args: Any, **kwargs: Any) -> None:
        if str(dst) == str(snapshot_file):
            replacements['count'] += 1
            if replacements['count'] == 2:
                raise OSError('injected replace failure')
        real_replace(src, dst, *args, **kwargs)

    monkeypatch.setattr(os, 'replace', _fail_the_second_snapshot_replace)
    monkeypatch.setattr(plan_logging, 'log_decision', lambda *args, **kwargs: {'status': 'error', 'error': 'injected'})

    result = _snap.authorize_change(PLAN_ID, 1, FROZEN[0], 'operator: approve the wording')

    assert result['status'] == 'error', result
    assert 'NOT fully rolled back' in result['message']
    assert snapshot_file.read_bytes() != before
    stored = json.loads(snapshot_file.read_text(encoding='utf-8'))
    assert [entry['criterion'] for entry in stored['authorized_changes']] == [FROZEN[0]]
    assert _snap.snapshot_state(PLAN_ID) == 'frozen'


def test_a_write_snapshot_whose_digest_cannot_be_recorded_restores_the_prior_bytes(plan_context, monkeypatch) -> None:
    """The ``write_snapshot``-site rollback is conditional on the bytes it wrote."""
    plan_dir = _plan(plan_context)
    snapshot_file = plan_dir / 'work' / 'criteria-snapshot.json'
    before = snapshot_file.read_bytes()
    assert _snap.authorize_refreeze(PLAN_ID, 'operator: approve the refined criteria')['status'] == 'success'
    (plan_dir / 'solution_outline.md').write_text(_outline([REWORDED, FROZEN[1]]), encoding='utf-8')

    monkeypatch.setattr(_snap, 'record_snapshot_digest', lambda *args, **kwargs: False)

    result = _snap.write_snapshot(PLAN_ID)

    assert result['status'] == 'error', result
    assert result['error'] == 'snapshot_integrity_unrecorded'
    assert snapshot_file.read_bytes() == before
    assert _snap.snapshot_state(PLAN_ID) == 'frozen'
