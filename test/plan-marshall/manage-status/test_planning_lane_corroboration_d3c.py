# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_status_planning_lane_corroboration_fixtures import _RECORDED_VECTOR, evaluate_signals_pure

# =============================================================================
# D1 — signal-resolution confidence
# =============================================================================


def test_d3c_several_nulls_reported_low_confidence():
    """(c) A signal vector with several nulls is reported low-confidence.

    The recorded vector resolved only 3 of the 6 READ signals — ``plan_source``,
    ``change_type`` and ``compatibility`` were null. Three of the four discriminating
    reads are unresolved, so the block flags it low-confidence and a 3-of-6 decision
    cannot masquerade as a confident one. ``planning_lane_override`` is absent from
    the split entirely: it was never read, only unset.
    """
    result = evaluate_signals_pure(**_RECORDED_VECTOR)
    confidence = result['confidence']

    assert confidence['signals_total'] == 6
    assert confidence['signals_resolved'] == 3
    assert confidence['signals_null'] == 3
    assert confidence['null_signals'] == ['change_type', 'compatibility', 'plan_source']
    assert confidence['low_confidence'] is True
