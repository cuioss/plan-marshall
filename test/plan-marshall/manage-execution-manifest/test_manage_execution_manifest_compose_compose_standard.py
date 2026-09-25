# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures import (
    _LANE_STEPS,
    _compose_ns,
    _patch_element_lane,
    _write_status_metadata,
    cmd_compose,
    read_manifest,
)


def test_compose_standard_profile_drops_only_full_tier(plan_context, monkeypatch):
    """A standard posture keeps tier-standard finalize steps and drops only the full-tier ones."""
    _patch_element_lane(monkeypatch)
    plan_id = 'lane-standard-compose'
    _write_status_metadata(plan_context, plan_id, {'execution_profile': 'standard'})

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
    assert result['execution_profile'] == 'standard'
    manifest = read_manifest(plan_id)
    assert 'sonar-roundtrip' in manifest['phase_6']['steps']
    assert 'finalize-step-security-audit' not in manifest['phase_6']['steps']
    assert 'plan-marshall:plan-retrospective' not in manifest['phase_6']['steps']
