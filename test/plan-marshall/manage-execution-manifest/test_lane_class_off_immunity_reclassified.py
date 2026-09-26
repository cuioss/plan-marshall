# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_lane_class_off_immunity_fixtures import (
    _FLOOR_STEPS,
    _FOOTPRINT,
    _RECLASSIFIED_STEP,
    _compose_ns,
    _composed_steps,
    _dropped_reasons,
    _restore_footprint_resolvers,
    _seed_marshal,
    _stub_footprint,
    _warnings_by_step,
    _write_execution_profile,
    cmd_compose,
)

# --- arm (d): the reclassified element drops by BOTH routes ------------------


def test_reclassified_lessons_capture_is_dropped_by_an_explicit_off(plan_context):
    """Route 1 — the ``off`` now BINDS, which is the point of the reclassification.

    Under its former ``core`` classification this exact stored value was
    neutralized: the one control an operator had over an advisory step did not
    work. The baseline compose in the same test is what makes the drop
    attributable to the override rather than to the posture — ``standard`` keeps
    the step when nothing is declared.
    """
    _stub_footprint(_FOOTPRINT)

    # Baseline: no override at all → the prunable class default (standard) is
    # within the standard posture, so the step is kept.
    _seed_marshal(off_steps=[])
    _write_execution_profile(plan_context, 'lessons-off-baseline', 'standard')
    baseline = cmd_compose(_compose_ns('lessons-off-baseline'))
    assert baseline is not None and baseline['status'] == 'success'
    assert _RECLASSIFIED_STEP in _composed_steps('lessons-off-baseline')
    assert _RECLASSIFIED_STEP not in _dropped_reasons(baseline)

    # Same posture, same candidates — only the stored override differs.
    _seed_marshal(off_steps=[_RECLASSIFIED_STEP])
    _write_execution_profile(plan_context, 'lessons-off-declared', 'standard')
    result = cmd_compose(_compose_ns('lessons-off-declared'))

    assert result is not None and result['status'] == 'success'
    dropped = _dropped_reasons(result)
    assert _RECLASSIFIED_STEP not in _composed_steps('lessons-off-declared')
    assert _RECLASSIFIED_STEP in dropped
    assert "'off'" in dropped[_RECLASSIFIED_STEP]
    # An honoured opt-out is a clean drop — a neutralization warning here would
    # mean the element was still being treated as floor.
    assert _RECLASSIFIED_STEP not in _warnings_by_step(result)


def test_reclassified_lessons_capture_falls_outside_the_minimal_posture_with_no_override(plan_context):
    """Route 2 — the accepted side effect: a ``minimal`` plan stops running it.

    No override is declared anywhere here. A non-floor class defaults to tier
    ``standard`` rather than ``core``'s ``minimal``, so the step now sits above the
    ``minimal`` cutoff. This is a consequence of the same property that makes its
    ``off`` honourable, and it is pinned deliberately rather than discovered later:
    the recorded reason must name the POSTURE CUTOFF, not an opt-out, because no
    operator asked for this removal.
    """
    plan_id = 'lessons-minimal-no-override'
    _seed_marshal(off_steps=[])
    _stub_footprint(_FOOTPRINT)
    _write_execution_profile(plan_context, plan_id, 'minimal')

    result = cmd_compose(_compose_ns(plan_id))

    assert result is not None and result['status'] == 'success'
    dropped = _dropped_reasons(result)
    assert _RECLASSIFIED_STEP not in _composed_steps(plan_id)
    assert _RECLASSIFIED_STEP in dropped
    assert 'posture cutoff' in dropped[_RECLASSIFIED_STEP]
    assert "'off'" not in dropped[_RECLASSIFIED_STEP]
    # The floor steps in the same minimal compose are untouched, so the drop is the
    # tier cutoff acting on ONE class rather than the posture emptying the list.
    composed = _composed_steps(plan_id)
    for step in _FLOOR_STEPS:
        assert step in composed
