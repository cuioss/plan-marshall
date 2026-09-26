# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_status_planning_lane_corroboration_fixtures import evaluate_signals_pure

# =============================================================================
# D3(d) — CONTROL: a genuinely deep-warranting vector still routes deep
# =============================================================================


def test_d3d_control_deep_warranting_vector_still_routes_deep():
    """(d) CONTROL — a genuinely deep-warranting vector still routes deep.

    The most important test in the plan: everything else confirms the router stops
    over-escalating; ONLY this confirms it can still escalate. A router hardwired to
    ``light`` would pass every other case here and fail this one. The vector fires
    several independent deep signals (broad scope → S2, generative change → S3,
    breaking compat → S4, vague request → S5, free-form source → S1), so the
    prose-only corroboration never applies and the lane is a confident deep.
    """
    result = evaluate_signals_pure(
        plan_source=None,
        scope_estimate='multi_module',
        change_type='feature',
        compatibility='breaking',
        request_concrete=False,
        risk_prose=True,
        override=None,
    )

    assert result['lane'] == 'deep'
    assert 'S2:scope_estimate' in result['fired_signals']
    # Not a lone-prose verdict — corroboration cannot fire, nothing is suppressed.
    assert result['suppressed_signals'] == []
    assert result['confidence']['low_confidence'] is False
