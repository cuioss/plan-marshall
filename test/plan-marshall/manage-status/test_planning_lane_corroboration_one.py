# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_status_planning_lane_corroboration_fixtures import evaluate_signals_pure


def test_one_null_discriminator_is_not_low_confidence():
    """A single unresolved discriminating read is not enough to flag the verdict.

    The boundary companion of the two-null case: the predicate fires at two, so one
    null must not. Without this the ``>= 2`` threshold would be indistinguishable
    from ``>= 1``.
    """
    result = evaluate_signals_pure(
        plan_source=None,
        scope_estimate='surgical',
        change_type='bug_fix',
        compatibility='deprecation',
        request_concrete=True,
        risk_prose=False,
        override=None,
    )
    confidence = result['confidence']

    assert confidence['null_signals'] == ['plan_source']
    assert confidence['low_confidence'] is False
