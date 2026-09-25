# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_status_planning_lane_corroboration_fixtures import _MEASURED_MIDDLE_BAND, evaluate_signals_pure, pytest


@pytest.mark.parametrize(
    'scope_estimate',
    ['module_pair', '', ' single_module'],
    ids=['unrecognised_band', 'empty_band', 'whitespace_padded_band'],
)
def test_unrecognised_noncommittal_band_does_not_suppress_s7(scope_estimate):
    """Only the explicit allowlist denies S7 the lane — nothing else does.

    Each band here is neither deep-biasing nor narrow, so the retired
    complement-of-two-sets test admitted all three and suppressed the warning. The
    allowlist admits ``single_module`` alone, so an unrecognised band, an empty one
    and a whitespace-padded one all fall through to "no corroboration" — even with
    the measured middle-band rule supplied, which isolates the allowlist as the
    single discriminator.
    """
    result = evaluate_signals_pure(
        plan_source='lesson',
        scope_estimate=scope_estimate,
        change_type='bug_fix',
        compatibility='deprecation',
        request_concrete=True,
        risk_prose=True,
        override=None,
        scope_band_rule=_MEASURED_MIDDLE_BAND,
    )

    assert result['lane'] == 'deep'
    assert result['fired_signals'] == ['S7:risk_prose']
    assert result['suppressed_signals'] == []
