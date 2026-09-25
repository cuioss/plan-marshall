# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_status_mark_step_done_fixtures import _args, _make_plan, cmd_mark_step_done, read_status


def test_mark_step_omits_facts_key_when_flag_absent(plan_context):
    """Caller omitting --fact produces the byte-identical historical record shape."""
    plan_id = 'mark-step-facts-omitted'
    _make_plan(plan_id)
    result = cmd_mark_step_done(_args(plan_id, '1-init', 'step-a', 'done', display_detail='legacy'))

    assert result['status'] == 'success'
    # The result echoes the field as None, but persistence omits the key entirely.
    assert result['facts'] is None

    persisted = read_status(plan_id)
    entry = persisted['metadata']['phase_steps']['1-init']['step-a']
    assert entry == {'outcome': 'done', 'display_detail': 'legacy'}
    assert 'facts' not in entry
