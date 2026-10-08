#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``loop-back close`` verb of manage-status.

The close is the operator ending a finalize step's round loop on findings the
operator names, so the properties pinned here are the ones that make it both
exact and recognisable afterwards:

* the step is recorded ``done`` over its live ``loop_back`` record, carrying the
  override facts that tell an operator close apart from a verifier's;
* exactly the named findings are resolved ``accepted`` — an unnamed pending
  finding stays pending — and the step's own state findings are resolved too;
* a hash id that is not a pending finding refuses the whole call, and a refused
  call writes nothing: no step record, no resolution, no waiver;
* a waived step keeps its ``done`` outcome and the anchor it completed at, and
  gains the waiver beside them;
* the waivers are stamped onto the status document as last committed, and a
  close that stamps none does not rewrite it;
* a blank or missing rationale is refused.

Each test uses its own ``plan_id`` so no test reads another's status document or
finding store.
"""

from __future__ import annotations

import sys
from argparse import Namespace
from typing import Any, cast

import pytest
from _mark_step_done_fixtures import _real_head, _tmp_repo_two_heads

from conftest import load_script_module

_lifecycle = load_script_module('plan-marshall', 'manage-status', '_cmd_lifecycle.py', '_loop_back_close_lifecycle')
_loop_back = load_script_module('plan-marshall', 'manage-status', '_cmd_loop_back.py', '_loop_back_close_cmd')
_status_core = load_script_module('plan-marshall', 'manage-status', '_status_core.py', '_loop_back_close_status_core')
_cli = load_script_module('plan-marshall', 'manage-status', 'manage-status.py', '_loop_back_close_cli')

cmd_create = _lifecycle.cmd_create
cmd_loop_back_close = _loop_back.cmd_loop_back_close
# The handler's own binding, so a fixture record is written by the very write the
# close goes through.
cmd_mark_step_done = _loop_back.cmd_mark_step_done
read_status = _status_core.read_status

_PHASE = '6-finalize'
_STEP = 'pre-submission-self-review'
_WAIVED_STEP = 'pre-push-quality-gate'
_STATE_RULE = 'pre-submission-self-review-state'
#: A budget source another writer spends from while a close is in flight.
_OTHER_SOURCE = 'wait-region-unified-triage'
_RATIONALE = 'the two residual findings are wording nits the operator accepts'

#: The facts a close reached by the step's own verifier records. An operator
#: close must record neither value.
_VERIFIER_MAY_CLOSE = 'yes'
_VERIFIER_ACCEPTANCE = 'accepted'


def _findings() -> Any:
    """The findings storage module the close handler itself resolves.

    Read through the handler's own loader rather than loaded a second time, so a
    finding filed by a fixture lands in the store the handler reads.
    """
    module = _loop_back._load_findings_core()
    assert module is not None, 'the findings store module is not importable in the test environment'
    return module


def _make_plan(plan_id: str) -> None:
    cmd_create(
        Namespace(
            plan_id=plan_id,
            title='Loop-back Close Test',
            phases='1-init,2-refine,3-outline,4-plan,5-execute,6-finalize',
            force=False,
        )
    )


def _mark(
    plan_id: str,
    step: str,
    outcome: str,
    head: str,
    detail: str,
    loop_back_target: str | None = None,
) -> dict[str, Any]:
    result = cmd_mark_step_done(
        Namespace(
            plan_id=plan_id,
            phase=_PHASE,
            step=step,
            outcome=outcome,
            display_detail=detail,
            head_at_completion=head,
            loop_back_target=loop_back_target,
            fact=None,
            force=False,
            no_completion_log=False,
        )
    )
    assert result is not None
    assert result['status'] == 'success', result
    return cast(dict[str, Any], result)


def _close(
    plan_id: str,
    head: str,
    rationale: str = _RATIONALE,
    accept: list[str] | None = None,
    waive_refire: list[str] | None = None,
    step: str = _STEP,
) -> dict[str, Any]:
    result = cmd_loop_back_close(
        Namespace(
            plan_id=plan_id,
            step=step,
            head=head,
            rationale=rationale,
            accept=accept,
            waive_refire=waive_refire,
        )
    )
    assert result is not None
    return cast(dict[str, Any], result)


def _file_finding(plan_id: str, title: str, rule: str | None = None) -> str:
    """File one pending 6-finalize Q-Gate finding and return its hash id."""
    kwargs: dict[str, Any] = {'severity': 'warning'}
    if rule is None:
        kwargs['file_path'] = 'doc/a.md'
    else:
        kwargs['rule'] = rule
    result = _findings().add_qgate_finding(plan_id, _PHASE, 'qgate', 'bug', title, f'detail of {title}', **kwargs)
    assert result['status'] == 'success', result
    return str(result['hash_id'])


def _records(plan_id: str) -> dict[str, dict[str, Any]]:
    """Every 6-finalize Q-Gate finding of the plan, keyed by hash id."""
    queried = _findings().query_qgate_findings(plan_id, _PHASE)
    assert queried['status'] == 'success', queried
    return {finding['hash_id']: finding for finding in queried['findings']}


def _pending(plan_id: str) -> set[str]:
    queried = _findings().query_qgate_findings(plan_id, _PHASE, resolution='pending')
    assert queried['status'] == 'success', queried
    return {finding['hash_id'] for finding in queried['findings']}


def _step_record(plan_id: str, step: str) -> dict[str, Any]:
    steps = read_status(plan_id).get('metadata', {}).get('phase_steps', {}).get(_PHASE, {})
    return cast(dict[str, Any], steps[step])


# =============================================================================
# The close itself
# =============================================================================


def test_a_close_records_done_over_a_live_loop_back_with_the_override_facts(plan_context):
    """The step's loop_back record becomes done, and the named findings accepted."""
    plan_id = 'loop-back-close-records-done'
    _make_plan(plan_id)
    head = _real_head()
    _mark(plan_id, _STEP, 'loop_back', head, 'self-review found 2 issues in 1 classes', loop_back_target=_PHASE)
    first = _file_finding(plan_id, 'ambiguous_wording at doc/a.md:12')
    second = _file_finding(plan_id, 'ambiguous_wording at doc/a.md:40')

    result = _close(plan_id, head, accept=[first, second])

    assert result['status'] == 'success', result
    assert result['step'] == _STEP
    assert result['outcome'] == 'done'
    assert result['head'] == head
    assert result['accepted'] == [first, second]
    assert result['accepted_count'] == 2

    record = _step_record(plan_id, _STEP)
    assert record['outcome'] == 'done'
    assert record['head_at_completion'] == head
    assert record['display_detail'] == 'operator close: 2 finding(s) accepted'
    assert record['facts'] == {
        'may_close': 'operator_override',
        'acceptance': 'operator_override',
        'work_performed': 'true',
    }
    # The superseded firing is kept: the close is recorded over the loop_back,
    # not in place of a record that never looped.
    assert record['prior_firings'] == [{'outcome': 'loop_back', 'loop_back_target': _PHASE}]

    records = _records(plan_id)
    for hash_id in (first, second):
        assert records[hash_id]['resolution'] == 'accepted'
        assert records[hash_id]['resolution_detail'] == _RATIONALE


