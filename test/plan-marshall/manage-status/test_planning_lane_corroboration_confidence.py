# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_status_planning_lane_corroboration_fixtures import evaluate_signals_pure


def test_confidence_high_when_most_signals_resolve():
    """The mirror: a fully-resolved vector is NOT flagged low-confidence.

    Pairs with the low-confidence cases so the flag is shown to discriminate, not to
    fire unconditionally. Every read resolved, so the null set is empty — the unset
    override is no longer counted as an unresolved read.
    """
    result = evaluate_signals_pure(
        plan_source='lesson',
        scope_estimate='surgical',
        change_type='bug_fix',
        compatibility='deprecation',
        request_concrete=True,
        risk_prose=False,
        override=None,
    )
    confidence = result['confidence']

    assert confidence['signals_resolved'] == 6
    assert confidence['signals_null'] == 0
    assert confidence['null_signals'] == []
    assert confidence['low_confidence'] is False
