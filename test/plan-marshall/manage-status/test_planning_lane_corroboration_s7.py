# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_status_planning_lane_corroboration_fixtures import evaluate_signals_pure


def test_s7_with_a_corroborator_routes_deep_not_suppressed():
    """S7 is suppressed only when ALONE — a corroborated prose warning still routes deep.

    Here a ``multi_module`` scope fires S2 alongside S7, so ``fired`` is not the
    prose-only singleton and nothing is suppressed. A genuinely large change that
    also carries an author warning is never de-escalated.
    """
    result = evaluate_signals_pure(
        plan_source='lesson',
        scope_estimate='multi_module',
        change_type='bug_fix',
        compatibility='deprecation',
        request_concrete=True,
        risk_prose=True,
        override=None,
    )

    assert result['lane'] == 'deep'
    assert result['fired_signals'] == ['S2:scope_estimate', 'S7:risk_prose']
    assert result['suppressed_signals'] == []
