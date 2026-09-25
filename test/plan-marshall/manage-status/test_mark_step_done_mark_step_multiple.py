# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_status_mark_step_done_fixtures import _args, _make_plan, cmd_mark_step_done, read_status


def test_mark_step_multiple_fact_flags_accumulate_into_one_dict(plan_context):
    """Repeated --fact flags accumulate into a single dict on the record."""
    plan_id = 'mark-step-facts-multi'
    _make_plan(plan_id)
    result = cmd_mark_step_done(
        _args(
            plan_id,
            '6-finalize',
            'finalize-step-sync-baseline',
            'done',
            display_detail='test detail',
            fact=['action=noop', 'upstream_commit_count=0', 'work_performed=true'],
        )
    )

    assert result['status'] == 'success'
    assert result['facts'] == {
        'action': 'noop',
        'upstream_commit_count': '0',
        'work_performed': 'true',
    }

    persisted = read_status(plan_id)
    entry = persisted['metadata']['phase_steps']['6-finalize']['finalize-step-sync-baseline']
    assert entry['facts'] == {
        'action': 'noop',
        'upstream_commit_count': '0',
        'work_performed': 'true',
    }
