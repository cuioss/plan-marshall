#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""PLAN-LB-169 D4 — a retirement carries the operator's OWN retirement decision.

PLAN-LB-163 closed a deliverable on a ``retired`` verdict once every frozen
criterion carried a ``criteria-authorize`` entry. That entry is keyed on the
deliverable and the frozen criterion text, so a decision recorded to approve a
REWRITE of a criterion was indistinguishable from one recorded to retire the
deliverable: the validator returned before grading the current criteria, and the
completion gate closed work no operator retired.

Post-change, an ``authorized_changes`` entry records WHAT the operator decided
(``decision_type``: ``rewrite`` — the default, and the reading of every entry
written before the field existed — or ``retirement``), and ``retirement_state``
reports ``closed`` only when every frozen criterion carries a retirement
decision. Each test below drives the real ``review_support.run_validate`` and
``open_criteria`` paths over a sandboxed plan directory.

The controls at the end are the behaviour that must read exactly as it does at
``main`` ``46d3308ea``: the ``met`` and ``not_met`` paths, the two pre-existing
refusals and the no-criteria refusal.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import _criteria_snapshot as _snap
import _review_support_validate as _validate
import pytest
import review_support

from conftest import load_script_module, parse_ns

_cli = load_script_module(
    'plan-marshall',
    'manage-solution-outline',
    'manage-solution-outline.py',
    module_name='_manage_solution_outline_for_retirement_test',
)

PLAN_ID = 'lb169-retirement-decision-d4'


def _outline(criteria: list[str]) -> str:
    body = '\n'.join(f'- {text}' for text in criteria)
    return (
        '# Solution: retirement decision\n\n## Summary\n\nFixture plan.\n\n## Deliverables\n\n'
        '### 1. Deliver the parser\n\n**Affected files:**\n- `src/parser.py` (write-new)\n\n'
        f'**Success Criteria:**\n{body}\n\n'
        '### 2. Deliver the documentation\n\n**Affected files:**\n- `doc/parser.md` (write-new)\n\n'
        '**Success Criteria:**\n- usage is documented\n'
    )


FROZEN = ['parser accepts input', 'parser rejects garbage']
REWRITTEN = ['parser accepts the input', 'parser rejects the garbage']


def _retirement_outline() -> str:
    """Deliverable 1 carries TWO criteria, so "one without a decision" is a real subset."""
    return _outline(FROZEN)


def _no_criteria_outline() -> str:
    """Deliverable 1 carries an EMPTY success-criteria block: nothing to authorize."""
    return (
        '# Solution: no criteria\n\n## Summary\n\nFixture plan.\n\n## Deliverables\n\n'
        '### 1. Deliver the parser\n\n**Affected files:**\n- `src/parser.py` (write-new)\n\n'
        '**Success Criteria:**\n\n'
        '### 2. Deliver the documentation\n\n**Affected files:**\n- `doc/parser.md` (write-new)\n\n'
        '**Success Criteria:**\n- usage is documented\n'
    )


def _plan(plan_context: Any, outline: str | None = None, *, rewrites: list[str] | None = None) -> Path:
    plan_dir = Path(plan_context.plan_dir_for(PLAN_ID))
    # The freeze binds its digest in the status record, so the plan must have one.
    (plan_dir / 'status.json').write_text(
        json.dumps(
            {
                'title': 'fixture',
                'phases': [{'name': '6-finalize', 'status': 'pending'}],
                'current_phase': '6-finalize',
                'metadata': {'use_worktree': False},
            }
        ),
        encoding='utf-8',
    )
    (plan_dir / 'references.json').write_text(json.dumps({'base_branch': 'main'}), encoding='utf-8')
    (plan_dir / 'solution_outline.md').write_text(
        _retirement_outline() if outline is None else outline, encoding='utf-8'
    )
    assert _snap.write_snapshot(PLAN_ID)['status'] == 'success'
    if rewrites is not None:
        # Freeze first, rewrite the outline after — the shape the defect statement names.
        (plan_dir / 'solution_outline.md').write_text(_outline(rewrites), encoding='utf-8')
    return plan_dir


