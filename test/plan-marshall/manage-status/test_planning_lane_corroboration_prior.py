# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_status_planning_lane_corroboration_fixtures import evaluate_signals_pure

# =============================================================================
# D2 — the corroboration boundary (don't-fight regression + corroborated deep)
# =============================================================================


def test_prior_fix_surgical_plus_s7_alone_still_deep():
    """The prior false-negative fix is preserved: S7 alone STILL carries a surgical band.

    ``surgical`` is a POSITIVELY-earned narrow verdict; an author's explicit prose
    warning overriding it is a high-information act, and the prior fix (see
    ``test_planning_lane_risk_prose.py``) deliberately lets it win. The
    corroboration is scoped to the non-committal middle band only, so this case is
    untouched — the two fixes do not fight.
    """
    result = evaluate_signals_pure(
        plan_source='lesson',
        scope_estimate='surgical',
        change_type='bug_fix',
        compatibility='deprecation',
        request_concrete=True,
        risk_prose=True,
        override=None,
    )

    assert result['lane'] == 'deep'
    assert result['fired_signals'] == ['S7:risk_prose']
    assert result['suppressed_signals'] == []
