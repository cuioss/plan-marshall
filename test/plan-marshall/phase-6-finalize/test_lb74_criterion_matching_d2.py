#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""A verdict row answers a frozen criterion only by ``criterion_id`` or exact text.

Four behaviours, each driving the real code path over a sandboxed plan directory:

* a positional fallback no longer closes a criterion: a verdict that answers
  unrelated text leaves the frozen criterion open;
* the validator names a verdict row that matches no frozen criterion by id or
  exact text;
* ``author-verdict`` accepts a ``criterion_id`` on a row and refuses one that
  names no frozen criterion;
* a paraphrased row carrying the criterion's ``C{n}`` id still grades it.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import _criteria_snapshot as _snap
import pytest
import review_support

PLAN_ID = 'lb74-criterion-matching-d2'
FROZEN = ['parser rejects garbage', 'parser accepts input']


@pytest.fixture(autouse=True)
def _no_evidence_tree(monkeypatch):
    """The evidence arm is not this deliverable's subject."""
    monkeypatch.setattr(review_support, '_main_checkout_root', lambda: None)


def _outline(criteria: list[str]) -> str:
    body = '\n'.join(f'- {text}' for text in criteria)
    return (
        '# Solution: criterion matching\n\n## Deliverables\n\n### 1. Deliver the parser\n\n'
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


def _document(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        'deliverables': [{'number': 1, 'verdict': 'met', 'criteria': rows}],
        'unrequested_changes': [],
        'self_reports': [],
        'files_read': ['src/parser.py'],
    }


def _seal(tmp_path: Path, document: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    path = tmp_path / 'verdict.json'
    path.write_text(json.dumps(document), encoding='utf-8')
    result = review_support.run_author_verdict(PLAN_ID, 'functional', str(path))
    return str(path), result


def _seal_into_plan(plan_dir: Path, tmp_path: Path, document: dict[str, Any]) -> None:
    path, result = _seal(tmp_path, document)
    assert result['status'] == 'success', result
    work = plan_dir / 'work'
    work.mkdir(parents=True, exist_ok=True)
    (work / 'functional-review-verdict.json').write_text(Path(path).read_text(encoding='utf-8'), encoding='utf-8')


def test_a_positional_fallback_no_longer_closes_a_criterion(plan_context, tmp_path) -> None:
    plan_dir = _plan(plan_context)
    _seal_into_plan(
        plan_dir,
        tmp_path,
        _document(
            [
                {'criterion': 'parser accepts input', 'status': 'met', 'evidence': ['src/parser.py:1']},
                {'criterion': 'junk input is refused', 'status': 'not_met', 'evidence': []},
            ]
        ),
    )

    payload = _snap.open_criteria(PLAN_ID)

    assert payload['open_count'] == 1, payload
    assert payload['open'][0]['criterion'] == FROZEN[0]


def test_the_validator_names_an_unmatched_verdict_row(plan_context, tmp_path) -> None:
    plan_dir = _plan(plan_context)
    paraphrased = 'the reader refuses junk input'
    _seal_into_plan(
        plan_dir,
        tmp_path,
        _document(
            [
                {'criterion': 'parser accepts input', 'status': 'met', 'evidence': ['src/parser.py:1']},
                {'criterion': paraphrased, 'status': 'met', 'evidence': ['src/parser.py:2']},
            ]
        ),
    )

    payload = review_support.run_validate(
        PLAN_ID, 'functional', str(plan_dir / 'work' / 'functional-review-verdict.json'), None
    )

    unmatched = next((item for item in payload['findings'] if item['kind'] == 'unmatched_criterion'), None)
    assert unmatched is not None, payload['findings']
    assert paraphrased in unmatched['title']
    open_payload = _snap.open_criteria(PLAN_ID)
    assert open_payload['open_count'] == 1, open_payload


def test_author_verdict_accepts_a_criterion_id_on_a_row(plan_context, tmp_path) -> None:
    _plan(plan_context)

    _, result = _seal(
        tmp_path,
        _document(
            [
                {'criterion': 'the reader refuses junk input', 'criterion_id': 'C1', 'status': 'met', 'evidence': []},
                {'criterion': 'parser accepts input', 'status': 'met', 'evidence': []},
            ]
        ),
    )

    assert result['status'] == 'success', result


def test_author_verdict_refuses_a_criterion_id_that_names_no_frozen_criterion(plan_context, tmp_path) -> None:
    _plan(plan_context)

    _, result = _seal(
        tmp_path,
        _document([{'criterion': 'parser accepts input', 'criterion_id': 'C9', 'status': 'met', 'evidence': []}]),
    )

    assert result['status'] == 'error'
    assert result['error'] == 'unknown_criterion_id'


def test_an_authorized_criterion_rewrite_is_not_reported_unmatched(plan_context, tmp_path) -> None:
    plan_dir = _plan(plan_context)
    assert _snap.authorize_change(PLAN_ID, 1, FROZEN[0], 'operator: the gap is refuted')['status'] == 'success'
    (plan_dir / 'solution_outline.md').write_text(_outline(['the reader refuses junk', FROZEN[1]]), encoding='utf-8')
    _seal_into_plan(
        plan_dir,
        tmp_path,
        _document(
            [
                {'criterion': 'the reader refuses junk', 'status': 'met', 'evidence': ['src/parser.py:1']},
                {'criterion': FROZEN[1], 'status': 'met', 'evidence': ['src/parser.py:2']},
            ]
        ),
    )

    payload = review_support.run_validate(
        PLAN_ID, 'functional', str(plan_dir / 'work' / 'functional-review-verdict.json'), None
    )

    assert [item for item in payload['findings'] if item['kind'] == 'unmatched_criterion'] == []
    assert [item for item in payload['findings'] if item['kind'] == 'criterion_rewritten'] == []


def test_a_superseded_deliverables_rows_are_not_reported_unmatched(plan_context, tmp_path) -> None:
    plan_dir = _plan(plan_context)
    _seal_into_plan(
        plan_dir,
        tmp_path,
        {
            'deliverables': [
                {
                    'number': 1,
                    'verdict': 'superseded',
                    'superseded_by': 'operator decision: the deliverable was dropped',
                    'criteria': [{'criterion': 'an unrelated row', 'status': 'not_met', 'evidence': []}],
                }
            ],
            'unrequested_changes': [],
            'self_reports': [],
            'files_read': [],
        },
    )

    payload = review_support.run_validate(
        PLAN_ID, 'functional', str(plan_dir / 'work' / 'functional-review-verdict.json'), None
    )

    assert [item for item in payload['findings'] if item['kind'] == 'unmatched_criterion'] == []


def test_author_verdict_refuses_a_qualified_id_for_another_deliverable(plan_context, tmp_path) -> None:
    _plan(plan_context)

    _, result = _seal(
        tmp_path,
        _document([{'criterion': 'parser accepts input', 'criterion_id': 'D2.C1', 'status': 'met', 'evidence': []}]),
    )

    assert result['status'] == 'error'
    assert result['error'] == 'unknown_criterion_id'


def test_a_qualified_id_answers_only_inside_its_own_deliverable() -> None:
    row = {'criterion': 'anything', 'criterion_id': 'D2.C1'}

    assert _snap.verdict_row_matches(row, 'frozen text', 1, 1) is False
    assert _snap.verdict_row_matches(row, 'frozen text', 1, 2) is True


def test_a_paraphrased_row_carrying_the_id_grades_its_criterion(plan_context, tmp_path) -> None:
    plan_dir = _plan(plan_context)
    _seal_into_plan(
        plan_dir,
        tmp_path,
        _document(
            [
                {
                    'criterion': 'the reader refuses junk input',
                    'criterion_id': 'C1',
                    'status': 'met',
                    'evidence': ['src/parser.py:1'],
                },
                {
                    'criterion': 'the parser takes the input',
                    'criterion_id': 'C2',
                    'status': 'met',
                    'evidence': ['src/parser.py:2'],
                },
            ]
        ),
    )

    payload = _snap.open_criteria(PLAN_ID)

    assert payload['open_count'] == 0, payload
