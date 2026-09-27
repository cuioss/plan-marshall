# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_status_mark_step_done_completion_head_and_keys_fixtures import (
    _args,
    _make_plan,
    cmd_mark_step_done,
    read_status,
)


def test_mark_step_bare_and_default_prefixed_reconcile_to_same_key(plan_context):
    """Recording via ``default:push`` then via ``push`` reconciles to ONE bare entry.

    Both spellings resolve to the same bare manifest key, so the second call is a
    no-op on the same record rather than creating a divergent orphan.
    """
    plan_id = 'mark-step-canon-reconcile'
    _make_plan(plan_id)
    first = cmd_mark_step_done(_args(plan_id, '6-finalize', 'default:push', 'done', display_detail='test detail'))
    assert first['status'] == 'success'
    assert first['changed'] is True

    # Same step, bare spelling, same outcome — idempotent no-op on the SAME entry.
    second = cmd_mark_step_done(_args(plan_id, '6-finalize', 'push', 'done', display_detail='test detail'))
    assert second['status'] == 'success'
    assert second['changed'] is False
    assert second['step'] == 'push'

    persisted = read_status(plan_id)
    phase_steps = persisted['metadata']['phase_steps']['6-finalize']
    # Exactly one entry under the bare key — no divergent default:-prefixed orphan.
    assert list(phase_steps.keys()) == ['push']
