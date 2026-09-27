# SPDX-License-Identifier: FSL-1.1-ALv2
"""Behavior-cluster tests carved from test_mark_step_done.py: mark step conflict."""

from _manage_status_mark_step_done_fixtures import (
    _args,
    _make_plan,
    cmd_mark_step_done,
    read_status,
    write_status,
)


def test_mark_step_conflict_fires_against_stale_legacy_key(plan_context):
    """A differing-outcome write over a stale ``default:push`` key raises conflict.

    Before the fix the stale key was invisible to ``get('push')``, so the conflict
    check was silently bypassed and a divergent duplicate was written. The fallback
    scan now surfaces the true existing outcome so the conflict fires.
    """
    plan_id = 'mark-step-legacy-conflict'
    _make_plan(plan_id)
    status = read_status(plan_id)
    status.setdefault('metadata', {})['phase_steps'] = {
        '6-finalize': {'default:push': {'outcome': 'done', 'display_detail': 'kept'}}
    }
    write_status(plan_id, status)

    result = cmd_mark_step_done(_args(plan_id, '6-finalize', 'push', 'skipped', display_detail='test detail'))

    assert result['status'] == 'error'
    assert result['error'] == 'conflict'
    assert result['existing_outcome'] == 'done'
    assert result['requested_outcome'] == 'skipped'

    # No divergent duplicate written — the stale legacy entry is untouched.
    persisted = read_status(plan_id)
    phase_steps = persisted['metadata']['phase_steps']['6-finalize']
    assert phase_steps == {'default:push': {'outcome': 'done', 'display_detail': 'kept'}}
    assert 'push' not in phase_steps
