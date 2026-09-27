# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_status_manage_status_transition_fixtures import (
    _MAILBOX_EPIC,
    _deliver,
    _inbox,
    _lifecycle,
    _mailbox_dir,
    _orchestrator_source_id,
    _persisted_status,
    _phase_status,
    _seed_plan_with_provenance,
    _transition,
)


def test_neither_arm_of_the_matched_pair_blocks_the_phase_write(plan_context):
    """The matched pair, anchored on PERSISTED state rather than on the return.

    One arm's mailbox is readable and carries a message; the other's cannot be
    listed at all. Both must advance the plan, and the assertion is made against
    ``status.json`` rather than against the returned dict — a check-point that
    returned ``status: success`` while skipping ``write_status`` would satisfy a
    return-only assertion and still have blocked the transition.

    The two arms are asserted side by side rather than in separate tests so the
    degraded arm's success is anchored: they are shown to differ in exactly the
    mailbox state, which is what makes this a matched pair instead of two calls
    that happen to agree.
    """
    readable_id = 'mailbox-pair-readable'
    _seed_plan_with_provenance(plan_context, readable_id, _orchestrator_source_id(_MAILBOX_EPIC))
    _deliver(readable_id)

    degraded_id = 'mailbox-pair-degraded'
    _seed_plan_with_provenance(plan_context, degraded_id, _orchestrator_source_id(_MAILBOX_EPIC))
    degraded_mailbox = _mailbox_dir(degraded_id)
    degraded_mailbox.parent.mkdir(parents=True, exist_ok=True)
    degraded_mailbox.write_text('a file where the mailbox directory belongs\n', encoding='utf-8')

    readable = _transition(readable_id)
    degraded = _transition(degraded_id)

    for plan_id, result in ((readable_id, readable), (degraded_id, degraded)):
        assert result['status'] == 'success', f'{plan_id} did not report a successful transition'
        persisted = _persisted_status(plan_context, plan_id)
        assert persisted['current_phase'] == '2-refine', (
            f'{plan_id} reported success but status.json was not advanced — the '
            'check-point blocked the phase write it is forbidden to gate.'
        )
        assert _phase_status(persisted, '1-init') == 'done'
        assert _phase_status(persisted, '2-refine') == 'in_progress'

    # Both arms reached the read; they differ in what the read could see.
    assert readable['mailbox']['probe'] == degraded['mailbox']['probe'] == _lifecycle.MAILBOX_PROBE_READ
    assert readable['mailbox']['state'] == _inbox.MAILBOX_STATE_PRESENT
    assert degraded['mailbox']['state'] == _inbox.MAILBOX_STATE_UNREADABLE
    assert readable['mailbox']['live_count'] == 1
    assert degraded['mailbox']['live_count'] == 0
