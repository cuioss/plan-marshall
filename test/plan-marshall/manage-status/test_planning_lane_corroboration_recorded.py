# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_status_planning_lane_corroboration_fixtures import (
    _MEASURED_MIDDLE_BAND,
    _RECORDED_VECTOR,
    _ns_route,
    _write_marshal,
    _write_orchestrator_request,
    _write_references,
    _write_status,
    cmd_planning_lane_route,
    evaluate_signals_pure,
)


def test_recorded_vector_is_light_when_s7_does_not_fire():
    """The recorded vector with ``risk_prose`` off is light, suppressing nothing.

    Flipping ``risk_prose`` off (the ONLY fired signal) yields ``light`` with an
    EMPTY suppressed set — proving the deep verdict this vector originally produced
    came from S7, and that suppression, not some other signal, is what changed it in
    the test above. The sanity anchor for D3(a).
    """
    vector = {**_RECORDED_VECTOR, 'risk_prose': False}

    result = evaluate_signals_pure(**vector, scope_band_rule=_MEASURED_MIDDLE_BAND)

    assert result['lane'] == 'light'
    assert result['fired_signals'] == []
    assert result['suppressed_signals'] == []


def test_recorded_vector_without_a_measured_band_keeps_the_lane():
    """No band rule supplied means nothing was measured — S7 keeps the lane.

    The same recorded vector, called the way a consumer that cannot supply a band
    rule calls it. Nothing contradicts the author, so the warning carries ``deep``
    and the suppressed set stays empty. This is the negative control for the
    measured-evidence bound: it differs from ``test_d3a_...`` in the band rule alone.
    """
    result = evaluate_signals_pure(**_RECORDED_VECTOR)

    assert result['lane'] == 'deep'
    assert result['fired_signals'] == ['S7:risk_prose']
    assert result['suppressed_signals'] == []


# =============================================================================
# D0/D3(b) — the orchestrator-spec plan_source bridge (end-to-end via the router)
# =============================================================================


def test_recorded_case_end_to_end_routes_light(plan_context):
    """End-to-end wiring of D3(a): a MEASURED middle band that fires ONLY S7 routes
    light through the real command entry point.

    The body names four distinct paths and no fan-out marker, so the band table
    counts them into the middle band (``path_count_middle_band``) — a real
    measurement, not a default. The count also keeps S5 / S1 quiet, while one
    risk-prose phrase (``foundation``) fires S7 alone. The corroboration then denies
    it the lane: ``light``, with S7 suppressed — the recorded over-route, corrected,
    proven through the reader rather than only the pure scorer.
    """
    plan_dir = plan_context.plan_dir_for('pl-recorded-e2e')
    _write_orchestrator_request(
        plan_dir,
        '.plan/orchestrator/y/plans/PLAN-03-y.md',
        'Update pkg/one.py, pkg/two.py, pkg/three.py and pkg/four.py. This is foundation work the rest builds on.',
    )
    _write_status(plan_dir, metadata={})
    _write_references(plan_dir, scope_estimate='single_module')
    _write_marshal(plan_context.fixture_dir)

    result = cmd_planning_lane_route(_ns_route('pl-recorded-e2e'))

    assert result['scope_provenance']['band_rule'] == _MEASURED_MIDDLE_BAND
    assert result['signals']['risk_prose'] is True
    assert result['planning_lane'] == 'light'
    assert result['fired_signals'] == []
    assert result['suppressed_signals'] == ['S7:risk_prose']
