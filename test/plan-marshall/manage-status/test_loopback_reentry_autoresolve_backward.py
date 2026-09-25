# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_status_loopback_reentry_autoresolve_fixtures import (
    Namespace,
    _read_status,
    _seed_plan,
    _stub_metadata,
    _stubbed_invariants,
    cmd_set_phase,
)

# =============================================================================
# (a) Backward set-phase persists the marker
# =============================================================================


def test_backward_set_phase_persists_loop_back_marker(plan_context, _stubbed_invariants, _stub_metadata):
    """5-execute → 2-refine (backward) writes metadata.loop_back_reentry."""
    plan_id = 'loopback-marker-persisted'
    status_path = _seed_plan(plan_context, plan_id, {'use_worktree': False})

    result = cmd_set_phase(Namespace(plan_id=plan_id, phase='2-refine'))

    assert result['status'] == 'success'
    marker = _read_status(status_path).get('metadata', {}).get('loop_back_reentry')
    assert marker is not None, (
        'Backward set-phase must persist metadata.loop_back_reentry so the guarded-boundary drift can be auto-resolved.'
    )
    assert marker['from_phase'] == '5-execute'
    assert marker['to_phase'] == '2-refine'
    assert marker['at'], 'Marker must carry a timestamp.'
