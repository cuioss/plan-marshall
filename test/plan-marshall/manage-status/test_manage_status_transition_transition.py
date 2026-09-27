# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_status_manage_status_transition_fixtures import (
    _MAILBOX_EPIC,
    _deliver,
    _inbox,
    _lifecycle,
    _orchestrator_source_id,
    _seed_plan_with_provenance,
    _transition,
)


def test_transition_reports_a_message_delivered_to_the_plans_mailbox(plan_context):
    """The positive control: a delivered message is visible at the hand-over.

    Without this arm every could-not-look assertion below would be satisfied by
    a check-point that never reports mail at all.
    """
    plan_id = 'mailbox-delivered'
    _seed_plan_with_provenance(plan_context, plan_id, _orchestrator_source_id(_MAILBOX_EPIC))
    _deliver(plan_id)

    result = _transition(plan_id)

    assert result['status'] == 'success'
    assert result['next_phase'] == '2-refine'
    mailbox = result['mailbox']
    assert mailbox['checkpoint'] == _lifecycle.MAILBOX_CHECKPOINT_KEY
    assert mailbox['probe'] == _lifecycle.MAILBOX_PROBE_READ
    assert mailbox['epic'] == _MAILBOX_EPIC
    assert mailbox['state'] == _inbox.MAILBOX_STATE_PRESENT
    assert mailbox['count'] == 1
    assert mailbox['live_count'] == 1
    assert mailbox['invalid_count'] == 0
