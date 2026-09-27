# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_status_manage_status_transition_fixtures import (
    _MAILBOX_COUNT_KEYS,
    _MAILBOX_EPIC,
    Namespace,
    _deliver,
    _lifecycle,
    _orchestrator_source_id,
    _seed_plan_with_provenance,
    _transition,
    cmd_transition,
)


def test_a_plan_with_no_epic_reports_not_orchestrated_and_publishes_no_counts(plan_context):
    """A non-orchestrated plan has no mailbox — a measured fact, not a zero.

    The omission of the count keys is the assertion that matters: a `0` here
    would be byte-identical to a mailbox that was listed and held nothing.
    """
    plan_id = 'mailbox-free-form'
    _seed_plan_with_provenance(plan_context, plan_id, 'a free-form description, not a pointer')

    mailbox = _transition(plan_id)['mailbox']

    assert mailbox['probe'] == _lifecycle.MAILBOX_PROBE_NOT_ORCHESTRATED
    assert mailbox['probe'] in _lifecycle.MAILBOX_PROBE_DID_NOT_READ
    assert 'not_orchestrator_pointer' in mailbox['reason']
    for key in _MAILBOX_COUNT_KEYS:
        assert key not in mailbox, f'{key} was published by a probe that never read a mailbox'
    assert 'state' not in mailbox


def test_a_probe_that_raises_is_contained_and_named(plan_context, monkeypatch):
    """An unanticipated probe failure degrades the block, never the transition.

    The blanket containment is what "inherits the fail-open contract in full"
    means at this site, and it is only worth having if the contained failure is
    still NAMED — a swallowed exception would be indistinguishable from a plan
    that simply has no mailbox.
    """
    plan_id = 'mailbox-probe-explodes'
    _seed_plan_with_provenance(plan_context, plan_id, _orchestrator_source_id(_MAILBOX_EPIC))

    def _exploding(_plan_id):
        raise RuntimeError('the reader blew up')

    monkeypatch.setattr(_lifecycle, '_resolve_mailbox_checkpoint', _exploding)

    result = _transition(plan_id)

    assert result['status'] == 'success'
    assert result['next_phase'] == '2-refine'
    mailbox = result['mailbox']
    assert mailbox['checkpoint'] == _lifecycle.MAILBOX_CHECKPOINT_KEY
    assert mailbox['probe'] == _lifecycle.MAILBOX_PROBE_UNRESOLVED
    assert 'RuntimeError' in mailbox['reason']
    assert 'the reader blew up' in mailbox['reason']


def test_a_refused_transition_carries_no_mailbox_block(plan_context):
    """The check-point rides a hand-over; a refusal is not one.

    Publishing a mailbox block on a payload whose phase never advanced would
    claim a check-point at a moment the plan did not change hands.
    """
    plan_id = 'mailbox-refused'
    _seed_plan_with_provenance(plan_context, plan_id, _orchestrator_source_id(_MAILBOX_EPIC))
    _deliver(plan_id)

    result = cmd_transition(Namespace(plan_id=plan_id, completed='9-nonexistent'))

    assert result['status'] == 'error'
    assert result['error'] == 'invalid_phase'
    assert 'mailbox' not in result
