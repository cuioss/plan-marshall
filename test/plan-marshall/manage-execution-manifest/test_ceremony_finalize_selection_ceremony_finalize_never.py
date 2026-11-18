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


# =============================================================================
# Test: "no push" always wins — a forced `always` never re-adds a push-only step
#
# Both gate values sit in this file because both pin what a forced gate value may
# NOT do: `never` may not keep a step, and `always` may not put a push-only step
# back on a plan that does not push. The reverse direction — a forced `always`
# genuinely re-adding a step on a PUSHING plan — lives beside the other force-in
# cases in `test_ceremony_finalize_selection_ceremony_finalize_always.py`.
# =============================================================================


# (ceremony gate, the push-only step it force-includes) for the three members of
# `_COMMIT_PUSH_DROP_STEPS` the ceremony gate map covers. `push` itself owns no
# ceremony gate, so it is covered by the all-gates case below instead.
_PUSH_ONLY_GATE_CASES = [
    ('functional_review', 'functional-review'),
    ('code_review', 'code-review'),
    ('qgate', 'pre-push-quality-gate'),
]


def _force_gates(gate: str) -> object:
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
