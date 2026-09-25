# SPDX-License-Identifier: FSL-1.1-ALv2
"""Behavior-cluster tests carved from test_planning_lane_corroboration.py: d3a."""

#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_status_planning_lane_corroboration_fixtures import (
    _MEASURED_MIDDLE_BAND,
    _RECORDED_VECTOR,
    evaluate_signals_pure,
)

# =============================================================================
# D3(a) — replay the recorded vector: NOT deep
# =============================================================================


def test_d3a_recorded_vector_does_not_route_deep():
    """(a) The exact recorded signal vector must NOT route deep.

    S7 was the SOLE fired signal against a ``single_module`` scope — the
    non-committal middle band — and the band was MEASURED
    (``path_count_middle_band``), so a real count contradicts the prose warning.
    The warning is uncorroborated and does not carry the lane: the verdict is
    ``light``, and S7 is reported under ``suppressed_signals`` rather than silently
    dropped.
    """
    result = evaluate_signals_pure(**_RECORDED_VECTOR, scope_band_rule=_MEASURED_MIDDLE_BAND)

    assert result['lane'] == 'light'
    assert result['fired_signals'] == []
    assert result['suppressed_signals'] == ['S7:risk_prose']
    # The signal FIRED — it is suppressed, not erased. The record must still say so.
    assert result['signals']['risk_prose'] is True
