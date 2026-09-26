# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_manage_execution_manifest_compose_fixtures import (
    _LANE_STEPS,
    _compose_ns,
    _dropped_steps,
    _patch_element_lane,
    _write_status_metadata,
    cmd_compose,
    read_manifest,
)


def test_compose_minimal_profile_prunes_phase_6_to_floor(plan_context, monkeypatch):
    """A minimal posture prunes the standard/full-tier finalize steps from phase_6.steps."""
    _patch_element_lane(monkeypatch)
    plan_id = 'lane-minimal-compose'
    _write_status_metadata(plan_context, plan_id, {'execution_profile': 'minimal'})

    result = cmd_compose(
        _compose_ns(
            plan_id=plan_id,
            change_type='feature',
            scope_estimate='multi_module',
            affected_files_count=5,
            phase_6_steps=','.join(_LANE_STEPS),
        )
    )

    assert result is not None
    assert result['execution_profile'] == 'minimal'
    manifest = read_manifest(plan_id)
    # The D1 sort choke-point places archive-plan (order 1100) terminal among
    # the order-resolvable steps, so it now trails deploy-target.
    assert manifest['phase_6']['steps'] == ['push', 'project:finalize-step-deploy-target', 'archive-plan']
    assert _dropped_steps(result['lane_dropped']) == {
        'sonar-roundtrip',
        'finalize-step-security-audit',
        'plan-marshall:plan-retrospective',
    }
    # Each surfaced record carries its own reason — the compose result is where an
    # operator reads WHY a lane element was pruned.
    assert all(record['reason'] for record in result['lane_dropped'])
