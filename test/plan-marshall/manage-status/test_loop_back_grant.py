#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``loop-back grant`` verb of manage-status.

The grant is the one recorded way past a ceiling refusal, so the properties
pinned here are the ones that make it both effective and traceable:

* a grant to a refused source lets that source's next admission through, and
  leaves a record of the rounds, the reason, who granted them, when, and how
  many rounds the source had spent at that moment;
* a blank reason, or fewer than one round, is refused and writes nothing;
* a grant to one source does not admit another;
* grants accumulate, and a later admission does not discard their records.

Each test uses its own ``plan_id`` so no test reads another's status document.
"""

from argparse import Namespace
from typing import Any, cast

import pytest

from conftest import load_script_module

_lifecycle = load_script_module('plan-marshall', 'manage-status', '_cmd_lifecycle.py', '_loop_back_grant_lifecycle')
_loop_back = load_script_module('plan-marshall', 'manage-status', '_cmd_loop_back.py', '_loop_back_grant_cmd')
_status_core = load_script_module('plan-marshall', 'manage-status', '_status_core.py', '_loop_back_grant_status_core')

cmd_create = _lifecycle.cmd_create
cmd_loop_back_admit = _loop_back.cmd_loop_back_admit
cmd_loop_back_grant = _loop_back.cmd_loop_back_grant
read_status = _status_core.read_status

_SELF_REVIEW = 'default:pre-submission-self-review'
_AUTOMATIC_REVIEW = 'plan-marshall:automatic-review'
_MAX_ITERATIONS = 3
_REASON = 'one more review round for the last fix'


def _make_plan(plan_id: str) -> None:
    cmd_create(
        Namespace(
            plan_id=plan_id,
            title='Loop-back Grant Test',
            phases='1-init,2-refine,3-outline,4-plan,5-execute,6-finalize',
            force=False,
        )
    )


def _admit(plan_id: str, source: str) -> dict[str, Any]:
    result = cmd_loop_back_admit(Namespace(plan_id=plan_id, source=source, ceiling=_MAX_ITERATIONS))
    assert result is not None
    return cast(dict[str, Any], result)


def _grant(
    plan_id: str,
    source: str,
    reason: str = _REASON,
    rounds: int = 1,
    granted_by: str = 'operator',
) -> dict[str, Any]:
    result = cmd_loop_back_grant(
        Namespace(plan_id=plan_id, source=source, reason=reason, rounds=rounds, granted_by=granted_by)
    )
    assert result is not None
    return cast(dict[str, Any], result)


def _drive_to_ceiling(plan_id: str, source: str) -> None:
    """Spend every configured round, then show the next one is refused."""
    for _ in range(_MAX_ITERATIONS):
        assert _admit(plan_id, source)['admitted'] is True
    assert _admit(plan_id, source)['admitted'] is False


def _budget(plan_id: str, source: str) -> dict[str, Any]:
    return cast(dict[str, Any], read_status(plan_id)['metadata']['loop_back_budgets'][source])


def test_a_grant_admits_the_refused_source_and_leaves_its_record(plan_context):
    """Refused at the ceiling, granted one round with a reason, admitted on the next call."""
    plan_id = 'loop-back-grant-admits'
    _make_plan(plan_id)
    _drive_to_ceiling(plan_id, _SELF_REVIEW)

    granted = _grant(plan_id, _SELF_REVIEW)

    assert granted['status'] == 'success'
    assert granted['source'] == _SELF_REVIEW
    assert granted['rounds'] == 1
    assert granted['granted'] == 1
    assert granted['spent'] == _MAX_ITERATIONS
    assert granted['reason'] == _REASON
    assert granted['granted_by'] == 'operator'
    assert granted['grant_count'] == 1

    # The grant record is in the status file, with every field it promises.
    budget = _budget(plan_id, _SELF_REVIEW)
    assert budget['spent'] == _MAX_ITERATIONS
    assert budget['granted'] == 1
    assert budget['grants'] == [
        {
            'rounds': 1,
            'reason': _REASON,
            'granted_by': 'operator',
            'granted_at': granted['granted_at'],
            'spent_at_grant': _MAX_ITERATIONS,
        }
    ]
    assert granted['granted_at']

    # The grant itself admits nothing; the next admission does.
    admitted = _admit(plan_id, _SELF_REVIEW)
    assert admitted['admitted'] is True
    assert admitted['iteration'] == _MAX_ITERATIONS + 1
    assert admitted['effective_ceiling'] == _MAX_ITERATIONS + 1
    # One granted round buys exactly one admission.
    assert _admit(plan_id, _SELF_REVIEW)['admitted'] is False


@pytest.mark.parametrize('blank', ['', '   ', '\t\n'])
def test_a_blank_reason_is_refused_and_writes_nothing(plan_context, blank):
    """A grant must state why; an empty or whitespace-only reason changes nothing."""
    plan_id = f'loop-back-grant-blank-reason-{len(blank)}'
    _make_plan(plan_id)
    _drive_to_ceiling(plan_id, _SELF_REVIEW)
    before = read_status(plan_id)

    result = _grant(plan_id, _SELF_REVIEW, reason=blank)

    assert result['status'] == 'error'
    assert result['error'] == 'blank_reason'
    assert result['source'] == _SELF_REVIEW
    assert read_status(plan_id) == before
    # The source is still refused: the refused grant bought no round.
    assert _admit(plan_id, _SELF_REVIEW)['admitted'] is False


@pytest.mark.parametrize('rounds', [0, -1])
def test_fewer_than_one_round_is_refused_and_writes_nothing(plan_context, rounds):
    """A grant of zero or negative rounds is not a grant."""
    plan_id = f'loop-back-grant-invalid-rounds-{abs(rounds)}'
    _make_plan(plan_id)
    _drive_to_ceiling(plan_id, _SELF_REVIEW)
    before = read_status(plan_id)

    result = _grant(plan_id, _SELF_REVIEW, rounds=rounds)

    assert result['status'] == 'error'
    assert result['error'] == 'invalid_rounds'
    assert read_status(plan_id) == before


def test_a_grant_to_one_source_does_not_admit_another(plan_context):
    """Rounds are granted to the named source only."""
    plan_id = 'loop-back-grant-other-source'
    _make_plan(plan_id)
    _drive_to_ceiling(plan_id, _SELF_REVIEW)
    _drive_to_ceiling(plan_id, _AUTOMATIC_REVIEW)

    _grant(plan_id, _SELF_REVIEW)

    other = _admit(plan_id, _AUTOMATIC_REVIEW)
    assert other['admitted'] is False
    assert other['granted'] == 0
    assert other['effective_ceiling'] == _MAX_ITERATIONS
    assert 'grants' not in _budget(plan_id, _AUTOMATIC_REVIEW)
    # The granted source itself is admitted, so the grant did land somewhere.
    assert _admit(plan_id, _SELF_REVIEW)['admitted'] is True


def test_grants_accumulate_and_survive_a_later_admission(plan_context):
    """Two grants are two records, oldest first, and an admission keeps both."""
    plan_id = 'loop-back-grant-accumulates'
    _make_plan(plan_id)
    _drive_to_ceiling(plan_id, _SELF_REVIEW)

    first = _grant(plan_id, _SELF_REVIEW, reason='first extension', rounds=2)
    assert _admit(plan_id, _SELF_REVIEW)['admitted'] is True
    second = _grant(plan_id, _SELF_REVIEW, reason='second extension', granted_by='release-manager')

    assert first['granted'] == 2
    assert second['granted'] == 3
    assert second['grant_count'] == 2
    budget = _budget(plan_id, _SELF_REVIEW)
    assert budget['spent'] == _MAX_ITERATIONS + 1
    assert budget['granted'] == 3
    assert [(g['rounds'], g['reason'], g['granted_by'], g['spent_at_grant']) for g in budget['grants']] == [
        (2, 'first extension', 'operator', _MAX_ITERATIONS),
        (1, 'second extension', 'release-manager', _MAX_ITERATIONS + 1),
    ]
    # granted is the sum of the rounds the records carry.
    assert budget['granted'] == sum(g['rounds'] for g in budget['grants'])


def test_a_grant_before_any_admission_creates_the_record(plan_context):
    """A source with no entry can be granted rounds; it has spent nothing."""
    plan_id = 'loop-back-grant-fresh-source'
    _make_plan(plan_id)

    result = _grant(plan_id, _SELF_REVIEW)

    assert result['spent'] == 0
    budget = _budget(plan_id, _SELF_REVIEW)
    assert budget['spent'] == 0
    assert budget['granted'] == 1
    assert budget['grants'][0]['spent_at_grant'] == 0
    assert _admit(plan_id, _SELF_REVIEW)['effective_ceiling'] == _MAX_ITERATIONS + 1
