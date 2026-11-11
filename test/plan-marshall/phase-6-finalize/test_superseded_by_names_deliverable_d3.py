#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""PLAN-LB-133 D3 — ``superseded_by`` must name an existing deliverable.

A ``superseded`` verdict closes a deliverable's frozen criteria, and an
empty-string check was its only guard: any free text closed them. The closing
rule is now the one the two consumers share — the value has to name a
deliverable the outline (the validator) or the frozen snapshot (``open_criteria``)
actually carries. Each behaviour is paired with the nearest input that must
still close the criteria: a value naming a real deliverable.

Both halves drive the real code paths over a sandboxed plan directory; the
validator half also neutralizes the tree-dependent test-integrity leg, which is
covered by its own module.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import _criteria_snapshot as _snap
import pytest
import review_support

PLAN_ID = 'lb133-superseded-by-d3'


def _outline() -> str:
    """Two deliverables, so "names a deliverable" has somewhere to point."""
    return (
        '# Solution: superseded_by names a deliverable\n\n## Summary\n\nFixture plan.\n\n'
        '## Deliverables\n\n'
        '### 1. Deliver the parser\n\n**Affected files:**\n- `src/parser.py` (write-new)\n\n'
        '**Success Criteria:**\n- parser accepts input\n\n'
        '### 2. Deliver the documentation\n\n**Affected files:**\n- `doc/parser.md` (write-new)\n\n'
        '**Success Criteria:**\n- usage is documented\n'
    )


def _plan(plan_context: Any, *, freeze: bool = False) -> Path:
    plan_dir = Path(plan_context.plan_dir_for(PLAN_ID))
    (plan_dir / 'status.json').write_text(
        json.dumps({'title': 'fixture', 'phases': [], 'current_phase': '6-finalize', 'metadata': {}}),
        encoding='utf-8',
    )
    (plan_dir / 'references.json').write_text(json.dumps({'base_branch': 'main'}), encoding='utf-8')
    (plan_dir / 'solution_outline.md').write_text(_outline(), encoding='utf-8')
    if freeze:
        assert _snap.write_snapshot(PLAN_ID)['status'] == 'success'
    return plan_dir


def _verdict(superseded_by: str) -> dict[str, Any]:
    return {
        'deliverables': [
            {'number': 1, 'verdict': 'superseded', 'superseded_by': superseded_by},
            {
                'number': 2,
                'verdict': 'met',
                'criteria': [{'criterion': 'usage is documented', 'status': 'met', 'evidence': ['doc/parser.md:1']}],
            },
        ],
        'unrequested_changes': [],
        'self_reports': [],
        'files_read': ['src/parser.py', 'doc/parser.md'],
    }


def _write_verdict(plan_dir: Path, tmp_path: Path, document: dict[str, Any]) -> str:
    """Seal ``document`` through the reviewer's own verb, then place it in the plan's slot.

    ``open_criteria`` reads a verdict only when its authorship marker matches, so
    the fixture goes through ``run_author_verdict`` rather than writing raw JSON.
    """
    staged = tmp_path / 'verdict.json'
    staged.write_text(json.dumps(document), encoding='utf-8')
    sealed = review_support.run_author_verdict(PLAN_ID, 'functional', str(staged))
    assert sealed['status'] == 'success', sealed
    work = plan_dir / 'work'
    work.mkdir(parents=True, exist_ok=True)
    path = work / 'functional-review-verdict.json'
    path.write_text(staged.read_text(encoding='utf-8'), encoding='utf-8')
    return str(path)


@pytest.fixture(autouse=True)
def _neutral_test_integrity(monkeypatch):
    """Keep the tree-dependent test-integrity leg out of these fixtures."""
    monkeypatch.setattr(
        review_support,
        'compute_test_integrity',
        lambda *_args, **_kwargs: {'status': 'success', 'findings': []},
    )


# --- the validator half -------------------------------------------------------------------


