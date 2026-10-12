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
# Test: generic consuming-project review form (default:functional-review)
# =============================================================================


class TestCeremonyFinalizeGenericReviewForm:
    """A consuming project lists the GENERIC ``default:functional-review`` step
    rather than the bare id. The composer `canonicalize_step_key`-normalizes it
    to bare ``functional-review`` at intake, so the ``functional_review`` gate's
    match-set MUST recognize that bare form — otherwise ``never`` cannot drop it
    and ``always`` re-inserts a duplicate.
    """

    def _generic_candidates(self) -> list[str]:
        # The generic consuming-project form replaces the bare default candidate.
        # The ``functional_review`` gate value is read from the
        # ``default:functional-review`` owner — which IS this generic form — so
        # listing it once serves as both the candidate and the knob owner in the
        # seeded steps map.
        return [s for s in DEFAULT_PHASE_6_STEPS if s != 'functional-review'] + [
            'pre-push-quality-gate',
            'default:functional-review',
        ]

    def test_never_drops_generic_default_form(self, plan_context):
        candidates = self._generic_candidates()
        _seed_marshal(finalize_gates={'functional_review': 'off'}, candidates=candidates)
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
        assert 'functional-review' not in _bare(_manifest_phase_6_steps(result))

    def test_always_does_not_duplicate_generic_default_form(self, plan_context):
        candidates = self._generic_candidates()
        _seed_marshal(finalize_gates={'functional_review': 'minimal'}, candidates=candidates)
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
        occurrences = sum(1 for s in steps if next(iter(_bare([s]))) == 'functional-review')
        assert occurrences == 1
        assert 'functional-review' not in result['ceremony_finalize_forced_in']


# =============================================================================
# Test: the functional_review gate — the functional review's own setting
# =============================================================================


class TestCeremonyFinalizeFunctionalReviewGate:
    """``functional_review`` is decided by ``default:functional-review``'s own ``lane``.

    ``off`` drops the step and ``minimal`` keeps it — even on a surgical scope,
    where the scope gate would otherwise drop it. Its independence from the code
    review's ``code_review`` gate is asserted in both directions by
    ``TestCeremonyFinalizeCodeReviewGate`` below.
    """

    def _candidates(self) -> list[str]:
        # DEFAULT_PHASE_6_STEPS carries the bare functional-review and code-review.
        return list(DEFAULT_PHASE_6_STEPS) + ['pre-push-quality-gate']

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


# =============================================================================
# Test: the code_review gate — the code review's own setting
# =============================================================================


class TestCeremonyFinalizeCodeReviewGate:
    """``code_review`` is decided by ``default:code-review``'s own ``lane``.

    ``off`` drops the step and ``minimal`` keeps it — even on a surgical scope,
    where the scope gate would otherwise drop it. The two review settings are
    independent in both directions: switching ``code_review`` off leaves the
    functional review selected, and switching ``functional_review`` off leaves the
    code review selected.
    """

    def _candidates(self) -> list[str]:
        # DEFAULT_PHASE_6_STEPS carries the bare functional-review and code-review.
        return list(DEFAULT_PHASE_6_STEPS) + ['pre-push-quality-gate']

    def _compose(self, plan_id: str, gates: dict[str, object], scope_estimate: str = 'multi_module') -> set[str]:
        candidates = self._candidates()
        _seed_marshal(finalize_gates=gates, candidates=candidates)
        _stub_footprint(_FOOTPRINT)
        result = cmd_compose(
            _compose_ns(plan_id=plan_id, scope_estimate=scope_estimate, phase_6_steps=','.join(candidates))
        )
        assert result is not None
        assert result['status'] == 'success'
        assert result['ceremony_finalize_gates']['code_review'] in ('never', 'always', 'auto')
        return set(_bare(_manifest_phase_6_steps(result)))

    def test_both_reviews_are_default_candidates(self):
        """Control: both reviews reach the composer without any gate declaration."""
        assert {'functional-review', 'code-review'} <= set(DEFAULT_PHASE_6_STEPS)

    def test_off_drops_code_review(self, plan_context):
        steps = self._compose('ceremony-code-off', {'code_review': 'off'})
        assert 'code-review' not in steps

    def test_minimal_keeps_code_review(self, plan_context):
        steps = self._compose('ceremony-code-minimal', {'code_review': 'minimal'})
        assert 'code-review' in steps

    def test_minimal_keeps_code_review_past_the_surgical_scope_gate(self, plan_context):
        steps = self._compose('ceremony-code-surgical', {'code_review': 'minimal'}, 'surgical')
        assert 'code-review' in steps

    def test_surgical_scope_drops_code_review_without_a_declared_lane(self, plan_context):
        """Control for the test above: without the declaration the scope gate does drop it."""
        steps = self._compose('ceremony-code-surgical-auto', {'code_review': 'standard'}, 'surgical')
        assert 'code-review' not in steps

    def test_code_review_off_leaves_functional_review_selected(self, plan_context):
        steps = self._compose('ceremony-code-off-functional-kept', {'code_review': 'off'})
        assert 'code-review' not in steps
        assert 'functional-review' in steps

    def test_functional_review_off_leaves_code_review_selected(self, plan_context):
        steps = self._compose('ceremony-functional-off-code-kept', {'functional_review': 'off'})
        assert 'functional-review' not in steps
        assert 'code-review' in steps
