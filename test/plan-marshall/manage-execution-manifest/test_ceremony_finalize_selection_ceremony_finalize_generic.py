# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_ceremony_finalize_selection_fixtures import (
    _FOOTPRINT,
    DEFAULT_PHASE_6_STEPS,
    _bare,
    _compose_ns,
    _manifest_phase_6_steps,
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