def test_an_operator_close_is_told_apart_from_a_verifier_close_by_its_facts(plan_context):
    """The recorded facts, not the done outcome, are what separate the two closes."""
    plan_id = 'loop-back-close-told-apart'
    _make_plan(plan_id)
    head = _real_head()

    result = _close(plan_id, head)

    facts = _step_record(plan_id, _STEP)['facts']
    assert facts['may_close'] == _loop_back.OPERATOR_OVERRIDE
    assert facts['acceptance'] == _loop_back.OPERATOR_OVERRIDE
    assert facts['may_close'] != _VERIFIER_MAY_CLOSE
    assert facts['acceptance'] != _VERIFIER_ACCEPTANCE
    # The return states the same pair, so a caller need not re-read the record.
    assert (result['may_close'], result['acceptance']) == (facts['may_close'], facts['acceptance'])


def test_an_unnamed_pending_finding_stays_pending(plan_context):
    """Matched control: the close resolves the findings it was told about and no other."""
    plan_id = 'loop-back-close-unnamed-stays'
    _make_plan(plan_id)
    head = _real_head()
    named = _file_finding(plan_id, 'ambiguous_wording at doc/a.md:12')
    unnamed = _file_finding(plan_id, 'duplicate_prose at doc/a.md:80')

    result = _close(plan_id, head, accept=[named])

    assert result['status'] == 'success', result
    assert _pending(plan_id) == {unnamed}
    assert _records(plan_id)[named]['resolution'] == 'accepted'


