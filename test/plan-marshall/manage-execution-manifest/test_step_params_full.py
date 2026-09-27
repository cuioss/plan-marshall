# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_step_params_fixtures import (
    _compose_ns,
    _patch_lane_resolution,
    _seed_marshal_with_lane_overrides,
    cmd_compose,
    read_manifest,
)


def test_full_posture_keeps_the_step_and_still_records_no_bare_off(plan_context, monkeypatch):
    """Under ``full`` the step survives, so its ``off`` must still not be recorded bare.

    ``full`` keeps everything — the lane pass short-circuits and drops nothing —
    so a ``prunable`` element carrying ``off`` stays in ``phase_6.steps``. That is
    precisely the case a value read off the lane pass would miss, so the snapshot
    must still report the tier the element runs at. The ``standard``-posture arm
    is the matched negative control: there the same ``off`` DOES drop the step,
    which is what proves the posture is what this test varies.
    """
    _seed_marshal_with_lane_overrides(plan_context.fixture_dir, {'default:sonar-roundtrip': 'off'})
    _patch_lane_resolution(monkeypatch, 'full')

    cmd_compose(_compose_ns('sp-lane-full'))

    manifest = read_manifest('sp-lane-full')
    assert manifest is not None
    assert 'sonar-roundtrip' in manifest['phase_6']['steps']
    params = manifest['phase_6']['step_params']['sonar-roundtrip']
    assert params['lane'] == 'standard'
    assert params['lane_requested'] == 'off'

    # Negative control: the same stored ``off`` on the same element is a real
    # opt-out under a pruning posture, so the step is dropped and never snapshotted.
    _patch_lane_resolution(monkeypatch, 'standard')
    cmd_compose(_compose_ns('sp-lane-standard-control'))

    control = read_manifest('sp-lane-standard-control')
    assert control is not None
    assert 'sonar-roundtrip' not in control['phase_6']['steps']
    assert 'sonar-roundtrip' not in control['phase_6']['step_params']
