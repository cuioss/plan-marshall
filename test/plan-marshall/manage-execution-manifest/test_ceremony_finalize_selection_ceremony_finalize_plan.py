# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_ceremony_finalize_selection_fixtures import (
    _FOOTPRINT,
    _bare,
    _compose_ns,
    _manifest_phase_6_steps,
    _phase_6_with_ceremony_steps,
    _seed_marshal,
    _stub_footprint,
    _write_plan_local_overrides,
    cmd_compose,
)


class TestCeremonyFinalizePlanLocalChannel:
    """A plan-local ``lane`` governs the ceremony gate exactly as a marshal one does."""

    _SELF_REVIEW_OWNER = 'default:pre-submission-self-review'

    def _compose_with(self, plan_id: str, candidates: list[str]):
        return cmd_compose(
            _compose_ns(
                plan_id=plan_id,
                change_type='feature',
                scope_estimate='multi_module',
                affected_files_count=5,
                phase_6_steps=','.join(candidates),
            )
        )

    def test_plan_local_off_drops_the_gate_step_like_a_marshal_off(self, plan_context):
        """``lane: off`` in either channel resolves the gate to ``never``.

        Asserted as an equivalence: the plan-local compose and the marshal compose
        must reach the SAME gate value and the same composed step list.
        """
        candidates = _phase_6_with_ceremony_steps().split(',')
        _stub_footprint(_FOOTPRINT)

        # Channel A — plan-local only; marshal declares nothing.
        _seed_marshal(candidates=candidates)
        _write_plan_local_overrides(plan_context, 'ceremony-plan-local-off', {self._SELF_REVIEW_OWNER: {'lane': 'off'}})
        plan_local = self._compose_with('ceremony-plan-local-off', candidates)

        # Channel B — marshal only; the plan declares nothing.
        _seed_marshal(finalize_gates={'self_review': 'off'}, candidates=candidates)
        marshal = self._compose_with('ceremony-marshal-off', candidates)

        assert plan_local is not None and marshal is not None
        assert plan_local['ceremony_finalize_gates']['self_review'] == 'never'
        assert plan_local['ceremony_finalize_gates']['self_review'] == marshal['ceremony_finalize_gates']['self_review']
        assert 'pre-submission-self-review' not in _bare(_manifest_phase_6_steps(plan_local))
        assert _bare(_manifest_phase_6_steps(plan_local)) == _bare(_manifest_phase_6_steps(marshal))

    def test_plan_local_minimal_forces_the_gate_in_like_a_marshal_minimal(self, plan_context):
        """``lane: minimal`` in either channel resolves the gate to ``always``."""
        candidates = _phase_6_with_ceremony_steps().split(',')
        _stub_footprint(_FOOTPRINT)

        _seed_marshal(candidates=candidates)
        _write_plan_local_overrides(
            plan_context, 'ceremony-plan-local-min', {self._SELF_REVIEW_OWNER: {'lane': 'minimal'}}
        )
        plan_local = self._compose_with('ceremony-plan-local-min', candidates)

        _seed_marshal(finalize_gates={'self_review': 'minimal'}, candidates=candidates)
        marshal = self._compose_with('ceremony-marshal-min', candidates)

        assert plan_local is not None and marshal is not None
        assert plan_local['ceremony_finalize_gates']['self_review'] == 'always'
        assert plan_local['ceremony_finalize_gates']['self_review'] == marshal['ceremony_finalize_gates']['self_review']

    def test_plan_local_declaration_also_grants_scope_gate_immunity(self, plan_context):
        """ONE declaration reaches BOTH readers — the symmetric-pair obligation.

        The assertion that pins the defect directly. A plan-local ``lane`` must
        simultaneously (a) resolve the ceremony gate and (b) appear in
        ``scope_gated_finalize_immune``. If only the immunity predicate saw the
        plan-local channel — the pre-fix state — the step would be spared the
        scope gate and then dropped by a ceremony gate that never heard about the
        declaration, which is a silent subtraction of an explicitly-declared step.
        """
        candidates = _phase_6_with_ceremony_steps().split(',')
        _seed_marshal(candidates=candidates)
        _stub_footprint(_FOOTPRINT)
        _write_plan_local_overrides(
            plan_context, 'ceremony-plan-local-immune', {self._SELF_REVIEW_OWNER: {'lane': 'off'}}
        )

        result = cmd_compose(
            _compose_ns(
                plan_id='ceremony-plan-local-immune',
                change_type='bug_fix',
                scope_estimate='surgical',
                affected_files_count=2,
                phase_6_steps=','.join(candidates),
            )
        )

        assert result is not None and result['status'] == 'success'
        # Reader 1 — the scope gate's immunity predicate saw the declaration.
        assert 'pre-submission-self-review' in result['scope_gated_finalize_immune']
        assert 'pre-submission-self-review' not in result['scope_gated_finalize_dropped']
        # Reader 2 — the ceremony gate saw the SAME declaration.
        assert result['ceremony_finalize_gates']['self_review'] == 'never'

    def test_plan_local_overlays_a_marshal_declaration_on_the_same_step(self, plan_context):
        """Precedence is plan-local ▸ marshal, applied per step key."""
        candidates = _phase_6_with_ceremony_steps().split(',')
        _seed_marshal(finalize_gates={'self_review': 'minimal'}, candidates=candidates)
        _stub_footprint(_FOOTPRINT)
        _write_plan_local_overrides(
            plan_context, 'ceremony-plan-local-wins', {self._SELF_REVIEW_OWNER: {'lane': 'off'}}
        )

        result = self._compose_with('ceremony-plan-local-wins', candidates)

        assert result is not None
        # marshal said minimal (always); the plan-local off wins → never.
        assert result['ceremony_finalize_gates']['self_review'] == 'never'

    def test_absent_plan_local_map_leaves_the_marshal_declaration_intact(self, plan_context):
        """The merge is an OVERLAY, not a replacement — no plan-local map is a no-op.

        The negative case: a merge that returned only the plan-local map would
        silently discard every project-wide declaration for any plan that has none
        of its own, and every positive test above would still pass.
        """
        candidates = _phase_6_with_ceremony_steps().split(',')
        _seed_marshal(finalize_gates={'self_review': 'off'}, candidates=candidates)
        _stub_footprint(_FOOTPRINT)

        result = self._compose_with('ceremony-no-plan-local', candidates)

        assert result is not None
        assert result['ceremony_finalize_gates']['self_review'] == 'never'