def test_a_pending_state_finding_is_resolved_by_the_close(plan_context):
    """The step's own state findings are resolved without being named."""
    plan_id = 'loop-back-close-state-finding'
    _make_plan(plan_id)
    head = _real_head()
    state = _file_finding(plan_id, 'further_round_owed at pre-submission-self-review', rule=_STATE_RULE)
    other_rule = _file_finding(plan_id, 'missing-yield at some-other-step', rule='missing-yield')

    result = _close(plan_id, head)

    assert result['status'] == 'success', result
    assert result['state_rule'] == _STATE_RULE
    assert result['state_findings_resolved'] == 1
    record = _records(plan_id)[state]
    assert record['resolution'] == 'accepted'
    assert head in record['resolution_detail']
    assert _RATIONALE in record['resolution_detail']
    # A finding under another rule key is not this step's state and is left alone.
    assert _pending(plan_id) == {other_rule}


# =============================================================================
# Refusals — validated before the first write
# =============================================================================


def test_an_unknown_hash_id_refuses_the_whole_close_and_writes_nothing(plan_context):
    """One bad id stops everything: no step record, no resolution of the good id."""
    plan_id = 'loop-back-close-unknown-hash'
    _make_plan(plan_id)
    head = _real_head()
    _mark(plan_id, _STEP, 'loop_back', head, 'self-review found 1 issues in 1 classes', loop_back_target=_PHASE)
    real = _file_finding(plan_id, 'ambiguous_wording at doc/a.md:12')
    state = _file_finding(plan_id, 'verdict_refused at pre-submission-self-review', rule=_STATE_RULE)
    before = read_status(plan_id)

    result = _close(plan_id, head, accept=[real, 'no-such-hash'])

    assert result['status'] == 'error'
    assert result['error'] == 'finding_not_pending'
    assert result['not_pending'] == ['no-such-hash']
    assert read_status(plan_id) == before
    assert _step_record(plan_id, _STEP)['outcome'] == 'loop_back'
    assert _pending(plan_id) == {real, state}


def test_an_already_resolved_hash_id_is_not_pending_and_refuses_the_close(plan_context):
    """A finding resolved earlier is not a pending finding, so naming it refuses."""
    plan_id = 'loop-back-close-resolved-hash'
    _make_plan(plan_id)
    head = _real_head()
    resolved = _file_finding(plan_id, 'ambiguous_wording at doc/a.md:12')
    _findings().resolve_qgate_finding(plan_id, _PHASE, resolved, 'fixed', detail='fixed earlier')
    before = read_status(plan_id)

    result = _close(plan_id, head, accept=[resolved])

    assert result['error'] == 'finding_not_pending'
    assert read_status(plan_id) == before
    assert _records(plan_id)[resolved]['resolution'] == 'fixed'


