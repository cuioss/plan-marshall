# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_lane_class_off_immunity_fixtures import (
    _FLOOR_STEPS,
    _FOOTPRINT,
    _compose_ns,
    _composed_steps,
    _restore_footprint_resolvers,
    _seed_marshal,
    _stub_footprint,
    _warnings_by_step,
    _write_execution_profile,
    cmd_compose,
)

# --- arm (c): a legacy stored inert value ------------------------------------


def test_a_legacy_stored_inert_off_still_produces_the_compose_time_warning(plan_context):
    """A stored inert ``off`` is reported at compose time, however it got there.

    The write surface now REFUSES an ``off`` on a floor element, so no new one can
    be stored — but the refusal is a gate on future writes, not a sweep of what is
    already on disk. Values written before it existed, and any written by hand as
    this fixture does, survive in marshal.json. Compose must therefore keep
    neutralizing and reporting them rather than treating an inert stored value as
    impossible.

    The write-time refusal itself is NOT re-asserted here — it is owned by
    ``test_cmd_quality_phases.py``'s step-set refusal cases, and duplicating it
    would make this module a second source of truth for a rule it only consumes.
    """
    plan_id = 'class-off-legacy-stored'
    _seed_marshal(off_steps=[_FLOOR_STEPS[0]])
    _stub_footprint(_FOOTPRINT)
    _write_execution_profile(plan_context, plan_id, 'standard')

    result = cmd_compose(_compose_ns(plan_id))

    assert result is not None and result['status'] == 'success'
    warned = _warnings_by_step(result)
    assert _FLOOR_STEPS[0] in warned
    assert 'immune' in warned[_FLOOR_STEPS[0]]
    assert _FLOOR_STEPS[0] in _composed_steps(plan_id)


def test_a_legacy_stored_inert_off_is_silent_under_the_full_posture(plan_context):
    """The caveat on the arm above: ``full`` reports nothing, because it resolves nothing.

    The ``full`` posture short-circuits the lane pass, so no element is examined
    and no neutralization is computed — the stored inert value is invisible. This
    is stated as its own control rather than left implicit because the two facts
    read as contradictory otherwise: a value the composer "always reports" is in
    fact reported only under a posture that prunes. An operator on a full-posture
    plan learns nothing about their inert override from this channel.
    """
    plan_id = 'class-off-legacy-full'
    _seed_marshal(off_steps=[_FLOOR_STEPS[0]])
    _stub_footprint(_FOOTPRINT)
    _write_execution_profile(plan_context, plan_id, 'full')

    result = cmd_compose(_compose_ns(plan_id))

    assert result is not None and result['status'] == 'success'
    assert result['execution_profile'] == 'full'
    assert result['lane_warnings'] == []
    assert result['lane_dropped'] == []
    assert _FLOOR_STEPS[0] in _composed_steps(plan_id)
