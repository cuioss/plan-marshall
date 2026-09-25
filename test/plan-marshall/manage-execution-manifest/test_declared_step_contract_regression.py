# SPDX-License-Identifier: FSL-1.1-ALv2
"""Behavior-cluster tests carved from test_declared_step_contract_regression.py: declared."""

#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_declared_step_contract_regression_fixtures import (
    _RETROSPECTIVE,
    _compose_ns,
    _persisted_phase_6_steps,
    _seed_marshal,
    _write_plan_local_overrides,
    cmd_compose,
)

# =============================================================================
# (a) Declared-lane immunity survives a single_module compose
# =============================================================================


class TestDeclaredLaneSurvivesScopeGate:
    """An operator's ``lane: minimal`` reaches the composed manifest."""

    _STEPS_WITH_LANE: dict[str, dict | None] = {
        'default:create-pr': None,
        'default:lessons-capture': None,
        'plan-marshall:plan-retrospective': {'lane': 'minimal'},
        'default:branch-cleanup': None,
        'default:archive-plan': None,
    }
    _STEPS_WITHOUT_LANE: dict[str, dict | None] = {
        'default:create-pr': None,
        'default:lessons-capture': None,
        'plan-marshall:plan-retrospective': None,
        'default:branch-cleanup': None,
        'default:archive-plan': None,
    }

    def test_declared_lane_minimal_survives_single_module_compose(self, plan_context):
        """The regression: the step is emitted despite the single_module scope gate.

        Pre-fix, ``_apply_scope_gated_finalize`` dropped
        ``plan-marshall:plan-retrospective`` unconditionally on a single_module
        plan, at a stage BEFORE lane resolution — and since the step is not one of
        the four ceremony gates, no re-add path existed, so the declared lane was
        structurally unreachable.
        """
        _seed_marshal(self._STEPS_WITH_LANE)
        result = cmd_compose(_compose_ns('dsc-immune', scope_estimate='single_module'))

        assert result is not None and result['status'] == 'success'
        assert _RETROSPECTIVE in _persisted_phase_6_steps('dsc-immune')
        assert result['scope_gated_finalize_immune'] == [_RETROSPECTIVE]
        assert result['scope_gated_finalize_dropped'] == []

    def test_discriminator_undeclared_lane_is_still_dropped(self, plan_context):
        """Non-vacuity: the SAME compose without the declaration still drops the step.

        This is the pre-fix behaviour, still live for an undeclared step. If the
        immunity test above passed for any reason other than the declaration, this
        assertion would fail too — the pair can only both hold when the
        declaration is what makes the difference.
        """
        _seed_marshal(self._STEPS_WITHOUT_LANE)
        result = cmd_compose(_compose_ns('dsc-nodecl', scope_estimate='single_module'))

        assert result is not None and result['status'] == 'success'
        assert _RETROSPECTIVE not in _persisted_phase_6_steps('dsc-nodecl')
        assert result['scope_gated_finalize_dropped'] == [_RETROSPECTIVE]
        assert result['scope_gated_finalize_immune'] == []

    def test_surgical_scope_also_honours_the_declaration(self, plan_context):
        """The immunity is a property of the declaration, not of one scope value."""
        _seed_marshal(self._STEPS_WITH_LANE)
        result = cmd_compose(_compose_ns('dsc-immune-surgical', scope_estimate='surgical'))

        assert result is not None and result['status'] == 'success'
        assert _RETROSPECTIVE in _persisted_phase_6_steps('dsc-immune-surgical')

    def test_non_scope_gated_plan_keeps_the_step_either_way(self, plan_context):
        """A multi_module plan never reaches the drop set — the gate is scope-entered."""
        _seed_marshal(self._STEPS_WITHOUT_LANE)
        result = cmd_compose(_compose_ns('dsc-multi', scope_estimate='multi_module'))

        assert result is not None and result['status'] == 'success'
        assert _RETROSPECTIVE in _persisted_phase_6_steps('dsc-multi')
        assert result['scope_gated_finalize_dropped'] == []

    def test_plan_local_declaration_grants_the_same_immunity(self, plan_context):
        """The PLAN-LOCAL channel grants immunity exactly as marshal does.

        The D2 regression peer, asserted at the same user-visible boundary as its
        marshal sibling above: the marshal step map carries NO lane at all, and the
        declaration lives only in that plan's
        ``status.metadata.finalize_step_overrides``. The composer merges the two
        channels into one map, so the scope gate's immunity predicate sees the
        plan-scoped answer.

        Pre-fix, the immunity predicate read marshal.json alone, so a plan-scoped
        answer was structurally unreachable here — the operator declared the step
        and it was dropped anyway, with the drop recorded as an ordinary scope-gate
        subtraction.
        """
        _seed_marshal(self._STEPS_WITHOUT_LANE)
        _write_plan_local_overrides(plan_context, 'dsc-plan-local', {_RETROSPECTIVE: {'lane': 'minimal'}})

        result = cmd_compose(_compose_ns('dsc-plan-local', scope_estimate='single_module'))

        assert result is not None and result['status'] == 'success'
        assert _RETROSPECTIVE in _persisted_phase_6_steps('dsc-plan-local')
        assert result['scope_gated_finalize_immune'] == [_RETROSPECTIVE]
        assert result['scope_gated_finalize_dropped'] == []

    def test_both_channels_reach_the_identical_outcome(self, plan_context):
        """Equivalence: the two channels are interchangeable for this decision.

        Asserted as an equality between the two composes rather than as two
        independent expectations. Written this way, the test fails if EITHER
        channel regresses — including the asymmetric failure the merge exists to
        prevent, where one reader honours a declaration the other cannot see.
        """
        # Channel A — marshal-declared.
        _seed_marshal(self._STEPS_WITH_LANE)
        marshal_result = cmd_compose(_compose_ns('dsc-chan-marshal', scope_estimate='single_module'))
        marshal_steps = _persisted_phase_6_steps('dsc-chan-marshal')

        # Channel B — plan-local declared, marshal silent.
        _seed_marshal(self._STEPS_WITHOUT_LANE)
        _write_plan_local_overrides(plan_context, 'dsc-chan-plan', {_RETROSPECTIVE: {'lane': 'minimal'}})
        plan_result = cmd_compose(_compose_ns('dsc-chan-plan', scope_estimate='single_module'))
        plan_steps = _persisted_phase_6_steps('dsc-chan-plan')

        assert marshal_steps == plan_steps
        assert (
            marshal_result['scope_gated_finalize_immune']
            == plan_result['scope_gated_finalize_immune']
            == [_RETROSPECTIVE]
        )

    def test_plan_local_declaration_does_not_leak_to_another_plan(self, plan_context):
        """A plan-local answer governs THAT plan only — the point of the channel.

        The anti-leak assertion at the consuming end (its writer-side peer lives in
        ``test_cmd_finalize_steps.py``). One plan declares the lane; a sibling plan
        composed against the SAME marshal.json must still be scope-gated, because
        the declaration was never written project-wide.
        """
        _seed_marshal(self._STEPS_WITHOUT_LANE)
        _write_plan_local_overrides(plan_context, 'dsc-leak-declared', {_RETROSPECTIVE: {'lane': 'minimal'}})

        declared = cmd_compose(_compose_ns('dsc-leak-declared', scope_estimate='single_module'))
        sibling = cmd_compose(_compose_ns('dsc-leak-sibling', scope_estimate='single_module'))

        assert _RETROSPECTIVE in _persisted_phase_6_steps('dsc-leak-declared')
        assert declared['scope_gated_finalize_immune'] == [_RETROSPECTIVE]
        # The sibling never declared anything, so the gate still takes the step.
        assert _RETROSPECTIVE not in _persisted_phase_6_steps('dsc-leak-sibling')
        assert sibling['scope_gated_finalize_dropped'] == [_RETROSPECTIVE]