@pytest.mark.parametrize('blank', ['', '   ', '\t\n'])
def test_a_blank_rationale_is_refused_and_writes_nothing(plan_context, blank):
    """A close must state why; an empty or whitespace-only rationale changes nothing."""
    plan_id = f'loop-back-close-blank-rationale-{len(blank)}'
    _make_plan(plan_id)
    head = _real_head()
    named = _file_finding(plan_id, 'ambiguous_wording at doc/a.md:12')
    before = read_status(plan_id)

    result = _close(plan_id, head, rationale=blank, accept=[named])

    assert result['status'] == 'error'
    assert result['error'] == 'blank_rationale'
    assert read_status(plan_id) == before
    assert _pending(plan_id) == {named}


def test_the_cli_verb_refuses_a_call_with_no_rationale_flag(plan_context, monkeypatch, capsys):
    """A missing --rationale never reaches the handler, and nothing is written."""
    plan_id = 'loop-back-close-cli-no-rationale'
    _make_plan(plan_id)
    head = _real_head()
    before = read_status(plan_id)
    monkeypatch.setattr(
        sys, 'argv', ['manage-status', 'loop-back', 'close', '--plan-id', plan_id, '--step', _STEP, '--head', head]
    )

    with pytest.raises(SystemExit) as exc:
        _cli.main()

    assert exc.value.code not in (0, None)
    captured = capsys.readouterr()
    assert 'rationale' in captured.err + captured.out
    assert read_status(plan_id) == before


def test_an_abbreviated_head_is_refused_and_writes_nothing(plan_context):
    """The closing HEAD is compared for equality later, so an abbreviation is refused."""
    plan_id = 'loop-back-close-abbreviated-head'
    _make_plan(plan_id)
    head = _real_head()
    before = read_status(plan_id)

    result = _close(plan_id, head[:9])

    assert result['status'] == 'error'
    assert result['error'] == 'invalid_head'
    assert read_status(plan_id) == before


# =============================================================================
# The re-fire waiver
# =============================================================================


def test_a_waived_step_keeps_its_done_record_and_gains_the_waiver(plan_context, tmp_path, monkeypatch):
    """The waiver is a sibling key: outcome, anchor and history are untouched."""
    plan_id = 'loop-back-close-waiver'
    _make_plan(plan_id)
    closing_head, completed_at = _tmp_repo_two_heads(tmp_path, monkeypatch)
    _mark(plan_id, _WAIVED_STEP, 'done', completed_at, 'quality gate green')
    before = dict(_step_record(plan_id, _WAIVED_STEP))

    result = _close(plan_id, closing_head, waive_refire=[_WAIVED_STEP])

    assert result['status'] == 'success', result
    assert result['waived_steps'] == [_WAIVED_STEP]
    record = _step_record(plan_id, _WAIVED_STEP)
    assert record['outcome'] == 'done'
    assert record['head_at_completion'] == completed_at
    assert record['head_at_completion'] != closing_head
    waiver = record['refire_waiver']
    assert waiver['head'] == closing_head
    assert _STEP in waiver['basis']
    assert _RATIONALE in waiver['basis']
    # Nothing but the waiver was added to the record.
    assert {key: value for key, value in record.items() if key != 'refire_waiver'} == before


def test_a_step_with_no_done_record_cannot_be_waived_and_nothing_is_written(plan_context):
    """Matched control for the waiver: there is no re-fire to waive for an unfinished step."""
    plan_id = 'loop-back-close-not-waivable'
    _make_plan(plan_id)
    head = _real_head()
    named = _file_finding(plan_id, 'ambiguous_wording at doc/a.md:12')
    before = read_status(plan_id)

    result = _close(plan_id, head, accept=[named], waive_refire=[_WAIVED_STEP])

    assert result['status'] == 'error'
    assert result['error'] == 'step_not_waivable'
    assert result['not_waivable'] == [_WAIVED_STEP]
    assert read_status(plan_id) == before
    assert _pending(plan_id) == {named}


