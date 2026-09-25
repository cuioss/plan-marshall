# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures import (
    _LANE_STEPS,
    _apply_lane_resolution,
    _dropped_steps,
    _lanes_preview_ns,
    _mem,
    _patch_element_lane,
    cmd_lanes_preview,
)


def test_lanes_preview_resolves_all_three_postures(plan_context, monkeypatch):
    """lanes preview returns the minimal/standard/full step MEMBERSHIP + cost sums in one result."""
    _patch_element_lane(monkeypatch)
    result = cmd_lanes_preview(_lanes_preview_ns('lanes-preview', _LANE_STEPS))

    assert result is not None and result['status'] == 'success'
    lanes = result['lanes']
    # Membership is asserted as a set: the preview now applies the composer's
    # frontmatter-order sort (see the ordering test below), so the emitted
    # sequence is the sorted one, not the candidate-list sequence.
    assert set(lanes['full']['phase_6_steps']) == set(_LANE_STEPS)
    assert set(lanes['minimal']['phase_6_steps']) == {
        'push',
        'archive-plan',
        'project:finalize-step-deploy-target',
    }
    assert set(lanes['standard']['phase_6_steps']) == {
        'push',
        'archive-plan',
        'sonar-roundtrip',
        'project:finalize-step-deploy-target',
    }
    # Cost sums are order-independent: XS=5K, L=130K → full=405K, standard=145K, minimal=15K.
    assert lanes['full']['cost_sum_tokens'] == 405000
    assert lanes['standard']['cost_sum_tokens'] == 145000
    assert lanes['minimal']['cost_sum_tokens'] == 15000



def test_lanes_preview_membership_agrees_with_apply_lane_resolution(plan_context, monkeypatch):
    """The preview MEMBERSHIP is the same projection compose applies.

    The preview shares ``_apply_lane_resolution`` with the composer, so for every
    posture it keeps exactly the same set of steps. The preview additionally
    applies the composer's ordering authority — asserted separately below — so
    this agreement is stated over membership, not sequence.
    """
    _patch_element_lane(monkeypatch)
    result = cmd_lanes_preview(_lanes_preview_ns('lanes-agree', _LANE_STEPS))
    assert result is not None

    for posture in ('minimal', 'standard', 'full'):
        kept, _dropped, _warnings = _apply_lane_resolution(_LANE_STEPS, posture, None)
        assert set(result['lanes'][posture]['phase_6_steps']) == set(kept)



def test_lanes_preview_applies_the_composer_ordering_authority(plan_context, monkeypatch):
    """The preview emits each posture in the composer's frontmatter-order sequence.

    Preview/compose agreement covers ORDER, not just membership: ``cmd_compose``
    sorts its final ``phase_6.steps`` via ``_sort_steps_by_frontmatter_order``, so
    an unsorted preview would report a different sequence for an identical
    membership — the divergence this reconciliation closes. The candidate list is
    deliberately fed in its unsorted fixture order.
    """
    _patch_element_lane(monkeypatch)
    result = cmd_lanes_preview(_lanes_preview_ns('lanes-order', _LANE_STEPS))
    assert result is not None

    for posture in ('minimal', 'standard', 'full'):
        kept, _dropped, _warnings = _apply_lane_resolution(_LANE_STEPS, posture, None)
        assert result['lanes'][posture]['phase_6_steps'] == _mem._sort_steps_by_frontmatter_order(kept)

    # Concretely, for the full posture the sort places the order-resolvable steps
    # ascending — deploy-target (81) before archive-plan (1100) — where the
    # candidate list had archive-plan second.
    full_steps = result['lanes']['full']['phase_6_steps']
    assert full_steps.index('project:finalize-step-deploy-target') < full_steps.index('archive-plan')



def test_lanes_preview_names_plan_input_dependent_steps(plan_context, monkeypatch):
    """The preview refuses diagnosably for steps whose fate needs plan inputs.

    ``finalize-step-security-audit`` survives the lane cutoff at the ``full``
    posture, but its membership in a composed manifest is decided by the
    ``security_class_inactive`` pre-filter, which reads ``affected_files_count``
    and the live footprint — inputs that do not exist at preview time. (The gate
    reads no ``change_type`` at all, but the two surface signals it does read are
    equally unavailable here.) The preview names it rather than implying the
    composer will agree.
    """
    _patch_element_lane(monkeypatch)
    result = cmd_lanes_preview(_lanes_preview_ns('lanes-plan-input', _LANE_STEPS))

    assert result is not None
    assert 'finalize-step-security-audit' in result['plan_input_dependent_steps']
    # ``push`` is named too: its final compose-time membership is decided by the
    # ``commit_and_push`` PLAN INPUT (via ``_apply_commit_push_disabled``), not by
    # marshal config alone — exactly the class of step the advisory exists to name.
    assert 'push' in result['plan_input_dependent_steps']
    # Steps whose fate marshal config alone decides are NOT named — naming them
    # would make the advisory meaningless.
    assert 'archive-plan' not in result['plan_input_dependent_steps']
    assert 'sonar-roundtrip' not in result['plan_input_dependent_steps']



def test_lanes_preview_reports_empty_advisory_when_nothing_is_plan_input_dependent(plan_context, monkeypatch):
    """An empty ``plan_input_dependent_steps`` means preview and compose agree outright.

    The fixture deliberately excludes ``push``: its membership IS plan-input
    dependent (``commit_and_push``), so including it would make this the
    something-is-plan-input-dependent scenario the sibling test already covers.
    """
    steps = ['archive-plan']
    _patch_element_lane(monkeypatch)
    result = cmd_lanes_preview(_lanes_preview_ns('lanes-no-advisory', steps))

    assert result is not None
    assert result['plan_input_dependent_steps'] == []



def test_lanes_preview_surfaces_each_postures_drops_beside_its_kept_set(plan_context, monkeypatch):
    """Each posture reports what it dropped, not only what it kept.

    A step missing from a lane is then diagnosable from this one payload — with
    the per-step reason the resolver already produces — instead of requiring the
    consumer to re-derive the difference against the candidate list and guess why.
    """
    _patch_element_lane(monkeypatch)

    result = cmd_lanes_preview(_lanes_preview_ns('lanes-dropped', _LANE_STEPS))

    assert result is not None
    minimal = result['lanes']['minimal']
    assert _dropped_steps(minimal['dropped']) == {
        'sonar-roundtrip',
        'finalize-step-security-audit',
        'plan-marshall:plan-retrospective',
    }
    # Kept and dropped partition the candidate set — nothing falls out unreported.
    assert set(minimal['phase_6_steps']) | _dropped_steps(minimal['dropped']) == set(_LANE_STEPS)
    for record in minimal['dropped']:
        assert record['reason']
    # The full posture prunes nothing, so its drop list is empty rather than absent.
    assert result['lanes']['full']['dropped'] == []
