#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""PLAN-LB-52 D1 — the criteria are frozen and the verdict is the reviewer's.

Three behaviours, each with the nearest input that must NOT produce a finding:

* an outline whose criterion was NARROWED after approval yields a finding;
* a verdict file EDITED after the review's own verb wrote it is refused;
* a criterion DELETED with no logged operator decision is refused.

The freeze is created by ``manage-solution-outline snapshot-criteria`` (exercised
here through ``_criteria_snapshot.write_snapshot``, the function that verb calls),
and the grading is the same ``review_support.run_validate`` the functional review
runs. Every test drives the real code paths over a sandboxed plan directory.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import _criteria_snapshot as _snap
import _review_support_attribution as _attr
import pytest
import review_support

PLAN_ID = 'criteria-integrity-d1'
TITLE = 'Freeze the criteria'
FROZEN = ['parser accepts input', 'parser rejects garbage']


def _outline(criteria: list[str], extra: list[str] | None = None) -> str:
    """A minimal solution outline whose single deliverable carries ``criteria``."""
    body = '\n'.join(f'- {text}' for text in criteria)
    tail = '\n'.join(f'- {text}' for text in extra or [])
    return (
        '# Solution: criteria integrity\n\n## Summary\n\nFixture plan.\n\n## Deliverables\n\n'
        f'### 1. {TITLE}\n\n**Affected files:**\n- `src/parser.py` (write-new)\n\n'
        f'**Success Criteria:**\n{body}\n{tail}\n'
    )


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


def _plan(plan_context: Any, criteria: list[str], *, freeze_from: list[str] | None = None) -> Path:
    """Write the outline (and, when frozen, the snapshot taken at approval)."""
    plan_dir = plan_context.plan_dir_for(PLAN_ID)
    (plan_dir / 'solution_outline.md').write_text(_outline(criteria), encoding='utf-8')
    (plan_dir / 'references.json').write_text(json.dumps({'base_branch': 'main'}), encoding='utf-8')
    if freeze_from is not None:
        (plan_dir / 'solution_outline.md').write_text(_outline(freeze_from), encoding='utf-8')
        _snap.write_snapshot(PLAN_ID)
        (plan_dir / 'solution_outline.md').write_text(_outline(criteria), encoding='utf-8')
    return plan_dir


def _sealed_verdict(tmp_path: Path, criteria: list[str]) -> str:
    path = tmp_path / 'verdict.json'
    path.write_text(json.dumps(_verdict(criteria)), encoding='utf-8')
    sealed = review_support.run_author_verdict(PLAN_ID, 'functional', str(path))
    assert sealed['status'] == 'success'
    return str(path)


@pytest.fixture
def env(plan_context, monkeypatch):
    """The evidence check stays off here: D1 is about the criteria, not the tree."""
    monkeypatch.setattr(_attr, 'resolve_live_worktree', lambda _plan_id: None)


# --- D1 (a): a criterion narrowed after approval yields a finding --------------------------


def test_narrowed_criterion_yields_a_blocking_finding(env, plan_context, tmp_path) -> None:
    narrowed = ['parser accepts input', 'parser rejects most garbage']
    _plan(plan_context, narrowed, freeze_from=FROZEN)

    payload = review_support.run_validate(PLAN_ID, 'functional', _sealed_verdict(tmp_path, narrowed), None)

    kinds = [(f['kind'], f['ref']) for f in payload['findings']]
    assert ('criterion_rewritten', 'D1') in kinds
    assert payload['may_close'] is False


def test_unchanged_outline_yields_no_criterion_finding(env, plan_context, tmp_path) -> None:
    _plan(plan_context, FROZEN, freeze_from=FROZEN)

    payload = review_support.run_validate(PLAN_ID, 'functional', _sealed_verdict(tmp_path, FROZEN), None)

    assert [f for f in payload['findings'] if f['ref'] == 'D1' and f['kind'].startswith('criterion_')] == []
    assert payload['valid'] is True


# --- D1 (b): a verdict edited after the reviewer wrote it is refused -----------------------


def test_verdict_edited_after_the_review_wrote_it_is_refused(env, plan_context, tmp_path) -> None:
    _plan(plan_context, FROZEN, freeze_from=FROZEN)
    verdict_file = _sealed_verdict(tmp_path, FROZEN)
    edited = json.loads(Path(verdict_file).read_text(encoding='utf-8'))
    edited['deliverables'][0]['criteria'][1]['status'] = 'not_met'
    Path(verdict_file).write_text(json.dumps(edited), encoding='utf-8')

    payload = review_support.run_validate(PLAN_ID, 'functional', verdict_file, None)

    assert payload['valid'] is False
    assert any('modified after the reviewer wrote it' in error for error in payload['errors'])


def test_unedited_sealed_verdict_validates_clean(env, plan_context, tmp_path) -> None:
    _plan(plan_context, FROZEN, freeze_from=FROZEN)

    payload = review_support.run_validate(PLAN_ID, 'functional', _sealed_verdict(tmp_path, FROZEN), None)

    assert payload['valid'] is True
    assert payload['errors'] == []


# --- D1 (c): a deleted criterion with no operator decision is refused ----------------------


def test_deleted_criterion_without_an_operator_decision_is_refused(env, plan_context, tmp_path) -> None:
    _plan(plan_context, FROZEN[:1], freeze_from=FROZEN)

    payload = review_support.run_validate(PLAN_ID, 'functional', _sealed_verdict(tmp_path, FROZEN[:1]), None)

    assert ('criterion_deleted', 'D1') in [(f['kind'], f['ref']) for f in payload['findings']]
    assert payload['may_close'] is False


def test_deleted_criterion_with_a_logged_operator_decision_is_not_refused(env, plan_context, tmp_path) -> None:
    _plan(plan_context, FROZEN[:1], freeze_from=FROZEN)
    recorded = _snap.authorize_change(PLAN_ID, 1, FROZEN[1], 'operator: the gap is refuted, drop the check')
    assert recorded['status'] == 'success'

    payload = review_support.run_validate(PLAN_ID, 'functional', _sealed_verdict(tmp_path, FROZEN[:1]), None)

    assert [f for f in payload['findings'] if f['kind'] == 'criterion_deleted'] == []
    assert payload['valid'] is True
