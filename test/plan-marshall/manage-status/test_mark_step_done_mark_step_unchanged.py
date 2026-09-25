# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_status_mark_step_done_fixtures import _args, _make_plan, cmd_mark_step_done, read_status


def test_mark_step_unchanged_recall_appends_no_firing(plan_context):
    """An idempotent re-call reports `changed: false` and grows no trail.

    Guards the append against firing on a no-op write, which would inflate
    `firing_count` on every retry of an already-recorded step.
    """
    plan_id = 'mark-step-firings-idempotent'
    _make_plan(plan_id)

    cmd_mark_step_done(_args(plan_id, '6-finalize', 'push', 'done', display_detail='pushed'))
    second = cmd_mark_step_done(_args(plan_id, '6-finalize', 'push', 'done', display_detail='pushed'))

    assert second['changed'] is False
    entry = read_status(plan_id)['metadata']['phase_steps']['6-finalize']['push']
    assert entry == {'outcome': 'done', 'display_detail': 'pushed'}
    assert 'prior_firings' not in entry
