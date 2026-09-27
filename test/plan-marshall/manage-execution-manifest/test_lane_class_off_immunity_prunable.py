# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_lane_class_off_immunity_fixtures import (
    _OPT_OUT_STEP,
    _compose_ns,
    _composed_steps,
    _dropped_reasons,
    _mem,
    _restore_footprint_resolvers,
    _seed_marshal,
    _stub_footprint,
    _write_execution_profile,
    cmd_compose,
)

# --- arm (e): predicate dormancy ---------------------------------------------


def test_prunable_when_is_declared_but_never_evaluated_at_compose_time(plan_context):
    """``prunable_when`` is contract-live and implementation-DORMANT.

    The reclassification's third consequence — eligibility for a predicate-driven
    skip — changes nothing today, because no composer code reads the key. This arm
    holds that claim to its word: the fixture step declares a ``prunable_when``
    predicate whose condition is satisfied (an empty footprint is the
    ``no_code_delta`` shape), its effective tier is within the posture, and it is
    KEPT.

    ⛔ This test is designed to FAIL the day predicate evaluation is wired. That
    failure is the signal, not a defect: the dormancy sentence in the step's own
    documentation asserts a property of the composer, and it must be revisited in
    the same change that makes it false rather than being discovered stale later.
    """
    plan_id = 'prunable-when-dormant'
    _seed_marshal(off_steps=[])
    # An empty — not unresolvable — footprint: the resolvable-and-genuinely-empty
    # state a `no_code_delta` predicate would read as "the condition holds".
    _stub_footprint([])
    _write_execution_profile(plan_context, plan_id, 'standard')

    # Derived, not assumed: the arm means nothing unless the fixture step actually
    # declares a predicate for the composer to ignore.
    lane = _mem._resolve_element_lane(_OPT_OUT_STEP)
    assert lane and lane.get('prunable_when'), (
        f'{_OPT_OUT_STEP} declares no prunable_when, so this arm pins no dormancy.'
    )

    result = cmd_compose(_compose_ns(plan_id))

    assert result is not None and result['status'] == 'success'
    assert _OPT_OUT_STEP in _composed_steps(plan_id)
    assert _OPT_OUT_STEP not in _dropped_reasons(result)
