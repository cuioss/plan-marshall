# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_ceremony_finalize_selection_fixtures import (
    _FOOTPRINT,
    _bare,
    _compose_ns,
    _manifest_phase_6_steps,
    _phase_6_with_ceremony_steps,
    _seed_marshal,
    _stub_footprint,
    cmd_compose,
)

# =============================================================================
# Test: never — force-drop
# =============================================================================


class TestCeremonyFinalizeNever:
    """``never`` drops the gate's finalize step from phase_6.steps."""

    def test_never_drops_each_gate_step(self, plan_context):
        _seed_marshal(finalize_gates={'self_review': 'off', 'qgate': 'off'})
        _stub_footprint(_FOOTPRINT)

        result = cmd_compose(_compose_ns(plan_id='ceremony-never-all'))

        assert result is not None
        assert result['status'] == 'success'
        bare = _bare(_manifest_phase_6_steps(result))
        assert 'pre-submission-self-review' not in bare
        assert 'pre-push-quality-gate' not in bare
        forced_out = set(result['ceremony_finalize_forced_out'])
        assert 'pre-submission-self-review' in forced_out
        assert 'pre-push-quality-gate' in forced_out

    def test_never_is_no_op_when_step_already_absent(self, plan_context):
        # Candidate set EXCLUDES self_review; never self_review is a no-op.
        candidates = [s for s in _phase_6_with_ceremony_steps().split(',') if s != 'default:pre-submission-self-review']
        # The seeded steps map IS the candidate list, so it must match the
        # composed candidate set (self_review owner excluded).
        _seed_marshal(finalize_gates={'self_review': 'off'}, candidates=candidates)
        _stub_footprint(_FOOTPRINT)

        result = cmd_compose(_compose_ns(plan_id='ceremony-never-absent', phase_6_steps=','.join(candidates)))

        assert result is not None
        assert result['status'] == 'success'
        assert result['ceremony_finalize_forced_out'] == []

    def test_never_preserves_automated_review(self, plan_context):
        _seed_marshal(
            finalize_gates={'self_review': 'off', 'qgate': 'off'},
            ci_provider='github',
        )
        _stub_footprint(_FOOTPRINT)

        result = cmd_compose(_compose_ns(plan_id='ceremony-never-bot'))

        assert result is not None
        assert result['status'] == 'success'
        # The bot-review invariant is orthogonal — automatic-review stays.
        assert 'automatic-review' in _bare(_manifest_phase_6_steps(result))