def test_the_validator_names_a_superseded_by_that_is_no_deliverable(plan_context, tmp_path) -> None:
    plan_dir = _plan(plan_context)

    payload = review_support.run_validate(
        PLAN_ID, 'functional', _write_verdict(plan_dir, tmp_path, _verdict('x')), None
    )

    assert payload['valid'] is False, payload
    assert any('superseded_by' in error and 'deliverable 1' in error for error in payload['errors']), payload


def test_the_validator_accepts_a_superseded_by_that_names_a_deliverable(plan_context, tmp_path) -> None:
    plan_dir = _plan(plan_context)

    payload = review_support.run_validate(
        PLAN_ID, 'functional', _write_verdict(plan_dir, tmp_path, _verdict('deliverable 2')), None
    )

    assert payload['errors'] == [], payload
    assert payload['valid'] is True, payload


# --- the open_criteria half ---------------------------------------------------------------


def test_open_criteria_keeps_the_rows_of_an_unnamed_superseded_by(plan_context, tmp_path) -> None:
    """A supersede that names nothing closes nothing, so its criteria stay open."""
    plan_dir = _plan(plan_context, freeze=True)
    _write_verdict(plan_dir, tmp_path, _verdict('x'))

    payload = _snap.open_criteria(PLAN_ID)

    assert payload['open_count'] == 1, payload
    assert payload['open'][0]['deliverable'] == 1, payload


def test_open_criteria_closes_the_rows_of_a_named_superseded_by(plan_context, tmp_path) -> None:
    plan_dir = _plan(plan_context, freeze=True)
    _write_verdict(plan_dir, tmp_path, _verdict('deliverable 2'))

    payload = _snap.open_criteria(PLAN_ID)

    assert payload['open_count'] == 0, payload


# --- the reference must be the value's own citation, not a token inside prose --------------


def test_a_reference_token_inside_prose_does_not_close_the_criteria(plan_context, tmp_path) -> None:
    """Free text that merely CONTAINS ``d1`` is not a citation.

    The value is read as a deliverable reference, so the reference has to stand at
    the head of the value; a stray token in the reviewer's prose would otherwise
    release ungraded work.
    """
    plan_dir = _plan(plan_context, freeze=True)
    _write_verdict(plan_dir, tmp_path, _verdict('see d1 notes'))

    payload = _snap.open_criteria(PLAN_ID)

    assert payload['open_count'] == 1, payload


def test_a_named_reference_may_be_followed_by_stated_prose(plan_context, tmp_path) -> None:
    """Control: the reference first, then the decision a reader needs, still closes."""
    plan_dir = _plan(plan_context, freeze=True)
    _write_verdict(plan_dir, tmp_path, _verdict('deliverable 2 — the operator decision that retired it'))

    payload = _snap.open_criteria(PLAN_ID)

    assert payload['open_count'] == 0, payload


# --- the citation must name a CLOSING successor, not merely a number -----------------------


def _two_row_verdict(first: dict[str, Any], second: dict[str, Any]) -> dict[str, Any]:
    return {'deliverables': [first, second], 'unrequested_changes': [], 'self_reports': [], 'files_read': []}


def test_a_self_citation_leaves_the_criteria_open_and_is_named(plan_context, tmp_path) -> None:
    plan_dir = _plan(plan_context, freeze=True)
    path = _write_verdict(plan_dir, tmp_path, _verdict('D1'))

    payload = _snap.open_criteria(PLAN_ID)
    validated = review_support.run_validate(PLAN_ID, 'functional', path, None)

    assert payload['open_count'] == 1, payload
    assert payload['open'][0]['deliverable'] == 1, payload
    assert any('superseded_by' in error and 'itself' in error for error in validated['errors']), validated


def test_a_supersede_cycle_leaves_both_deliverables_open_and_is_named(plan_context, tmp_path) -> None:
    plan_dir = _plan(plan_context, freeze=True)
    cycle = _two_row_verdict(
        {'number': 1, 'verdict': 'superseded', 'superseded_by': 'D2'},
        {'number': 2, 'verdict': 'superseded', 'superseded_by': 'D1'},
    )
    path = _write_verdict(plan_dir, tmp_path, cycle)

    payload = _snap.open_criteria(PLAN_ID)
    validated = review_support.run_validate(PLAN_ID, 'functional', path, None)

    assert payload['open_count'] == 2, payload
    assert {row['deliverable'] for row in payload['open']} == {1, 2}, payload
    assert any('superseded_by' in error and 'cycle' in error for error in validated['errors']), validated


