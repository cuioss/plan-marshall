# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_status_planning_lane_corroboration_fixtures import evaluate_signals_pure


def test_post_bridge_motivating_vector_is_low_confidence():
    """The motivating vector stays low-confidence once the bridge resolves plan_source.

    Two of the four discriminating reads (``change_type``, ``compatibility``) are
    null against four resolved signals — a bare majority rule called that confident,
    because the two body-derived booleans can never be null and always pad the
    resolved side. Keying on the discriminators alone is what makes the flag fire.
    """
    result = evaluate_signals_pure(
        plan_source='.plan/orchestrator/x/plans/PLAN-01-x.md',
        scope_estimate='single_module',
        change_type=None,
        compatibility=None,
        request_concrete=True,
        risk_prose=True,
        override=None,
    )
    confidence = result['confidence']

    assert confidence['signals_resolved'] == 4
    assert confidence['null_signals'] == ['change_type', 'compatibility']
    assert confidence['low_confidence'] is True
