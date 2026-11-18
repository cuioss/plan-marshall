# SPDX-License-Identifier: FSL-1.1-ALv2

import pytest
from _manage_execution_manifest_ceremony_finalize_selection_fixtures import (
    _FOOTPRINT,
    _bare,
    _compose_ns,
    _manifest_phase_6_steps,
    _mem,
    _phase_6_with_ceremony_steps,
    _restore_footprint_resolver,
    _seed_marshal,
    _stub_footprint,
    cmd_compose,
)

# =============================================================================
# Test: always — force-include (overriding scope_gated_finalize)
# =============================================================================


class TestCeremonyFinalizeAlways:
    """``always`` re-adds the gate's step even when a pre-filter dropped it."""

    def test_functional_review_survives_surgical_scope_gate_via_declared_lane_immunity(self, plan_context):
        """A ``minimal`` functional_review gate keeps the step on a surgical plan —
        by IMMUNITY at the scope gate, not by an ``always`` re-add.

        Setting the gate to ``minimal`` writes ``lane: minimal`` on
        ``default:functional-review``, which is an explicit non-``auto`` lane
        declaration. ``scope_gated_finalize`` therefore never drops the step, so by
        the time the ceremony transform runs there is nothing to re-add and
        ``always`` is correctly a no-op. The operator-visible outcome — the step
        runs — is unchanged; the mechanism that delivers it moved one stage
        earlier, from undoing the drop to preventing it.
        """
        _seed_marshal(finalize_gates={'functional_review': 'minimal'})
        _stub_footprint(_FOOTPRINT)

        result = cmd_compose(
            _compose_ns(
                plan_id='ceremony-always-surgical',
                scope_estimate='surgical',
                change_type='bug_fix',
            )
        )

        assert result is not None
        assert result['status'] == 'success'
        bare = _bare(_manifest_phase_6_steps(result))
        assert 'functional-review' in bare
        # Kept by the scope gate's declared-lane immunity...
        assert 'functional-review' in result['scope_gated_finalize_immune']
        assert 'functional-review' not in result['scope_gated_finalize_dropped']
        # ...so the ceremony transform had nothing to re-add.
        assert 'functional-review' not in result['ceremony_finalize_forced_in']
        # The code review declared no lane, so the surgical scope gate drops it:
        # the functional review's setting does not reach the code review.
        assert 'code-review' not in bare
        assert 'code-review' in result['scope_gated_finalize_dropped']

    def test_always_still_readds_a_step_the_scope_gate_dropped(self, plan_context):
        """``always`` remains the re-add path when the step carries NO lane declaration.

        Immunity only covers a step the operator declared a non-``standard`` lane for.
        Here the ``functional_review`` gate is forced in through the ceremony
        channel while the owning step declares no lane, so ``scope_gated_finalize``
        drops it on a surgical plan and the ``always`` transform genuinely re-adds
        it — the mechanism the immunity test above does NOT exercise.
        """
        # Candidate set WITHOUT the functional-review owner, so the step is absent
        # from the seeded steps map (and therefore carries no lane declaration) and
        # the ceremony gate must insert it.
        candidates = [s for s in _phase_6_with_ceremony_steps().split(',') if s != 'functional-review']
        _seed_marshal(candidates=candidates)
        _stub_footprint(_FOOTPRINT)
        # Force the gate value directly — the owning step is absent from the map,
        # so `_seed_marshal` cannot fold the knob onto it.
        # ``_read_finalize_gates`` takes the plan id so it can resolve the gate's
        # lane from the MERGED plan-local-over-marshal step map; the stub accepts
        # (and ignores) it.
        original_gates = _mem._read_finalize_gates
        _mem._read_finalize_gates = lambda _plan_id: {
            'functional_review': 'always',
            'code_review': 'auto',
            'qgate': 'auto',
            'simplify': 'auto',
            'security_audit': 'auto',
        }
        try:
            result = cmd_compose(
                _compose_ns(
                    plan_id='ceremony-always-readd',
                    scope_estimate='surgical',
                    change_type='bug_fix',
                    phase_6_steps=','.join(candidates),
                )
            )
        finally:
            _mem._read_finalize_gates = original_gates

        assert result is not None
        assert result['status'] == 'success'
        assert 'functional-review' in _bare(_manifest_phase_6_steps(result))
        # The canonical insertion form is BARE (aligned with the compose-time
        # canonical-step-key gate) — no `default:`-prefixed id is re-inserted.
        assert 'functional-review' in result['ceremony_finalize_forced_in']

    def test_always_readds_qgate_dropped_by_inactive_prefilter(self, plan_context):
        # Empty footprint → pre_push_quality_gate_inactive drops the qgate step.
        # `always` re-adds it regardless.
        _seed_marshal(finalize_gates={'qgate': 'minimal'})
        _stub_footprint([])

        result = cmd_compose(_compose_ns(plan_id='ceremony-always-qgate'))

        assert result is not None
        assert result['status'] == 'success'
        assert 'pre-push-quality-gate' in _bare(_manifest_phase_6_steps(result))
        assert 'pre-push-quality-gate' in result['ceremony_finalize_forced_in']

    def test_always_is_no_op_when_step_already_present(self, plan_context):
        _seed_marshal(finalize_gates={'code_review': 'minimal'})
        _stub_footprint(_FOOTPRINT)

        # multi_module feature → code-review survives the matrix already present.
        result = cmd_compose(_compose_ns(plan_id='ceremony-always-present'))

        assert result is not None
        assert result['status'] == 'success'
        assert result['ceremony_finalize_forced_in'] == []
        assert 'code-review' in _bare(_manifest_phase_6_steps(result))

    def test_always_inserts_before_plan_mutating_tail(self, plan_context):
        _seed_marshal(finalize_gates={'code_review': 'minimal'})
        _stub_footprint(_FOOTPRINT)

        result = cmd_compose(
            _compose_ns(
                plan_id='ceremony-always-order',
                scope_estimate='surgical',
                change_type='bug_fix',
            )
        )

        assert result is not None
        steps = _manifest_phase_6_steps(result)
        # The kept step must precede archive-plan (plan-mutating tail).
        bare_seq = [next(iter(_bare([s]))) for s in steps]
        assert 'code-review' in bare_seq
        assert 'archive-plan' in bare_seq
        assert bare_seq.index('code-review') < bare_seq.index('archive-plan')


