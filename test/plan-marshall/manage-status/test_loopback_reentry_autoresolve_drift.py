# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_status_loopback_reentry_autoresolve_fixtures import (
    Namespace,
    _is_true,
    _read_status,
    _seed_plan,
    _store,
    _stub_metadata,
    _stubbed_invariants,
    cmd_set_phase,
    cmd_transition,
)

# =============================================================================
# (b) Drift + marker → auto-recapture, marker cleared, phase advances
# =============================================================================


def test_drift_with_marker_auto_recaptures_and_advances(plan_context, _stubbed_invariants, _stub_metadata):
    """Invariant drift with the marker present is auto-resolved: the handshake
    row is replaced (override=true, reason recorded), the marker is cleared,
    and the transition proceeds to 6-finalize."""
    plan_id = 'loopback-drift-autoresolved'
    status_path = _seed_plan(plan_context, plan_id, {'use_worktree': False})

    # Sanctioned loop-back: backward move writes the marker; the plan then
    # works its way forward again to the guarded boundary.
    cmd_set_phase(Namespace(plan_id=plan_id, phase='2-refine'))
    cmd_set_phase(Namespace(plan_id=plan_id, phase='5-execute'))
    assert _read_status(status_path)['metadata'].get('loop_back_reentry') is not None

    # The re-run phases legitimately changed an invariant → drift by construction.
    _stubbed_invariants['task_state_hash'] = 'hash-tasks-after-loopback'

    result = cmd_transition(Namespace(plan_id=plan_id, completed='5-execute'))

    assert result is not None
    assert result['status'] == 'success', f'Scheduled loop-back drift must be auto-resolved, got {result!r}.'
    assert result['next_phase'] == '6-finalize'

    after = _read_status(status_path)
    assert after['current_phase'] == '6-finalize'
    assert 'loop_back_reentry' not in after.get('metadata', {}), (
        'The marker must be cleared so the override fires exactly once.'
    )

    row = _store.get_row(plan_id, '5-execute')
    assert row is not None
    assert _is_true(row.get('override')), f'Auto-recapture must mark the replaced row override=true, got {row!r}.'
    assert 'loop-back re-entry auto-override (scheduled by 5-execute loop_back)' in str(row.get('override_reason')), (
        f'Recorded reason must name the scheduling loop-back, got {row!r}.'
    )
    assert row.get('task_state_hash') == 'hash-tasks-after-loopback', (
        'The replaced row must capture the post-loop-back state.'
    )

    # Unscheduled drift AFTER the marker is consumed still blocks — proven by
    # test_drift_without_marker_still_blocks (case c); the marker-absence
    # assertion above is what guarantees that case now applies.


# =============================================================================
# (c) Drift WITHOUT the marker still blocks
# =============================================================================


def test_drift_without_marker_still_blocks(plan_context, _stubbed_invariants, _stub_metadata):
    """Unscheduled drift keeps today's blocking behavior unchanged."""
    plan_id = 'loopback-unscheduled-drift-blocks'
    status_path = _seed_plan(plan_context, plan_id, {'use_worktree': False})

    _stubbed_invariants['task_state_hash'] = 'hash-tasks-mutated'

    result = cmd_transition(Namespace(plan_id=plan_id, completed='5-execute'))

    assert result is not None
    assert result['status'] == 'drift', f'Drift without the marker must block the transition, got {result!r}.'
    assert result['drift_count'] >= 1
    after = _read_status(status_path)
    assert after['current_phase'] == '5-execute', (
        'cmd_transition advanced despite unscheduled drift — the auto-override '
        'must be gated on the loop_back_reentry marker.'
    )