def _retired_verdict(criteria: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    row: dict[str, Any] = {'number': 1, 'verdict': 'retired'}
    if criteria is not None:
        row['criteria'] = criteria
    return {
        'deliverables': [
            row,
            {
                'number': 2,
                'verdict': 'met',
                'criteria': [{'criterion': 'usage is documented', 'status': 'met', 'evidence': ['doc/parser.md:1']}],
            },
        ],
        'unrequested_changes': [],
        'self_reports': [],
        'files_read': [],
    }


def _write_verdict(plan_dir: Path, tmp_path: Path, document: dict[str, Any]) -> str:
    """Seal ``document`` through the reviewer's own verb, then place it in the plan's slot."""
    staged = tmp_path / 'verdict.json'
    staged.write_text(json.dumps(document), encoding='utf-8')
    sealed = review_support.run_author_verdict(PLAN_ID, 'functional', str(staged))
    assert sealed['status'] == 'success', sealed
    work = plan_dir / 'work'
    work.mkdir(parents=True, exist_ok=True)
    path = work / 'functional-review-verdict.json'
    path.write_text(staged.read_text(encoding='utf-8'), encoding='utf-8')
    return str(path)


def _authorize(number: int, criterion: str, decision_type: str = 'retirement') -> None:
    """Record the operator's decision on one frozen criterion, of ``decision_type``."""
    payload = _snap.authorize_change(
        PLAN_ID, number, criterion, f'operator: {decision_type} decision on {criterion}', decision_type=decision_type
    )
    assert payload['status'] == 'success', payload


def _pre_change_record(number: int, criterion: str) -> None:
    """Append an ``authorized_changes`` entry shaped exactly as records written before this change.

    Those entries carry no ``decision_type`` at all, so the fixture writes the entry
    by hand — the current ``authorize_change`` always records a type — and re-records
    the snapshot digest the way every writer does.
    """
    path = _snap.snapshot_path(PLAN_ID)
    snapshot = json.loads(path.read_text(encoding='utf-8'))
    snapshot['authorized_changes'].append(
        {
            'deliverable': number,
            'criterion': criterion,
            'decision': 'operator: approve the wording',
            'phase': '3-outline',
        }
    )
    path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    assert _snap.record_snapshot_digest(PLAN_ID)


@pytest.fixture(autouse=True)
def _isolate_tree_legs(monkeypatch):
    """Keep the tree-dependent test-integrity and evidence legs out of these fixtures."""
    monkeypatch.setattr(
        review_support,
        'compute_test_integrity',
        lambda *_args, **_kwargs: {'status': 'success', 'findings': []},
    )
    monkeypatch.setattr(review_support, '_main_checkout_root', lambda: None)


# --- D1: a rewrite approval is not a retirement decision -----------------------------------


def test_rewrite_authorizations_do_not_close_a_retired_deliverable(plan_context, tmp_path) -> None:
    """The defect: criteria authorized as rewrites closed a ``retired`` verdict."""
    plan_dir = _plan(plan_context)
    _authorize(1, 'parser accepts input', 'rewrite')
    _authorize(1, 'parser rejects garbage', 'rewrite')
    path = _write_verdict(plan_dir, tmp_path, _retired_verdict())

    payload = review_support.run_validate(PLAN_ID, 'functional', path, None)
    state = _snap.retirement_state(_snap.read_snapshot(PLAN_ID), 1)

    assert payload['valid'] is False, payload
    assert any(
        'retired' in error and 'retirement decision' in error and 'parser accepts input' in error
        for error in payload['errors']
    ), payload
    assert state['state'] == 'unauthorized', state
    assert state['unauthorized'] == ['parser accepts input', 'parser rejects garbage'], state


def test_a_pre_change_authorization_does_not_close_a_retired_deliverable(plan_context, tmp_path) -> None:
    """An entry written before the decision type existed fails closed for ``retired``."""
    plan_dir = _plan(plan_context)
    _pre_change_record(1, 'parser accepts input')
    _pre_change_record(1, 'parser rejects garbage')
    path = _write_verdict(plan_dir, tmp_path, _retired_verdict())

    snapshot = _snap.read_snapshot(PLAN_ID)
    assert snapshot is not None, 'the plan must carry a readable criteria snapshot'
    entries = snapshot['authorized_changes']
    assert all('decision_type' not in entry for entry in entries), entries
    payload = review_support.run_validate(PLAN_ID, 'functional', path, None)
    state = _snap.retirement_state(snapshot, 1)

    assert payload['valid'] is False, payload
    assert state['state'] == 'unauthorized', state
    assert state['unauthorized'] == ['parser accepts input', 'parser rejects garbage'], state


def test_the_defect_input_is_refused_and_the_gate_stays_open(plan_context, tmp_path) -> None:
    """The spec's own input: frozen ``[a, b]`` rewritten to ``[a', b']``, both rewrites authorized.

    The rewrite approvals keep their drift meaning — ``criteria_drift`` reports nothing —
    and they close NOTHING of the retirement: the validator refuses it and the completion
    gate, which never runs the validator, reads both frozen criteria as open.
    """
    plan_dir = _plan(plan_context, rewrites=REWRITTEN)
    _authorize(1, 'parser accepts input', 'rewrite')
    _authorize(1, 'parser rejects garbage', 'rewrite')
    path = _write_verdict(plan_dir, tmp_path, _retired_verdict())

    payload = review_support.run_validate(PLAN_ID, 'functional', path, None)
    criteria = _snap.open_criteria(PLAN_ID)
    drift = _snap.criteria_drift(PLAN_ID)

    assert payload['valid'] is False, payload
    assert drift == [], drift
    assert any('retirement decision' in error for error in payload['errors']), payload
    assert criteria['open_count'] == 2, criteria
    assert {row['criterion'] for row in criteria['open']} == set(FROZEN), criteria
    assert {row['status'] for row in criteria['open']} == {'ungraded'}, criteria


def test_a_retirement_decision_closes_a_retired_deliverable(plan_context, tmp_path) -> None:
    """The operator's own retirement decision per criterion still closes it, as before."""
    plan_dir = _plan(plan_context)
    _authorize(1, 'parser accepts input', 'retirement')
    _authorize(1, 'parser rejects garbage', 'retirement')
    path = _write_verdict(plan_dir, tmp_path, _retired_verdict())

    payload = review_support.run_validate(PLAN_ID, 'functional', path, None)
    criteria = _snap.open_criteria(PLAN_ID)

    assert payload['errors'] == [], payload
    assert payload['valid'] is True, payload
    assert [finding for finding in payload['findings'] if finding['kind'] == 'deliverable_not_met'] == [], payload
    assert criteria['open_count'] == 0, criteria


def test_a_mixed_record_is_refused_naming_only_the_rewrite_criterion(plan_context, tmp_path) -> None:
    """One retirement and one rewrite: the criterion without a retirement decision is named."""
    plan_dir = _plan(plan_context)
    _authorize(1, 'parser accepts input', 'retirement')
    _authorize(1, 'parser rejects garbage', 'rewrite')
    path = _write_verdict(plan_dir, tmp_path, _retired_verdict())

    payload = review_support.run_validate(PLAN_ID, 'functional', path, None)
    state = _snap.retirement_state(_snap.read_snapshot(PLAN_ID), 1)
    criteria = _snap.open_criteria(PLAN_ID)

    assert payload['valid'] is False, payload
    refusal = next(error for error in payload['errors'] if 'retired' in error)
    assert 'parser rejects garbage' in refusal, payload
    assert 'parser accepts input' not in refusal, payload
    assert state['state'] == 'unauthorized', state
    assert state['unauthorized'] == ['parser rejects garbage'], state
    # A criterion the operator DID record a retirement decision for closes on that
    # decision; the one behind a rewrite stays open.
    assert criteria['open_count'] == 1, criteria
    assert criteria['open'][0]['criterion'] == 'parser rejects garbage', criteria


def test_a_rewrite_authorization_closes_nothing_in_the_gate(plan_context, tmp_path) -> None:
    """The gate re-derives the one predicate; it holds no second, type-blind reading.

    ``open_criteria`` asks whether each criterion carries a RETIREMENT decision, not
    whether it carries any decision, so a rewrite authorization leaves both open.
    """
    plan_dir = _plan(plan_context)
    _authorize(1, 'parser accepts input', 'rewrite')
    _authorize(1, 'parser rejects garbage', 'rewrite')
    _write_verdict(plan_dir, tmp_path, _retired_verdict())

    criteria = _snap.open_criteria(PLAN_ID)
    state = _snap.retirement_state(_snap.read_snapshot(PLAN_ID), 1)

    assert state['state'] == 'unauthorized', state
    assert criteria['open_count'] == 2, criteria
    assert {row['criterion'] for row in criteria['open']} == set(FROZEN), criteria
    assert {row['status'] for row in criteria['open']} == {'ungraded'}, criteria


# --- D2: a refused retirement grades the current criteria and closes nothing ---------------


def test_a_refused_retirement_still_grades_the_criteria_its_row_carries(plan_context, tmp_path) -> None:
    """The refused row does not short-circuit grading: its ``met`` claim is checked."""
    plan_dir = _plan(plan_context)
    _authorize(1, 'parser accepts input', 'rewrite')
    _authorize(1, 'parser rejects garbage', 'rewrite')
    path = _write_verdict(
        plan_dir, tmp_path, _retired_verdict([{'criterion': 'parser accepts input', 'status': 'met', 'evidence': []}])
    )

    payload = review_support.run_validate(PLAN_ID, 'functional', path, None)

    assert payload['valid'] is False, payload
    # The met -> unevidenced rewrite is produced by ``_grade_criteria`` alone, so its
    # presence is what shows the refused retirement did not return before grading.
    assert {'deliverable': 1, 'criterion': 1, 'from': 'met', 'to': 'unevidenced'} in payload['rewrites'], payload


def test_a_refused_retirement_carrying_no_grades_is_reported_ungraded(plan_context, tmp_path) -> None:
    """The defect's own row shape — ``{number: 1, verdict: retired}`` — is graded, not skipped."""
    plan_dir = _plan(plan_context)
    _authorize(1, 'parser accepts input', 'rewrite')
    _authorize(1, 'parser rejects garbage', 'rewrite')
    path = _write_verdict(plan_dir, tmp_path, _retired_verdict())

    payload = review_support.run_validate(PLAN_ID, 'functional', path, None)

    assert payload['valid'] is False, payload
    assert any('0 criteria rows' in error for error in payload['errors']), payload


def test_a_refused_retirement_with_no_grades_is_reported_even_with_no_outline_criteria(plan_context, tmp_path) -> None:
    """The empty-grading diagnostic does not depend on the outline's criterion count.

    With no current criteria the count check has nothing to compare against, so the row
    carrying none would otherwise be refused without ever saying that it grades nothing.
    """
    plan_dir = _plan(plan_context, rewrites=[])
    _authorize(1, 'parser accepts input', 'rewrite')
    _authorize(1, 'parser rejects garbage', 'rewrite')
    path = _write_verdict(plan_dir, tmp_path, _retired_verdict())

    payload = review_support.run_validate(PLAN_ID, 'functional', path, None)

    assert payload['valid'] is False, payload
    assert any('no criterion grades' in error for error in payload['errors']), payload


def test_an_unsealed_verdict_closes_nothing_on_a_rewrite_authorization(plan_context, tmp_path) -> None:
    """An edited verdict is untrusted: the gate must not fall back to the rewrite path.

    Removing the authorship marker turns the sealed verdict into an unsealed one, so the
    gate cannot read that the deliverable was retired — and must not let the more
    permissive rewrite exemption close what the retirement rule left open.
    """
    plan_dir = _plan(plan_context)
    _authorize(1, 'parser accepts input', 'rewrite')
    _authorize(1, 'parser rejects garbage', 'rewrite')
    path = Path(_write_verdict(plan_dir, tmp_path, _retired_verdict()))
    document = json.loads(path.read_text(encoding='utf-8'))
    document.pop(_snap.AUTHORED_KEY, None)
    path.write_text(json.dumps(document), encoding='utf-8')

    criteria = _snap.open_criteria(PLAN_ID)

    assert criteria['verdict_state'] == 'unsealed', criteria
    # Fail closed across the whole verdict: deliverable 1's two criteria AND deliverable
    # 2's one read open, because the document that graded them is no longer trustworthy.
    assert criteria['open_count'] == 3, criteria
    assert {row['criterion'] for row in criteria['open']} >= set(FROZEN), criteria


# --- controls: unchanged from ``main`` ``46d3308ea`` ---------------------------------------


def test_a_met_row_still_passes(plan_context, tmp_path, monkeypatch) -> None:
    """CONTROL: the ``met`` path is untouched by the retirement decision."""
    plan_dir = _plan(plan_context)
    path = _write_verdict(
        plan_dir,
        tmp_path,
        {
            'deliverables': [
                {
                    'number': 1,
                    'verdict': 'met',
                    'criteria': [
                        {'criterion': 'parser accepts input', 'status': 'met', 'evidence': ['src/parser.py:1']},
                        {'criterion': 'parser rejects garbage', 'status': 'met', 'evidence': ['src/parser.py:2']},
                    ],
                },
                {
                    'number': 2,
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

    payload = review_support.run_validate(PLAN_ID, 'functional', path, None)

    assert payload['errors'] == [], payload
    assert payload['valid'] is True, payload


def test_a_not_met_row_still_files_its_deliverable_row(plan_context, tmp_path) -> None:
    """CONTROL: the ``not_met`` path is untouched by the retirement decision."""
    plan_dir = _plan(plan_context)
    path = _write_verdict(
        plan_dir,
        tmp_path,
        {
            'deliverables': [
                {
                    'number': 1,
                    'verdict': 'not_met',
                    'criteria': [
                        {'criterion': 'parser accepts input', 'status': 'met', 'evidence': ['src/parser.py:1']},
                        {'criterion': 'parser rejects garbage', 'status': 'not_met', 'evidence': []},
                    ],
                },
                {
                    'number': 2,
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

    payload = review_support.run_validate(PLAN_ID, 'functional', path, None)

    assert any(finding['kind'] == 'deliverable_not_met' for finding in payload['findings']), payload


def test_a_retired_row_with_one_unrecorded_criterion_is_still_refused(plan_context, tmp_path) -> None:
    """CONTROL: the pre-existing ``unauthorized`` refusal names the criterion.

    The authorized criterion is recorded WITHOUT a decision type — the shape every
    record has at ``main`` ``46d3308ea`` — so this control exercises the refusal on
    both trees and pins that the refusal still names the criterion that is missing.
    """
    plan_dir = _plan(plan_context)
    _pre_change_record(1, 'parser accepts input')
    path = _write_verdict(plan_dir, tmp_path, _retired_verdict())

    payload = review_support.run_validate(PLAN_ID, 'functional', path, None)

    assert payload['valid'] is False, payload
    assert any('retired' in error and 'parser rejects garbage' in error for error in payload['errors']), payload


def test_a_retired_row_with_no_criteria_to_authorize_is_still_refused(plan_context, tmp_path) -> None:
    """CONTROL: the pre-existing no-criteria refusal is unchanged."""
    plan_dir = _plan(plan_context, _no_criteria_outline())
    path = _write_verdict(plan_dir, tmp_path, _retired_verdict())

    payload = review_support.run_validate(PLAN_ID, 'functional', path, None)

    assert payload['valid'] is False, payload
    assert any('retired' in error and 'nothing to authorize' in error for error in payload['errors']), payload


# --- D3: the edges the PLAN-LB-169 and PLAN-LB-163 landings recorded -----------------------


def test_an_absent_verdict_closes_nothing_on_a_rewrite_authorization(plan_context) -> None:
    """No verdict grades anything, so no decision exemption may close a criterion.

    An unsealed verdict already refused the exemption; a DELETED verdict took the more
    permissive path because its state was not read as untrusted.
    """
    _plan(plan_context)
    _authorize(1, 'parser accepts input', 'rewrite')
    _authorize(1, 'parser rejects garbage', 'rewrite')

    criteria = _snap.open_criteria(PLAN_ID)

    assert criteria['verdict_state'] == 'absent', criteria
    assert criteria['open_count'] == 3, criteria


def test_the_decision_type_invalid_branch_is_refused_before_the_guard(plan_context) -> None:
    """An unknown decision type is refused rather than recorded as an untyped entry."""
    _plan(plan_context)

    payload = _snap.authorize_change(PLAN_ID, 1, 'parser accepts input', 'operator: bogus', decision_type='bogus')

    assert (payload['status'], payload['error']) == ('error', 'decision_type_invalid'), payload


def test_the_decision_type_flag_reaches_the_commit_through_the_parser(plan_context) -> None:
    """``--decision-type`` is parsed by the real CLI, echoed, and recorded on the entry."""
    _plan(plan_context)
    namespace = parse_ns(
        'plan-marshall',
        'manage-solution-outline',
        'manage-solution-outline.py',
        'criteria-authorize',
        '--plan-id',
        PLAN_ID,
        '--deliverable-number',
        '1',
        '--criterion',
        'parser accepts input',
        '--decision',
        'operator: retire the deliverable',
        '--decision-type',
        'retirement',
        register=False,
    )

    assert namespace.decision_type == 'retirement'
    payload = _cli.cmd_criteria_authorize(namespace)

    assert (payload['status'], payload['decision_type']) == ('success', 'retirement'), payload
    snapshot = _snap.read_snapshot(PLAN_ID)
    assert snapshot is not None
    entries = [entry for entry in snapshot['authorized_changes'] if entry['criterion'] == 'parser accepts input']
    assert entries and entries[-1]['decision_type'] == 'retirement', snapshot['authorized_changes']


def test_a_rewrite_never_downgrades_a_retirement_decision(plan_context) -> None:
    """A later rewrite would replace the operator's retirement and is refused."""
    _plan(plan_context)
    _authorize(1, 'parser accepts input', 'retirement')

    payload = _snap.authorize_change(
        PLAN_ID, 1, 'parser accepts input', 'operator: rewrite it again', decision_type='rewrite'
    )

    assert (payload['status'], payload['error']) == ('error', 'retirement_decision_downgraded'), payload
    snapshot = _snap.read_snapshot(PLAN_ID)
    assert snapshot is not None
    assert [entry['decision_type'] for entry in snapshot['authorized_changes']] == ['retirement']


def test_a_retirement_supersedes_an_earlier_rewrite_decision(plan_context) -> None:
    """Matched control: the opposite direction is an update, and it is recorded."""
    _plan(plan_context)
    _authorize(1, 'parser accepts input', 'rewrite')

    payload = _snap.authorize_change(
        PLAN_ID, 1, 'parser accepts input', 'operator: retire instead', decision_type='retirement'
    )

    assert payload['status'] == 'success', payload
    snapshot = _snap.read_snapshot(PLAN_ID)
    assert snapshot is not None
    assert [entry['decision_type'] for entry in snapshot['authorized_changes']] == ['retirement']


def test_a_non_list_criteria_on_a_refused_retired_row_keeps_its_shape_error(plan_context, tmp_path) -> None:
    """A malformed ``criteria`` is named as malformed, not coerced into the vague refusal."""
    plan_dir = _plan(plan_context)
    _authorize(1, 'parser accepts input', 'rewrite')
    _authorize(1, 'parser rejects garbage', 'rewrite')
    document = _retired_verdict()
    document['deliverables'][0]['criteria'] = {'criterion': 'parser accepts input'}
    path = _write_verdict(plan_dir, tmp_path, document)

    payload = review_support.run_validate(PLAN_ID, 'functional', path, None)

    assert payload['valid'] is False, payload
    assert any('criteria must be a list' in error for error in payload['errors']), payload


def test_a_refused_retirement_publishes_the_rows_grading_findings(plan_context, tmp_path) -> None:
    """An invalid verdict still publishes the findings its graded rows produced."""
    plan_dir = _plan(plan_context)
    _authorize(1, 'parser accepts input', 'rewrite')
    _authorize(1, 'parser rejects garbage', 'rewrite')
    document = _retired_verdict([{'criterion': 'parser accepts input', 'status': 'met', 'evidence': []}])
    document['unrequested_changes'] = [
        {'path': 'src/extra.py', 'reason': 'unasked', 'consequential': True, 'fix_kind': 'implementation'}
    ]
    path = _write_verdict(plan_dir, tmp_path, document)

    payload = review_support.run_validate(PLAN_ID, 'functional', path, None)

    assert payload['valid'] is False, payload
    assert any(finding['kind'] == 'unrequested_change' for finding in payload['findings']), payload


def test_the_unrecordable_retirement_states_carry_their_own_code(plan_context) -> None:
    """``no_snapshot`` and ``no_deliverable`` name themselves instead of reusing no_criteria."""
    _plan(plan_context)
    snapshot = _snap.read_snapshot(PLAN_ID)
    assert snapshot is not None

    assert _snap.retirement_state(None, 1)['state'] == _snap.RETIREMENT_NO_SNAPSHOT
    assert _snap.retirement_state(snapshot, 99)['state'] == _snap.RETIREMENT_NO_DELIVERABLE
    for state, code in (
        (_snap.RETIREMENT_NO_SNAPSHOT, 'no_snapshot'),
        (_snap.RETIREMENT_NO_DELIVERABLE, 'no_deliverable'),
        (_snap.RETIREMENT_NO_CRITERIA, 'nothing to authorize'),
    ):
        assert code in _validate._retirement_refusal('deliverable 1', state, 1), state


def test_a_retired_deliverables_criteria_no_longer_cover_a_spec_clause() -> None:
    """A retirement must not silently retire the spec clause those criteria stood in for."""
    snapshot = {'spec': {'deliverables': [{'spec_deliverable': 'D1', 'done_when': 'parser accepts input'}]}}
    by_number = {
        1: {'number': 1, 'success_criteria': ['parser accepts input']},
        2: {'number': 2, 'success_criteria': ['usage is documented']},
    }

    assert _snap._spec_clause_drift(snapshot, by_number) == []
    rows = _snap._spec_clause_drift(snapshot, by_number, frozenset({1}))

    assert [row['kind'] for row in rows] == [_snap.SPEC_MISSING], rows


def test_a_snapshot_with_no_recorded_freeze_is_present_not_frozen(plan_context) -> None:
    """The legacy ``present`` state is reported as itself and documented as unverified."""
    plan_dir = _plan(plan_context)
    status = json.loads((plan_dir / 'status.json').read_text(encoding='utf-8'))
    metadata = status.get('metadata')
    assert isinstance(metadata, dict)
    metadata.pop(_snap.INTEGRITY_KEY, None)
    (plan_dir / 'status.json').write_text(json.dumps(status), encoding='utf-8')

    assert _snap.snapshot_state(PLAN_ID) == 'present'
    assert 'no digest to compare' in (_snap.snapshot_state.__doc__ or '')
