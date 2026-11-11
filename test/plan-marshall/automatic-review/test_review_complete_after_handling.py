# SPDX-License-Identifier: FSL-1.1-ALv2
"""A flagged bot with a qualifying, handled review is complete at any later head.

The producer keeps reporting the same facts it always did: a bot named in
``stale_participation_bots[]`` published a review that fails the currency test,
which for a bot declaring ``review_complete_after_handling`` is exactly "a
qualifying review of an earlier head". This module pins the classifier and the
trigger selector on that reading:

- ``classify_bot`` reports such a bot ``participated`` / ``participated_but_empty``
  instead of ``participated_stale``, so participation can be complete while the
  recorded review predates the head;
- pending findings still block through the triage arm, and an unreadable store is
  never a pass;
- a bot WITHOUT the flag keeps ``participated_stale``;
- a flagged bot whose only record is a refusal or an acknowledgment is not done;
- ``trigger-bot`` withholds a done bot from both trigger lists and names it in
  ``review_complete_bots[]``.
"""

from __future__ import annotations

import _findings_core as fc
import pytest

from conftest import load_script_module

rc = load_script_module('plan-marshall', 'automatic-review', 'review_completeness.py', register=False)

_STALE = 'a' * 40
_PR = 101


def _state(result: dict, bot: str) -> str:
    for record in result['bot_states']:
        if record['bot_kind'] == bot:
            return str(record['state'])
    raise AssertionError(f'{bot} missing from bot_states: {result["bot_states"]}')


def _seed_comment(plan_id: str, bot: str) -> str:
    """File one producer-shaped ``pr-comment`` finding for ``bot``, left pending."""
    result = fc.add_finding(
        plan_id,
        'pr-comment',
        title=f'PR #{_PR} inline comment by {bot}',
        detail=f'pr_number: {_PR}\nkind: inline\nauthor: {bot}\nthread_id: t\ncomment_id: c\n',
        bot_kind=bot,
        kind='inline',
        author=bot,
        reviewed_commit_sha=_STALE,
    )
    assert result['status'] == 'success', result
    return str(result['hash_id'])


# ---------------------------------------------------------------------------
# classify_bot
# ---------------------------------------------------------------------------


def test_a_flagged_bot_reported_stale_has_participated():
    """The stale report IS the qualifying review on an earlier head."""
    state = rc.classify_bot(
        'coderabbit',
        proven_participants={},
        has_findings=True,
        in_progress=set(),
        refused=set(),
        stale_participants={'coderabbit'},
    )

    assert state == rc.STATE_PARTICIPATED


def test_a_flagged_stale_bot_with_no_findings_is_participated_but_empty():
    state = rc.classify_bot(
        'coderabbit',
        proven_participants={},
        has_findings=False,
        in_progress=set(),
        refused=set(),
        stale_participants={'coderabbit'},
    )

    assert state == rc.STATE_PARTICIPATED_BUT_EMPTY


def test_an_unflagged_stale_bot_stays_participated_stale():
    """MATCHED CONTROL — same observation, no flag: today's verdict and remedy stand."""
    state = rc.classify_bot(
        'sourcery',
        proven_participants={},
        has_findings=True,
        in_progress=set(),
        refused=set(),
        stale_participants={'sourcery'},
    )

    assert state == rc.STATE_PARTICIPATED_STALE


def test_a_flagged_bot_whose_only_record_is_a_refusal_is_not_done():
    """A refusal is not a review: the done rule never claims one."""
    state = rc.classify_bot(
        'coderabbit',
        proven_participants={},
        has_findings=False,
        in_progress=set(),
        refused={'coderabbit'},
        stale_participants={'coderabbit'},
    )

    assert state != rc.STATE_PARTICIPATED
    assert state != rc.STATE_PARTICIPATED_BUT_EMPTY
    assert state.startswith('refused_')


# ---------------------------------------------------------------------------
# check_completeness
# ---------------------------------------------------------------------------


