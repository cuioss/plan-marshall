# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_lane_class_off_immunity_fixtures import (
    _FLOOR_STEPS,
    _FOOTPRINT,
    _compose_ns,
    _composed_steps,
    _dropped_reasons,
    _mem,
    _restore_footprint_resolvers,
    _seed_marshal,
    _stub_footprint,
    _warnings_by_step,
    _write_execution_profile,
    cmd_compose,
    pytest,
)

# --- arm (a): a floor off is neutralized, under every pruning posture ---------


@pytest.mark.parametrize('posture', ['standard', 'minimal'])
def test_floor_element_survives_an_explicit_off_and_the_neutralization_is_reported(plan_context, posture):
    """A ``core`` element carrying an explicit ``off`` still composes — and says so.

    Asserted under BOTH pruning postures because the rule is a property of the
    class, not of the posture. ``full`` is excluded deliberately: that posture
    short-circuits the lane pass entirely, so it would report the same survival
    for a reason that has nothing to do with immunity (see the ``full``-posture
    control in the legacy-value arm below).

    Survival alone is not the contract — a composer that silently ignored the
    stored value would satisfy it. The warning is what makes the neutralization
    visible to the operator who wrote the ``off``, so both are asserted together.
    """
    plan_id = f'class-off-floor-{posture}'
    _seed_marshal(off_steps=_FLOOR_STEPS)
    _stub_footprint(_FOOTPRINT)
    _write_execution_profile(plan_context, plan_id, posture)

    result = cmd_compose(_compose_ns(plan_id))

    assert result is not None and result['status'] == 'success'
    assert result['execution_profile'] == posture

    composed = _composed_steps(plan_id)
    dropped = _dropped_reasons(result)
    warned = _warnings_by_step(result)
    for step in _FLOOR_STEPS:
        assert step in composed, f'{step} must survive a floor off under {posture}'
        assert step not in dropped, f'{step} was dropped despite being floor-classed'
        assert step in warned, f'{step} neutralized its off silently — the operator is not told'
        assert 'immune' in warned[step]
        assert 'cannot be weakened' in warned[step]
        # The warning names the CLASS it resolved, so the operator can tell WHY the
        # value was refused rather than only THAT it was.
        assert _mem._resolve_element_lane(step)['class'] in warned[step]
