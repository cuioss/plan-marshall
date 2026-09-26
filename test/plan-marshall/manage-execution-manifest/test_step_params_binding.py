# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_step_params_fixtures import (
    _compose_ns,
    _patch_lane_resolution,
    _seed_marshal_with_lane_overrides,
    cmd_compose,
    read_manifest,
)


def test_binding_lane_snapshots_the_stored_value_with_no_lane_requested_key(plan_context, monkeypatch):
    """A stored lane that BINDS snapshots that value and adds no ``lane_requested``.

    ``sonar-roundtrip`` is ``prunable`` with a declared ``standard`` tier, so a
    stored ``minimal`` genuinely overrides the declaration — request and outcome
    agree, and an unremarkable step must gain no extra key.
    """
    _seed_marshal_with_lane_overrides(plan_context.fixture_dir, {'default:sonar-roundtrip': 'minimal'})
    _patch_lane_resolution(monkeypatch, 'standard')

    cmd_compose(_compose_ns('sp-lane-binds'))

    manifest = read_manifest('sp-lane-binds')
    assert manifest is not None
    params = manifest['phase_6']['step_params']['sonar-roundtrip']
    # the override wins over the declared ``standard`` tier — so it IS the outcome
    assert params['lane'] == 'minimal'
    assert 'lane_requested' not in params
