# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_status_loopback_reentry_autoresolve_fixtures import (
    Namespace,
    Path,
    _read_status,
    _stub_metadata,
    _stubbed_invariants,
    cmd_create,
    cmd_set_phase,
)

# =============================================================================
# (d) Forward set-phase writes no marker
# =============================================================================


def test_forward_set_phase_writes_no_marker(plan_context, _stubbed_invariants, _stub_metadata):
    """A forward move never schedules an auto-override."""
    plan_id = 'loopback-forward-no-marker'
    cmd_create(
        Namespace(
            plan_id=plan_id,
            title='Loop-Back Auto-Resolve Test',
            phases='1-init,2-refine,3-outline,4-plan,5-execute,6-finalize',
            force=False,
        )
    )

    result = cmd_set_phase(Namespace(plan_id=plan_id, phase='2-refine'))

    assert result['status'] == 'success'
    status_path: Path = plan_context.plan_dir_for(plan_id) / 'status.json'
    metadata = _read_status(status_path).get('metadata', {})
    assert 'loop_back_reentry' not in metadata, (
        f'Forward set-phase must not write the loop-back marker, got {metadata!r}.'
    )
