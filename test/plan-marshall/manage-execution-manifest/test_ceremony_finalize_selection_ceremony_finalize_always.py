# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_ceremony_finalize_selection_fixtures import (
    _FOOTPRINT,
    _bare,
    _compose_ns,
    _manifest_phase_6_steps,
    _mem,
    _phase_6_with_ceremony_steps,
    _seed_marshal,
    _stub_footprint,
    cmd_compose,
)

# =============================================================================
# Test: always — force-include (overriding scope_gated_finalize)
# =============================================================================


class TestCeremonyFinalizeAlways:
    """``always`` re-adds the gate's step even when a pre-filter dropped it."""

    def test_self_review_survives_surgical_scope_gate_via_declared_lane_immunity(self, plan_context):
        """A ``minimal`` self_review gate keeps the step on a surgical plan — by
        IMMUNITY at the scope gate, not by an ``always`` re-add.

        Setting the gate to ``minimal`` writes ``lane: minimal`` on
        ``default:pre-submission-self-review``, which is an explicit non-``auto``
        lane declaration. ``scope_gated_finalize`` therefore never drops the step,
        so by the time the ceremony transform runs there is nothing to re-add and
        ``always`` is correctly a no-op. The operator-visible outcome — the step
        runs — is unchanged; the mechanism that delivers it moved one stage
        earlier, from undoing the drop to preventing it.
        """
        _seed_marshal(finalize_gates={'self_review': 'minimal'})
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
        assert 'pre-submission-self-review' in bare
        # Kept by the scope gate's declared-lane immunity...
        assert 'pre-submission-self-review' in result['scope_gated_finalize_immune']
        assert 'pre-submission-self-review' not in result['scope_gated_finalize_dropped']
        # ...so the ceremony transform had nothing to re-add.
        assert 'pre-submission-self-review' not in result['ceremony_finalize_forced_in']

    def test_always_still_readds_a_step_the_scope_gate_dropped(self, plan_context):
        """``always`` remains the re-add path when the step carries NO lane declaration.

        Immunity only covers a step the operator declared a non-``standard`` lane for.
        Here the ``self_review`` gate is forced in through the ceremony channel
        while the owning step declares no lane, so ``scope_gated_finalize`` drops
        it on a surgical plan and the ``always`` transform genuinely re-adds it —
        the mechanism the immunity test above does NOT exercise.
        """
        # Candidate set WITHOUT the self-review owner, so the step is absent from
        # the seeded steps map (and therefore carries no lane declaration) and the
        # ceremony gate must insert it.
        candidates = [s for s in _phase_6_with_ceremony_steps().split(',') if s != 'default:pre-submission-self-review']
        _seed_marshal(candidates=candidates)
        _stub_footprint(_FOOTPRINT)
        # Force the gate value directly — the owning step is absent from the map,
        # so `_seed_marshal` cannot fold the knob onto it.
        # ``_read_finalize_gates`` takes the plan id so it can resolve the gate's
        # lane from the MERGED plan-local-over-marshal step map; the stub accepts
        # (and ignores) it.
        original_gates = _mem._read_finalize_gates
        _mem._read_finalize_gates = lambda _plan_id: {
            'self_review': 'always',
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
        assert 'pre-submission-self-review' in _bare(_manifest_phase_6_steps(result))
        # The canonical insertion form is BARE (aligned with the compose-time
        # canonical-step-key gate) — no `default:`-prefixed id is re-inserted.
        assert 'pre-submission-self-review' in result['ceremony_finalize_forced_in']

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
        _seed_marshal(finalize_gates={'self_review': 'minimal'})
        _stub_footprint(_FOOTPRINT)

        # multi_module feature → self_review survives the matrix already present.
        result = cmd_compose(_compose_ns(plan_id='ceremony-always-present'))

        assert result is not None
        assert result['status'] == 'success'
        assert result['ceremony_finalize_forced_in'] == []
        assert 'pre-submission-self-review' in _bare(_manifest_phase_6_steps(result))

    def test_always_inserts_before_plan_mutating_tail(self, plan_context):
        _seed_marshal(finalize_gates={'self_review': 'minimal'})
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
        # The re-added step must precede archive-plan (plan-mutating tail).
        bare_seq = [next(iter(_bare([s]))) for s in steps]
        assert 'pre-submission-self-review' in bare_seq
        assert 'archive-plan' in bare_seq
        assert bare_seq.index('pre-submission-self-review') < bare_seq.index('archive-plan')
