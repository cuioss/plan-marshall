# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_status_mark_step_done_completion_head_and_keys_fixtures import (
    _args,
    _make_plan,
    cmd_mark_step_done,
    read_status,
)


def test_mark_step_omits_head_at_completion_key_when_flag_absent(plan_context):
    """Caller omitting --head-at-completion produces the legacy two-key dict shape."""
    plan_id = 'mark-step-head-omitted'
    _make_plan(plan_id)
    result = cmd_mark_step_done(_args(plan_id, '1-init', 'step-a', 'done', display_detail='legacy'))

    assert result['status'] == 'success'
    assert result['changed'] is True
    # Result echoes the field as None, but persistence omits the key entirely.
    assert result['head_at_completion'] is None

    persisted = read_status(plan_id)
    entry = persisted['metadata']['phase_steps']['1-init']['step-a']
    assert entry == {'outcome': 'done', 'display_detail': 'legacy'}
    assert 'head_at_completion' not in entry