def test_a_handled_flagged_review_completes_participation(plan_context):
    """The done fixture: stale report, no pending finding, participation complete."""
    plan_id = 'lb142-done-complete'
    plan_context.plan_dir_for(plan_id)

    result = rc.check_completeness(
        plan_id,
        ['coderabbit'],
        triage_ran=True,
        stale_participation_bots=['coderabbit'],
        pr_number=_PR,
    )

    assert result['status'] == 'success'
    assert result['participation_complete'] is True
    assert _state(result, 'coderabbit') in (rc.STATE_PARTICIPATED, rc.STATE_PARTICIPATED_BUT_EMPTY)


def test_a_pending_finding_still_blocks_a_flagged_review(plan_context):
    """Handling is not removed: a pending finding after triage is a real incompleteness."""
    plan_id = 'lb142-done-pending'
    plan_context.plan_dir_for(plan_id)
    _seed_comment(plan_id, 'coderabbit')

    result = rc.check_completeness(
        plan_id,
        ['coderabbit'],
        triage_ran=True,
        stale_participation_bots=['coderabbit'],
        pr_number=_PR,
    )

    assert result['participation_complete'] is False
    assert result['pending_bots'] == ['coderabbit']


def test_an_unflagged_stale_bot_is_still_incomplete(plan_context):
    """MATCHED CONTROL — the same store and observation, a bot without the flag blocks."""
    plan_id = 'lb142-done-unflagged'
    plan_context.plan_dir_for(plan_id)

    result = rc.check_completeness(
        plan_id,
        ['sourcery'],
        triage_ran=True,
        stale_participation_bots=['sourcery'],
        pr_number=_PR,
    )

    assert result['participation_complete'] is False
    assert _state(result, 'sourcery') == rc.STATE_PARTICIPATED_STALE


def test_an_unreadable_findings_store_is_never_complete(plan_context, monkeypatch):
    """Fail-closed: a store nobody could read answers neither way."""
    plan_id = 'lb142-done-unreadable'
    plan_context.plan_dir_for(plan_id)
    monkeypatch.setattr(
        rc,
        '_read_pr_comment_findings',
        lambda _plan_id, _pr: {'status': 'error', 'error': 'load_failure', 'detail': 'unreadable'},
    )

    result = rc.check_completeness(
        plan_id,
        ['coderabbit'],
        triage_ran=True,
        stale_participation_bots=['coderabbit'],
        pr_number=_PR,
    )

    assert result['status'] == 'error'
    assert result.get('participation_complete') is not True


# ---------------------------------------------------------------------------
# trigger-bot
# ---------------------------------------------------------------------------


def test_trigger_bot_lists_no_flagged_bot_with_a_review_on_record():
    payload = rc.list_bots_for_trigger(
        ['coderabbit'],
        [],
        ['coderabbit'],
        optional_bots=['sourcery'],
    )

    assert payload['trigger_bots'] == []
    assert payload['required_stale_bots'] == []
    assert payload['review_complete_bots'] == ['coderabbit']


def test_trigger_bot_still_lists_an_unflagged_stale_bot():
    """MATCHED CONTROL — the same stale set without the flag is triggered as today."""
    payload = rc.list_bots_for_trigger(
        ['sourcery'],
        [],
        ['sourcery'],
        optional_bots=['coderabbit'],
    )

    assert payload['trigger_bots'] == ['sourcery']
    assert payload['required_stale_bots'] == ['sourcery']
    assert payload['review_complete_bots'] == []


def test_trigger_bot_withholds_a_flagged_bot_whose_stored_finding_is_joined():
    """A stored finding is evidence the bot reviewed, so the done filter covers the join.

    The exclusion keys on the registry flag, not on which source named the bot: a
    flagged bot owes no later head once ANY admitted evidence of its review exists.
    """
    payload = rc.list_bots_for_trigger(
        [],
        ['coderabbit'],
        ['coderabbit'],
        optional_bots=['sourcery'],
        stored_findings_stale=True,
    )

    assert payload['trigger_bots'] == []
    assert payload['required_stale_bots'] == []
    assert payload['review_complete_bots'] == ['coderabbit']


def test_a_flagged_candidate_in_neither_roster_list_is_still_reported_unclassified():
    """The done filter must not swallow the misconfiguration warning."""
    payload = rc.list_bots_for_trigger(
        ['coderabbit'],
        [],
        ['sourcery'],
        optional_bots=[],
    )

    assert payload['review_complete_bots'] == ['coderabbit']
    assert payload['unclassified_bots'] == ['coderabbit']
