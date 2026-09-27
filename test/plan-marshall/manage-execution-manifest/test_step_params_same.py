# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_step_params_fixtures import (
    _FLOOR_LANE_STEP,
    _OPT_OUT_LANE_STEP,
    _compose_ns,
    _patch_lane_resolution,
    _seed_marshal_with_lane_overrides,
    cmd_compose,
    read_manifest,
)


def test_the_same_off_on_a_non_floor_element_binds_and_is_never_snapshotted(plan_context, monkeypatch):
    """MATCHED NEGATIVE on the CLASS axis: identical value, identical posture.

    ``lessons-capture`` sits off the floor, so the very ``off`` the element above
    neutralized is a real opt-out here — the step is dropped and never reaches the
    snapshot at all. Without this arm the neutralization case would be equally
    satisfied by a lane pass that had simply stopped dropping anything, and the
    ``lane``/``lane_requested`` pair would be attributable to the value rather
    than to the class.
    """
    _seed_marshal_with_lane_overrides(plan_context.fixture_dir, {f'default:{_OPT_OUT_LANE_STEP}': 'off'})
    _patch_lane_resolution(monkeypatch, 'standard')

    cmd_compose(_compose_ns('sp-lane-opt-out-binds'))

    manifest = read_manifest('sp-lane-opt-out-binds')
    assert manifest is not None
    assert _OPT_OUT_LANE_STEP not in manifest['phase_6']['steps']
    assert _OPT_OUT_LANE_STEP not in manifest['phase_6']['step_params']
    # The floor element in the same compose declares no override and is untouched,
    # so the drop is the override acting on ONE class rather than the posture
    # emptying the list.
    assert _FLOOR_LANE_STEP in manifest['phase_6']['steps']
