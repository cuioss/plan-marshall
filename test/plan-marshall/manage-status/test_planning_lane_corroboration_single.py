# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_status_planning_lane_corroboration_fixtures import evaluate_signals_pure


def test_single_module_without_s7_is_unaffected():
    """The corroboration touches ONLY the prose-only singleton.

    A ``single_module`` scope with no risk prose and no other deep signal was light
    before and stays light — the rule removes nothing that was not S7-alone.
    """
    result = evaluate_signals_pure(
        plan_source='lesson',
        scope_estimate='single_module',
        change_type='bug_fix',
        compatibility='deprecation',
        request_concrete=True,
        risk_prose=False,
        override=None,
    )

    assert result['lane'] == 'light'
    assert result['fired_signals'] == []
    assert result['suppressed_signals'] == []
