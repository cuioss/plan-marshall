# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_status_loopback_reentry_autoresolve_fixtures import (
    Namespace,
    _is_true,
    _lifecycle,
    _read_status,
    _seed_plan,
    _store,
    _stub_metadata,
    _stubbed_invariants,
    cmd_set_phase,
    cmd_transition,
)

# =============================================================================
# (b2) Clean verify + marker → marker consumed WITHOUT recapture
# =============================================================================


def test_clean_verify_with_marker_consumes_marker_without_recapture(plan_context, _stubbed_invariants, _stub_metadata):
    """Consume-on-next-guarded-verification: a clean (non-blocking) guarded
    verify with the marker present must clear it — without a recapture — so a
    stale marker cannot incorrectly auto-override a later, genuinely
    unscheduled drift."""
    plan_id = 'loopback-clean-verify-consumes-marker'
    status_path = _seed_plan(plan_context, plan_id, {'use_worktree': False})

    # Sanctioned loop-back writes the marker; invariants are NOT mutated, so
    # the guarded verify at the boundary comes back clean.
    cmd_set_phase(Namespace(plan_id=plan_id, phase='2-refine'))
    cmd_set_phase(Namespace(plan_id=plan_id, phase='5-execute'))
    assert _read_status(status_path)['metadata'].get('loop_back_reentry') is not None

    result = cmd_transition(Namespace(plan_id=plan_id, completed='5-execute'))

    assert result is not None
    assert result['status'] == 'success'
    assert result['next_phase'] == '6-finalize'

    after = _read_status(status_path)
    assert 'loop_back_reentry' not in after.get('metadata', {}), (
        'A clean guarded verification must consume the marker — a stale '
        'marker would incorrectly auto-override a later unscheduled drift.'
    )

    row = _store.get_row(plan_id, '5-execute')
    assert row is not None
    assert not _is_true(row.get('override')), (
        f'A clean verify must NOT recapture with override=true — the marker is consumed by a plain clear, got {row!r}.'
    )



def test_clean_tree_refusal_with_explicit_none_metadata():
    """_clean_tree_refusal must not raise AttributeError when
    status['metadata'] is explicitly None — no worktree means no refusal."""
    result = _lifecycle._clean_tree_refusal('loopback-none-metadata-cleantree', {'metadata': None})

    assert result is None, 'None metadata implies no use_worktree — the clean-tree gate must pass through, not crash.'
