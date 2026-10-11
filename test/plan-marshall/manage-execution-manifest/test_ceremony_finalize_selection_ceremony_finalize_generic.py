# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_ceremony_finalize_selection_fixtures import (
    _FOOTPRINT,
    DEFAULT_PHASE_6_STEPS,
    _bare,
    _compose_ns,
    _manifest_phase_6_steps,
    _restore_footprint_resolver,
    _seed_marshal,
    _stub_footprint,
    cmd_compose,
)

# =============================================================================
# Test: generic consuming-project self_review form (default:pre-submission-self-review)
# =============================================================================


class TestCeremonyFinalizeGenericSelfReviewForm:
    """A consuming project lists the GENERIC ``default:pre-submission-self-review``
    step (not the meta-project ``project:``-prefixed wrapper). The composer
    `canonicalize_step_key`-normalizes it to bare ``pre-submission-self-review``
    at intake, so the ``self_review`` gate's match-set MUST recognize that bare
    form — otherwise ``never`` cannot drop it and ``always`` re-inserts a
    duplicate. Regression for the match-set that omitted the normalized form
    after the canonical insertion form was generalized to ``default:``.
    """

    def _generic_candidates(self) -> list[str]:
        # The generic consuming-project self-review form. The ``self_review`` gate
        # value is read from the ``default:pre-submission-self-review`` owner —
        # which IS this generic form — so listing it once serves as both the
        # candidate and the knob owner in the seeded steps map.
        return list(DEFAULT_PHASE_6_STEPS) + [
            'pre-push-quality-gate',
            'default:pre-submission-self-review',
        ]

    def test_never_drops_generic_default_form(self, plan_context):
        candidates = self._generic_candidates()
        _seed_marshal(finalize_gates={'self_review': 'off'}, candidates=candidates)
        _stub_footprint(_FOOTPRINT)

        result = cmd_compose(
            _compose_ns(
                plan_id='ceremony-never-generic',
                phase_6_steps=','.join(candidates),
            )
        )

        assert result is not None
        assert result['status'] == 'success'
        # The normalized bare form must be dropped by `never`.
        assert 'pre-submission-self-review' not in _bare(_manifest_phase_6_steps(result))

    def test_always_does_not_duplicate_generic_default_form(self, plan_context):
        candidates = self._generic_candidates()
        _seed_marshal(finalize_gates={'self_review': 'minimal'}, candidates=candidates)
        _stub_footprint(_FOOTPRINT)

        result = cmd_compose(
            _compose_ns(
                plan_id='ceremony-always-generic',
                phase_6_steps=','.join(candidates),
            )
        )

        assert result is not None
        assert result['status'] == 'success'
        # `always` must see the already-present normalized form and NOT re-insert
        # a duplicate. Count raw occurrences (a set would mask the duplicate).
        steps = _manifest_phase_6_steps(result)
        occurrences = sum(1 for s in steps if next(iter(_bare([s]))) == 'pre-submission-self-review')
        assert occurrences == 1
        assert 'pre-submission-self-review' not in result['ceremony_finalize_forced_in']


# =============================================================================
# Test: the functional_review gate — the functional review's own setting
# =============================================================================


class TestCeremonyFinalizeFunctionalReviewGate:
    """``functional_review`` is decided by ``default:functional-review``'s own ``lane``.

    ``off`` drops the step and ``minimal`` keeps it — even on a surgical scope,
    where the scope gate would otherwise drop it. The gate is independent of the
    structural self-review's ``self_review`` gate in both directions: switching one
    off leaves the other review selected.
    """

    def _candidates(self) -> list[str]:
        # DEFAULT_PHASE_6_STEPS carries the bare functional-review; the generic
        # self-review form rides along so the two gates can be told apart.
        return list(DEFAULT_PHASE_6_STEPS) + ['pre-push-quality-gate', 'default:pre-submission-self-review']

    def _compose(self, plan_id: str, gates: dict[str, object], scope_estimate: str = 'multi_module') -> set[str]:
        candidates = self._candidates()
        _seed_marshal(finalize_gates=gates, candidates=candidates)
        _stub_footprint(_FOOTPRINT)
        result = cmd_compose(
            _compose_ns(plan_id=plan_id, scope_estimate=scope_estimate, phase_6_steps=','.join(candidates))
        )
        assert result is not None
        assert result['status'] == 'success'
        assert result['ceremony_finalize_gates']['functional_review'] in ('never', 'always', 'auto')
        return set(_bare(_manifest_phase_6_steps(result)))

    def test_off_drops_functional_review(self, plan_context):
        steps = self._compose('ceremony-functional-off', {'functional_review': 'off'})
        assert 'functional-review' not in steps
        # The structural self-review is governed by its own gate and stays selected.
        assert 'pre-submission-self-review' in steps

    def test_minimal_keeps_functional_review(self, plan_context):
        steps = self._compose('ceremony-functional-minimal', {'functional_review': 'minimal'})
        assert 'functional-review' in steps

    def test_minimal_keeps_functional_review_past_the_surgical_scope_gate(self, plan_context):
        steps = self._compose('ceremony-functional-surgical', {'functional_review': 'minimal'}, 'surgical')
        assert 'functional-review' in steps

    def test_surgical_scope_drops_functional_review_without_a_declared_lane(self, plan_context):
        """Control for the test above: without the declaration the scope gate does drop it."""
        steps = self._compose('ceremony-functional-surgical-auto', {'functional_review': 'standard'}, 'surgical')
        assert 'functional-review' not in steps

    def test_self_review_off_leaves_functional_review_selected(self, plan_context):
        steps = self._compose('ceremony-self-review-off', {'self_review': 'off'})
        assert 'pre-submission-self-review' not in steps
        assert 'functional-review' in steps
