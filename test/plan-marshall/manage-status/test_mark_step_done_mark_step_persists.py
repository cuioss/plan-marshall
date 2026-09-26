# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_status_mark_step_done_fixtures import _args, _make_plan, cmd_mark_step_done, read_status

# =============================================================================
# Structured step facts (--fact KEY=VALUE)
#
# The facts dict is what makes a step record answer structured questions that
# its display_detail prose cannot. These cases pin the persistence shape, the
# omit-when-absent legacy guarantee, accumulation across repeated flags, the
# malformed-token rejection, and facts-only change detection.
# =============================================================================


def test_mark_step_persists_facts_into_the_record(plan_context):
    """A single --fact is parsed into a facts dict persisted on the entry."""
    plan_id = 'mark-step-facts-single'
    _make_plan(plan_id)
    result = cmd_mark_step_done(
        _args(
            plan_id,
            '6-finalize',
            'finalize-step-sync-baseline',
            'done',
            display_detail='no-op rebase',
            fact=['action=noop'],
        )
    )

    assert result['status'] == 'success'
    assert result['changed'] is True
    assert result['facts'] == {'action': 'noop'}

    persisted = read_status(plan_id)
    assert persisted['metadata']['phase_steps']['6-finalize']['finalize-step-sync-baseline'] == {
        'outcome': 'done',
        'display_detail': 'no-op rebase',
        'facts': {'action': 'noop'},
    }
