# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_status_mark_step_done_fixtures import (
    _args,
    _make_plan,
    cmd_mark_step_done,
    read_status,
    write_status,
)


def test_mark_step_force_overwrites_stale_legacy_key_without_duplicate(plan_context):
    """A ``--force`` differing-outcome write over a stale ``default:push`` key pops it.

    The final-write branch pops the located stale key before storing the new
    canonical entry, so the force overwrite leaves exactly one canonical entry.
    """
    plan_id = 'mark-step-legacy-force'
    _make_plan(plan_id)
    status = read_status(plan_id)
    status.setdefault('metadata', {})['phase_steps'] = {
        '6-finalize': {'default:push': {'outcome': 'done', 'display_detail': 'old'}}
    }
    write_status(plan_id, status)

    result = cmd_mark_step_done(_args(plan_id, '6-finalize', 'push', 'skipped', force=True, display_detail='new'))

    assert result['status'] == 'success'
    assert result['changed'] is True
    assert result['previous_outcome'] == 'done'

    persisted = read_status(plan_id)
    phase_steps = persisted['metadata']['phase_steps']['6-finalize']
    assert phase_steps == {
        'push': {
            'outcome': 'skipped',
            'display_detail': 'new',
            'firing_count': 2,
            'prior_firings': [{'outcome': 'done'}],
        }
    }
    assert 'default:push' not in phase_steps