def test_a_real_re_fire_of_a_waived_step_drops_the_waiver(plan_context, tmp_path, monkeypatch):
    """A waiver answers for one recorded completion; a new firing carries none."""
    plan_id = 'loop-back-close-waiver-dropped'
    _make_plan(plan_id)
    closing_head, completed_at = _tmp_repo_two_heads(tmp_path, monkeypatch)
    _mark(plan_id, _WAIVED_STEP, 'done', completed_at, 'quality gate green')
    _close(plan_id, closing_head, waive_refire=[_WAIVED_STEP])
    assert 'refire_waiver' in _step_record(plan_id, _WAIVED_STEP)

    _mark(plan_id, _WAIVED_STEP, 'done', closing_head, 'quality gate green at the closing head')

    record = _step_record(plan_id, _WAIVED_STEP)
    assert 'refire_waiver' not in record
    assert record['head_at_completion'] == closing_head


def test_a_close_whose_every_waiver_is_refused_does_not_rewrite_the_status_document(
    plan_context, tmp_path, monkeypatch
):
    """With no waiver stamped there is nothing to commit, so the file is left as it was."""
    plan_id = 'loop-back-close-waiver-all-refused'
    _make_plan(plan_id)
    closing_head, completed_at = _tmp_repo_two_heads(tmp_path, monkeypatch)
    _mark(plan_id, _WAIVED_STEP, 'done', completed_at, 'quality gate green')
    status_path = _status_core.get_status_path(plan_id)
    after_mark: dict[str, Any] = {}
    real_mark = _loop_back.cmd_mark_step_done

    def _mark_then_loop_the_waived_step_back(args: Namespace) -> Any:
        # Another writer re-fires the waived step once the close has validated it.
        result = real_mark(args)
        _mark(plan_id, _WAIVED_STEP, 'loop_back', completed_at, 'quality gate re-fired', loop_back_target=_PHASE)
        after_mark.update(content=status_path.read_bytes(), inode=status_path.stat().st_ino)
        return result

    monkeypatch.setattr(_loop_back, 'cmd_mark_step_done', _mark_then_loop_the_waived_step_back)

    result = _close(plan_id, closing_head, waive_refire=[_WAIVED_STEP])

    assert result['status'] == 'error'
    assert result['error'] == 'close_incomplete'
    assert result['waived_steps'] == []
    assert len(result['waiver_refusals']) == 1
    assert _WAIVED_STEP in result['waiver_refusals'][0]
    assert status_path.read_bytes() == after_mark['content']
    # A commit replaces the file, so an unchanged inode means none happened.
    assert status_path.stat().st_ino == after_mark['inode']


def test_a_change_committed_before_the_waiver_stamp_survives_it(plan_context, tmp_path, monkeypatch):
    """The waivers are stamped onto the document as last committed, not onto an earlier read."""
    plan_id = 'loop-back-close-waiver-keeps-commit'
    _make_plan(plan_id)
    closing_head, completed_at = _tmp_repo_two_heads(tmp_path, monkeypatch)
    _mark(plan_id, _WAIVED_STEP, 'done', completed_at, 'quality gate green')
    real_rmw_json = _loop_back.rmw_json

    def _admit_a_round_then_update(path: Any, mutate: Any) -> Any:
        # Another writer commits a budget change after the close's mark and
        # before the close takes the guard for its waiver stamp.
        _loop_back.cmd_loop_back_admit(Namespace(plan_id=plan_id, source=_OTHER_SOURCE, ceiling=1))
        return real_rmw_json(path, mutate)

    monkeypatch.setattr(_loop_back, 'rmw_json', _admit_a_round_then_update)

    result = _close(plan_id, closing_head, waive_refire=[_WAIVED_STEP])

    assert result['status'] == 'success', result
    assert result['waived_steps'] == [_WAIVED_STEP]
    assert _step_record(plan_id, _WAIVED_STEP)['refire_waiver']['head'] == closing_head
    budgets = read_status(plan_id)['metadata']['loop_back_budgets']
    assert budgets[_OTHER_SOURCE]['spent'] == 1
