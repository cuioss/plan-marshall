# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_lane_class_off_immunity_fixtures import (
    _FLOOR_STEPS,
    _FOOTPRINT,
    _OPT_OUT_STEP,
    _compose_ns,
    _composed_steps,
    _dropped_reasons,
    _restore_footprint_resolvers,
    _seed_marshal,
    _stub_footprint,
    _warnings_by_step,
    _write_execution_profile,
    cmd_compose,
    pytest,
)

# --- arm (b): the matched negative — the same off on a non-floor class binds --


@pytest.mark.parametrize('posture', ['standard', 'minimal'])
def test_non_floor_element_is_dropped_by_the_same_off_under_the_same_posture(plan_context, posture):
    """MATCHED NEGATIVE on the CLASS axis: identical value, identical posture.

    Without this arm, the floor arm above would be satisfied by a lane pass that
    had simply stopped dropping anything at all. The only difference between the
    two composes is which class the target step declares, which is what attributes
    the split to the immunity rule rather than to the posture, the candidate list,
    or a disabled lane pass.
    """
    plan_id = f'class-off-nonfloor-{posture}'
    _seed_marshal(off_steps=[_OPT_OUT_STEP])
    _stub_footprint(_FOOTPRINT)
    _write_execution_profile(plan_context, plan_id, posture)

    result = cmd_compose(_compose_ns(plan_id))

    assert result is not None and result['status'] == 'success'
    composed = _composed_steps(plan_id)
    dropped = _dropped_reasons(result)
    warned = _warnings_by_step(result)

    assert _OPT_OUT_STEP not in composed
    assert _OPT_OUT_STEP in dropped
    # The drop is attributed to the opt-out, not to the posture cutoff — two
    # different facts about the same removal, and an operator reading the record
    # needs to tell them apart.
    assert "'off'" in dropped[_OPT_OUT_STEP]
    assert 'posture cutoff' not in dropped[_OPT_OUT_STEP]
    # A real opt-out is a clean drop: nothing was neutralized, so nothing warns.
    assert _OPT_OUT_STEP not in warned
    # The floor steps in the same compose declare no override and are untouched —
    # the drop is the override's doing, not the compose's.
    for step in _FLOOR_STEPS:
        assert step in composed
