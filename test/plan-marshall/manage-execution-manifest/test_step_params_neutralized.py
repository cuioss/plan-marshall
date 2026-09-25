# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_step_params_fixtures import (
    _FLOOR_LANE_STEP,
    _compose_ns,
    _patch_lane_resolution,
    _seed_marshal_with_lane_overrides,
    cmd_compose,
    read_manifest,
)


def test_neutralized_off_snapshots_the_effective_tier_and_records_the_request(plan_context, monkeypatch):
    """A step kept despite a neutralized ``off`` snapshots the tier it runs at.

    ``archive-plan`` is a floor element — its class is immune to a weakening
    ``off`` — so the element is KEPT and the stored ``off`` never bound. The
    snapshot must say so from both sides: ``lane`` names the tier it actually
    runs at, ``lane_requested`` preserves what was asked for.
    """
    _seed_marshal_with_lane_overrides(plan_context.fixture_dir, {f'default:{_FLOOR_LANE_STEP}': 'off'})
    _patch_lane_resolution(monkeypatch, 'standard')

    cmd_compose(_compose_ns('sp-lane-neutralized'))

    manifest = read_manifest('sp-lane-neutralized')
    assert manifest is not None
    # precondition: the off did NOT remove the floor element
    assert _FLOOR_LANE_STEP in manifest['phase_6']['steps']
    params = manifest['phase_6']['step_params'][_FLOOR_LANE_STEP]
    assert params['lane'] == 'minimal'
    assert params['lane_requested'] == 'off'