# =============================================================================
# Test: "no push" always wins — a forced `always` never re-adds a push-only step
#
# The mirror image of the cases above: the same force-in path, on a plan whose
# `commit_and_push` is false, must leave the `commit_push_disabled` pre-filter's
# drop standing.
# =============================================================================


# (ceremony gate, the push-only step it force-includes) for the three members of
# `_COMMIT_PUSH_DROP_STEPS` the ceremony gate map covers. `push` itself owns no
# ceremony gate, so it is covered by the all-gates case below instead.
_PUSH_ONLY_GATE_CASES = [
    ('functional_review', 'functional-review'),
    ('code_review', 'code-review'),
    ('qgate', 'pre-push-quality-gate'),
]


def _force_gates(gate: str):
    """Return a ``_read_finalize_gates`` stub forcing ``gate`` to ``always``.

    Used where the owning step is absent from the seeded candidate list, so
    ``_seed_marshal`` cannot fold the knob onto it.
    """
    forced = dict.fromkeys(('functional_review', 'code_review', 'qgate', 'simplify', 'security_audit'), 'auto')
    forced[gate] = 'always'
    return lambda _plan_id: dict(forced)


def _compose_with_forced_gate(plan_id: str, gate: str, step: str, commit_and_push: str | None):
    """Compose a candidate set WITHOUT ``step`` while ``gate`` is forced ``always``."""
    candidates = [s for s in _phase_6_with_ceremony_steps().split(',') if s != step]
    _seed_marshal(candidates=candidates)
    _stub_footprint(_FOOTPRINT)
    original_gates = _mem._read_finalize_gates
    _mem._read_finalize_gates = _force_gates(gate)
    try:
        return cmd_compose(
            _compose_ns(
                plan_id=plan_id,
                phase_6_steps=','.join(candidates),
                commit_and_push=commit_and_push,
            )
        )
    finally:
        _mem._read_finalize_gates = original_gates


