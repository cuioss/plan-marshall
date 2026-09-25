# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_status_manage_status_transition_fixtures import (
    _MAILBOX_COUNT_KEYS,
    _MAILBOX_EPIC,
    Namespace,
    _inbox,
    _lifecycle,
    _mailbox_dir,
    _orchestrator_source_id,
    _seed_plan_with_provenance,
    _transition,
    cmd_create,
)


def test_an_empty_mailbox_and_an_absent_one_are_different_zeros(plan_context):
    """``count: 0`` alone does not discriminate — the state is what does.

    Both arms report zero messages. Only one of them looked.
    """
    looked_id = 'mailbox-looked-empty'
    _seed_plan_with_provenance(plan_context, looked_id, _orchestrator_source_id(_MAILBOX_EPIC))
    _mailbox_dir(looked_id).mkdir(parents=True, exist_ok=True)
    looked = _transition(looked_id)['mailbox']

    # Same epic tree (materialized by the arm above), no mailbox for this plan.
    absent_id = 'mailbox-never-addressed'
    _seed_plan_with_provenance(plan_context, absent_id, _orchestrator_source_id(_MAILBOX_EPIC))
    absent = _transition(absent_id)['mailbox']

    assert looked['probe'] == absent['probe'] == _lifecycle.MAILBOX_PROBE_READ
    assert looked['count'] == absent['count'] == 0
    assert looked['state'] == _inbox.MAILBOX_STATE_PRESENT
    assert absent['state'] == _inbox.MAILBOX_STATE_NO_MAILBOX
    assert looked['state'] not in _inbox.MAILBOX_COULD_NOT_LOOK_STATES
    assert absent['state'] in _inbox.MAILBOX_COULD_NOT_LOOK_STATES



def test_an_unreadable_mailbox_degrades_the_block_and_never_the_transition(plan_context):
    """A mailbox that cannot be listed still lets the phase advance.

    The failure is produced the way production would meet it — the addressee
    path is a FILE where a directory belongs — rather than by stubbing the
    reader, so the fail-open claim is exercised through the real read path.
    """
    plan_id = 'mailbox-unreadable'
    _seed_plan_with_provenance(plan_context, plan_id, _orchestrator_source_id(_MAILBOX_EPIC))
    mailbox = _mailbox_dir(plan_id)
    mailbox.parent.mkdir(parents=True, exist_ok=True)
    mailbox.write_text('not a directory\n', encoding='utf-8')

    result = _transition(plan_id)

    assert result['status'] == 'success'
    assert result['completed_phase'] == '1-init'
    assert result['mailbox']['probe'] == _lifecycle.MAILBOX_PROBE_READ
    assert result['mailbox']['state'] == _inbox.MAILBOX_STATE_UNREADABLE
    assert result['mailbox']['count'] == 0



def test_an_unreadable_request_md_reports_unresolved_and_publishes_no_counts(plan_context):
    """Provenance that cannot be read establishes nothing about the mailbox."""
    plan_id = 'mailbox-no-request'
    cmd_create(
        Namespace(
            plan_id=plan_id,
            title='Mailbox Checkpoint',
            phases='1-init,2-refine,3-outline,4-plan,5-execute,6-finalize',
            force=False,
        )
    )
    # No request.md is written at all — the plan carries no readable provenance.

    result = _transition(plan_id)

    assert result['status'] == 'success'
    mailbox = result['mailbox']
    assert mailbox['probe'] == _lifecycle.MAILBOX_PROBE_UNRESOLVED
    assert 'request.md' in mailbox['reason']
    for key in _MAILBOX_COUNT_KEYS:
        assert key not in mailbox