def test_a_successor_graded_not_met_leaves_the_criteria_open(plan_context, tmp_path) -> None:
    plan_dir = _plan(plan_context, freeze=True)
    path = _write_verdict(
        plan_dir,
        tmp_path,
        _two_row_verdict(
            {'number': 1, 'verdict': 'superseded', 'superseded_by': 'D2'},
            {
                'number': 2,
                'verdict': 'not_met',
                'criteria': [{'criterion': 'usage is documented', 'status': 'not_met', 'evidence': []}],
            },
        ),
    )

    payload = _snap.open_criteria(PLAN_ID)
    validated = review_support.run_validate(PLAN_ID, 'functional', path, None)

    assert any(row['deliverable'] == 1 for row in payload['open']), payload
    assert any(
        'superseded_by' in error and 'not met or met_with_residuals' in error for error in validated['errors']
    ), validated


def test_a_successor_that_is_itself_superseded_is_refused(plan_context, tmp_path) -> None:
    """D2 is superseded by a met D3: D1's citation names an assistant, not a closing successor."""
    plan_dir = _plan(plan_context, freeze=True)
    path = _write_verdict(
        plan_dir,
        tmp_path,
        {
            'deliverables': [
                {'number': 1, 'verdict': 'superseded', 'superseded_by': 'D2'},
                {'number': 2, 'verdict': 'superseded', 'superseded_by': 'D3'},
                {
                    'number': 3,
                    'verdict': 'met',
                    'criteria': [
                        {'criterion': 'usage is documented', 'status': 'met', 'evidence': ['doc/parser.md:1']}
                    ],
                },
            ],
            'unrequested_changes': [],
            'self_reports': [],
            'files_read': [],
        },
    )

    payload = _snap.open_criteria(PLAN_ID)
    validated = review_support.run_validate(PLAN_ID, 'functional', path, None)

    assert any(row['deliverable'] == 1 for row in payload['open']), payload
    assert any('superseded_by' in error and 'itself superseded' in error for error in validated['errors']), validated


@pytest.mark.parametrize(
    'cited',
    ['Deliverable 2', 'Deliverable #2', 'Deliverable D2', '`D2`', '**D2**', '(D2)', 'D2 - the operator decision'],
)
def test_the_natural_reference_spellings_name_a_closing_successor(plan_context, tmp_path, monkeypatch, cited) -> None:
    # The evidence-existence leg is not this clause's subject; the closed criteria are.
    monkeypatch.setattr(review_support, '_main_checkout_root', lambda: None)
    plan_dir = _plan(plan_context, freeze=True)
    path = _write_verdict(plan_dir, tmp_path, _verdict(cited))

    payload = _snap.open_criteria(PLAN_ID)
    validated = review_support.run_validate(PLAN_ID, 'functional', path, None)

    assert payload['open_count'] == 0, payload
    assert validated['errors'] == [], validated


def test_a_refused_spelling_and_a_refused_number_say_different_things(plan_context, tmp_path) -> None:
    """The validator names WHY it refused; the two reasons are not one message."""
    plan_dir = _plan(plan_context)
    unreadable = review_support.run_validate(
        PLAN_ID, 'functional', _write_verdict(plan_dir, tmp_path, _verdict('x')), None
    )
    unknown = review_support.run_validate(
        PLAN_ID, 'functional', _write_verdict(plan_dir, tmp_path, _verdict('D9')), None
    )

    spelling_errors = [error for error in unreadable['errors'] if 'superseded_by' in error]
    number_errors = [error for error in unknown['errors'] if 'superseded_by' in error]
    assert spelling_errors and number_errors, (unreadable, unknown)
    assert spelling_errors != number_errors, (spelling_errors, number_errors)