class TestCeremonyFinalizeAlwaysRefusedOnLocalOnlyPlan:
    """A local-only plan never gets a push-only step back from a forced ``always``."""

    @pytest.mark.parametrize(('gate', 'step'), _PUSH_ONLY_GATE_CASES)
    def test_always_gate_does_not_readd_the_step_when_push_is_disabled(self, plan_context, gate, step):
        _seed_marshal(finalize_gates={gate: 'minimal'})
        _stub_footprint(_FOOTPRINT)

        result = cmd_compose(_compose_ns(plan_id=f'ceremony-no-push-{step}', commit_and_push='false'))

        assert result is not None
        assert result['status'] == 'success'
        assert step not in _bare(_manifest_phase_6_steps(result))
        assert step not in result['ceremony_finalize_forced_in']

    @pytest.mark.parametrize(('gate', 'step'), _PUSH_ONLY_GATE_CASES)
    def test_always_gate_is_refused_when_the_step_is_absent_and_push_is_disabled(self, plan_context, gate, step):
        """The guard covers the INSERTION path: the step is absent, so ``always`` would add it."""
        result = _compose_with_forced_gate(f'ceremony-no-push-insert-{step}', gate, step, 'false')

        assert result is not None
        assert result['status'] == 'success'
        assert step not in _bare(_manifest_phase_6_steps(result))
        assert step not in result['ceremony_finalize_forced_in']

    @pytest.mark.parametrize(('gate', 'step'), _PUSH_ONLY_GATE_CASES)
    def test_always_gate_still_inserts_the_step_when_the_plan_pushes(self, plan_context, gate, step):
        """Control for the refusal above: same absent step, same gate, plan pushes → inserted."""
        result = _compose_with_forced_gate(f'ceremony-push-insert-{step}', gate, step, None)

        assert result is not None
        assert result['status'] == 'success'
        assert step in _bare(_manifest_phase_6_steps(result))
        assert step in result['ceremony_finalize_forced_in']

    def test_push_stays_dropped_whatever_the_gates_say(self, plan_context):
        """`push` owns no ceremony gate, so the drop the pre-filter made must survive every gate."""
        _seed_marshal(
            finalize_gates={
                'functional_review': 'minimal',
                'code_review': 'minimal',
                'qgate': 'minimal',
                'simplify': 'minimal',
                'security_audit': 'minimal',
            }
        )
        _stub_footprint(_FOOTPRINT)

        result = cmd_compose(_compose_ns(plan_id='ceremony-no-push-all-gates', commit_and_push='false'))

        assert result is not None
        assert result['status'] == 'success'
        bare = _bare(_manifest_phase_6_steps(result))
        for step in ('push', 'pre-push-quality-gate', 'functional-review', 'code-review'):
            assert step not in bare

    def test_a_gate_outside_the_push_only_set_is_still_forced_in_when_push_is_disabled(self, plan_context):
        """The guard is keyed on the step, not on the gate value: a non-push gate still adds."""
        _seed_marshal(finalize_gates={'simplify': 'minimal'})
        _stub_footprint(_FOOTPRINT)

        # `analysis` makes simplify_inactive drop the step, so `always` must re-add it.
        result = cmd_compose(
            _compose_ns(plan_id='ceremony-no-push-simplify', change_type='analysis', commit_and_push='false')
        )

        assert result is not None
        assert result['status'] == 'success'
        assert 'finalize-step-simplify' in _bare(_manifest_phase_6_steps(result))
        assert 'finalize-step-simplify' in result['ceremony_finalize_forced_in']
