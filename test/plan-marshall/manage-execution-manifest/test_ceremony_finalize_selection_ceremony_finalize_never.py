# SPDX-License-Identifier: FSL-1.1-ALv2

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

_apply_ceremony_finalize_selection = _mem._apply_ceremony_finalize_selection

# =============================================================================
# Test: never — force-drop
# =============================================================================


class TestCeremonyFinalizeNever:
    """``never`` drops the gate's finalize step from phase_6.steps."""

    def test_never_drops_each_gate_step(self, plan_context):
        _seed_marshal(finalize_gates={'functional_review': 'off', 'code_review': 'off', 'qgate': 'off'})
        _stub_footprint(_FOOTPRINT)

        result = cmd_compose(_compose_ns(plan_id='ceremony-never-all'))

        assert result is not None
        assert result['status'] == 'success'
        bare = _bare(_manifest_phase_6_steps(result))
        assert 'functional-review' not in bare
        assert 'code-review' not in bare
        assert 'pre-push-quality-gate' not in bare
        forced_out = set(result['ceremony_finalize_forced_out'])
        assert 'functional-review' in forced_out
        assert 'code-review' in forced_out
        assert 'pre-push-quality-gate' in forced_out

    def test_never_is_no_op_when_step_already_absent(self):
        """A ``never`` gate whose step is not a candidate changes nothing and reports nothing.

        The transform is driven directly with a ``never`` value: through ``compose``
        an absent owner step carries no ``lane`` override, so the gate would resolve
        to ``auto`` and the ``never`` branch would never be entered.
        """
        candidates = [s for s in _phase_6_with_ceremony_steps().split(',') if s != 'code-review']
        steps = list(candidates)

        forced_in, forced_out = _apply_ceremony_finalize_selection(steps, {'code_review': 'never'})

        assert (forced_in, forced_out) == ([], [])
        assert steps == candidates

    def test_never_drops_the_step_when_present(self):
        """Control for the no-op case above: the same ``never`` value drops a present step."""
        candidates = _phase_6_with_ceremony_steps().split(',')
        assert 'code-review' in candidates, 'control: the candidate set must carry the code review'
        steps = list(candidates)

        _, forced_out = _apply_ceremony_finalize_selection(steps, {'code_review': 'never'})

        assert forced_out == [{'gate': 'code_review', 'step': 'code-review'}]
        assert 'code-review' not in steps

    def test_never_preserves_automated_review(self, plan_context):
        _seed_marshal(
            finalize_gates={'functional_review': 'off', 'code_review': 'off', 'qgate': 'off'},
            ci_provider='github',
        )
        _stub_footprint(_FOOTPRINT)

        result = cmd_compose(_compose_ns(plan_id='ceremony-never-bot'))

        assert result is not None
        assert result['status'] == 'success'
        # The bot-review invariant is orthogonal — automatic-review stays.
        assert 'automatic-review' in _bare(_manifest_phase_6_steps(result))
