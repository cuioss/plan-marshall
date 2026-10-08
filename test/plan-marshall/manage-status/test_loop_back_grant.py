#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``loop-back grant`` verb of manage-status.

The properties pinned here are the ones that make a grant both effective and
traceable:

* a grant to a refused source lets that source's next admission through, and
  leaves a record of the rounds, the reason, who granted them, when, and how
  many rounds the source had spent at that moment;
* a blank reason, or fewer than one round, is refused and writes nothing;
* a grant to one source does not admit another;
* grants accumulate, and a later admission does not discard their records;
* a persisted grant writes one decision-log line naming the source, the rounds,
  the reason and who granted them, a refused grant writes none, and a line that
  cannot be written leaves the grant in place and is reported in the return.

Each test uses its own ``plan_id`` so no test reads another's status document.
"""

import sys
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
# The logging module the grant handler itself writes through, so the log read
# back here is the one the handler wrote to.
read_decision_log = sys.modules[_loop_back.log_decision.__module__].read_decision_log

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


# =============================================================================
# The decision-log line
# =============================================================================


def _grant_lines(plan_id: str) -> list[str]:
    """The decision-log messages the grant verb wrote for ``plan_id``."""
    logged = read_decision_log(plan_id)
    assert logged['status'] == 'success', logged
    return [entry['message'] for entry in logged['entries'] if 'loop-back-grant' in entry['message']]


def test_a_grant_writes_one_decision_line_naming_source_rounds_reason_and_granter(plan_context):
    """One persisted grant is one line, and the line carries all four facts."""
    plan_id = 'loop-back-grant-decision-line'
    _make_plan(plan_id)

    result = _grant(plan_id, _SELF_REVIEW, reason='the last fix needs a look', rounds=2, granted_by='release-manager')

    assert result['status'] == 'success'
    assert result['decision_logged'] is True
    assert 'decision_log_error' not in result
    lines = _grant_lines(plan_id)
    assert len(lines) == 1, lines
    line = lines[0]
    assert _SELF_REVIEW in line
    assert 'Granted 2 loop-back round(s)' in line
    assert 'the last fix needs a look' in line
    assert 'granted_by=release-manager' in line


def test_each_grant_writes_its_own_decision_line(plan_context):
    """Two grants are two lines, in the order they were granted."""
    plan_id = 'loop-back-grant-two-lines'
    _make_plan(plan_id)

    _grant(plan_id, _SELF_REVIEW, reason='first extension')
    _grant(plan_id, _AUTOMATIC_REVIEW, reason='second extension')

    lines = _grant_lines(plan_id)
    assert len(lines) == 2, lines
    assert _SELF_REVIEW in lines[0] and 'first extension' in lines[0]
    assert _AUTOMATIC_REVIEW in lines[1] and 'second extension' in lines[1]


def test_a_refused_grant_writes_no_decision_line(plan_context):
    """Matched control: nothing was granted, so nothing is logged as granted."""
    plan_id = 'loop-back-grant-refused-no-line'
    _make_plan(plan_id)

    result = _grant(plan_id, _SELF_REVIEW, reason='   ')

    assert result['status'] == 'error'
    assert 'decision_logged' not in result
    assert _grant_lines(plan_id) == []


def test_a_log_write_that_raises_leaves_the_grant_in_place_and_is_reported(plan_context, monkeypatch):
    """The grant is persisted before the line is written, and survives its failure."""
    plan_id = 'loop-back-grant-log-raises'
    _make_plan(plan_id)
    _drive_to_ceiling(plan_id, _SELF_REVIEW)

    def _raise(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise OSError('decision log is not writable')

    monkeypatch.setattr(_loop_back, 'log_decision', _raise)

    result = _grant(plan_id, _SELF_REVIEW)

    assert result['status'] == 'success'
    assert result['granted'] == 1
    assert result['decision_logged'] is False
    assert 'decision log is not writable' in result['decision_log_error']
    budget = _budget(plan_id, _SELF_REVIEW)
    assert budget['granted'] == 1
    assert len(budget['grants']) == 1
    # The round the grant bought is still spendable.
    assert _admit(plan_id, _SELF_REVIEW)['admitted'] is True


def test_a_log_write_that_reports_an_error_leaves_the_grant_in_place_and_is_reported(plan_context, monkeypatch):
    """A logger that returns an error instead of raising is reported the same way."""
    plan_id = 'loop-back-grant-log-error'
    _make_plan(plan_id)
    monkeypatch.setattr(
        _loop_back,
        'log_decision',
        lambda *_args, **_kwargs: {'status': 'error', 'error': 'write_failed', 'message': 'disk full'},
    )

    result = _grant(plan_id, _SELF_REVIEW)

    assert result['status'] == 'success'
    assert result['decision_logged'] is False
    assert result['decision_log_error'] == 'disk full'
    assert _budget(plan_id, _SELF_REVIEW)['granted'] == 1
