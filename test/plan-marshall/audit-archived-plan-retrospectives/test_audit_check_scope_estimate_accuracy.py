#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""``scope-estimate`` accuracy — the estimated-versus-actual scope verdict and the
edge cases where an estimate is unavailable.

``check_scope_estimate`` grades the REALIZED footprint, resolved through the
``realized_footprint`` -> ``merge_commit_sha`` -> ``modified_files`` tier order,
and falls back to the declared ``affected_files`` count ONLY when no tier
resolves. See ``test_audit_footprint_tier_resolution.py`` for the tier order and
the five consuming sites; this file covers the band verdict layered on top.
"""

from typing import Any

from _audit_fixtures import audit

from conftest import PROJECT_ROOT


def _scope_inputs(
    *,
    scope_estimate: str | None,
    realized: int | None = None,
    declared: int = 0,
) -> Any:
    """Build a PlanInputs carrying only the scope-estimate-relevant counts.

    ``check_scope_estimate`` reads ``scope_estimate`` plus the footprint counts
    already collected onto ``PlanInputs`` (it does NOT re-read disk), so the
    instance is constructed directly rather than materialised.

    ⛔ ``realized`` is the cardinality of the RESOLVED footprint, and ``None``
    means no tier resolved at all — the two states a bare count cannot tell apart.
    The tier fields are derived here rather than passed independently so this
    helper cannot express a state ``collect_inputs`` could never produce: that
    function reads ``modified_files_count`` and the tier from the SAME references
    dict, so a positive count with an unresolved tier is unreachable in
    production. A fixture asserting that combination pins the pre-tier reading,
    not the shipped contract.
    """
    resolved = realized is not None
    count = realized if resolved else 0
    return audit.PlanInputs(
        plan_id='scope-plan',
        plan_dir=PROJECT_ROOT / '.plan' / 'temp' / 'nonexistent-scope-plan',
        scope_estimate=scope_estimate,
        affected_files_count=declared,
        # the legacy key is the LAST tier, so it carries the same count it resolved
        modified_files_count=count,
        realized_footprint_count=count,
        footprint_tier='modified_files' if resolved else audit.FOOTPRINT_TIER_UNRESOLVED,
    )


class TestCheckScopeEstimate:
    """``check_scope_estimate`` flags a declared scope band the realized file count
    falls outside, grades the resolved footprint over the declared one, and
    tolerates an unbanded / absent declaration."""

    def test_in_band_surgical_not_flagged(self):
        # surgical band is [1, 3]; actual 2 sits inside.
        inputs = _scope_inputs(scope_estimate='surgical', realized=2)

        result = audit.check_scope_estimate(inputs)

        assert result['mismatch'] == ''
        assert result['declared_scope'] == 'surgical'
        assert result['actual_file_count'] == 2

    def test_surgical_overshoot_flagged(self):
        # actual 9 exceeds the surgical [1, 3] upper bound.
        inputs = _scope_inputs(scope_estimate='surgical', realized=9)

        result = audit.check_scope_estimate(inputs)

        # the mismatch names the band and the actual count
        assert 'declared=surgical' in result['mismatch']
        assert 'actual=9' in result['mismatch']

    def test_below_band_low_bound_flagged(self):
        # single_module band is [1, 15]; a RESOLVED-empty footprint sits below it.
        inputs = _scope_inputs(scope_estimate='single_module', realized=0, declared=0)

        result = audit.check_scope_estimate(inputs)

        # actual 0 < low 1 → flagged
        assert 'declared=single_module' in result['mismatch']
        assert 'actual=0' in result['mismatch']

    def test_unbounded_upper_band_never_overshoots(self):
        # multi_module band is [5, None]; a large actual cannot overshoot.
        inputs = _scope_inputs(scope_estimate='multi_module', realized=500)

        result = audit.check_scope_estimate(inputs)

        # no upper bound, actual >= low → not flagged
        assert result['mismatch'] == ''

    def test_realized_count_preferred_over_declared(self):
        # the resolved footprint (post-execution truth) 2 wins over declared 99.
        inputs = _scope_inputs(scope_estimate='surgical', realized=2, declared=99)

        result = audit.check_scope_estimate(inputs)

        # the in-band realized count is used, not the out-of-band declared one
        assert result['actual_file_count'] == 2
        assert result['mismatch'] == ''

    def test_declared_used_only_when_no_tier_resolves(self):
        # nothing resolved → the declared 7 is the only number there is, and it
        # overshoots surgical [1, 3].
        inputs = _scope_inputs(scope_estimate='surgical', realized=None, declared=7)

        result = audit.check_scope_estimate(inputs)

        # fallback count is used and flags the overshoot
        assert result['actual_file_count'] == 7
        assert 'actual=7' in result['mismatch']

    def test_a_resolved_empty_footprint_does_not_fall_back_to_declared(self):
        """⛔ The discriminating pair for the defect the tier partition removes.

        Same declared count as the test above, but here a tier DID resolve and
        named no path. The count must stay `0` rather than borrowing the declared
        7 — against a `realized or declared` reading this assertion fails with 7.
        """
        inputs = _scope_inputs(scope_estimate='surgical', realized=0, declared=7)

        result = audit.check_scope_estimate(inputs)

        assert result['actual_file_count'] == 0
        assert 'actual=0' in result['mismatch']

    def test_unmapped_scope_string_flagged(self):
        # a declared scope with no band mapping in SCOPE_FILE_BANDS.
        inputs = _scope_inputs(scope_estimate='gigantic', realized=4)

        result = audit.check_scope_estimate(inputs)

        # the no-band-mapping branch fires
        assert 'no band mapping' in result['mismatch']
        assert result['declared_scope'] == 'gigantic'

    def test_absent_scope_never_flagged(self):
        # no declared scope at all.
        inputs = _scope_inputs(scope_estimate=None, realized=42)

        result = audit.check_scope_estimate(inputs)

        # empty declared scope short-circuits both branches
        assert result['declared_scope'] == ''
        assert result['mismatch'] == ''


class TestEmittedCountBasis:
    """⛔ The count is emitted WITH the source that produced it.

    `actual_file_count: 0` is produced by two different states. Without the basis
    the emitted row cannot be read, which is the same ambiguity the tier partition
    removed one layer down inside `graded_file_count`.
    """

    def test_a_resolved_zero_and_an_unresolved_zero_are_distinguishable(self):
        resolved_empty = audit.check_scope_estimate(
            _scope_inputs(scope_estimate='surgical', realized=0, declared=0)
        )
        nothing_resolved = audit.check_scope_estimate(
            _scope_inputs(scope_estimate='surgical', realized=None, declared=0)
        )

        # identical counts...
        assert resolved_empty['actual_file_count'] == 0
        assert nothing_resolved['actual_file_count'] == 0
        # ...told apart only by the basis, which is why it is emitted
        assert resolved_empty['count_basis'] == 'modified_files'
        assert nothing_resolved['count_basis'] == audit.COUNT_BASIS_DECLARED
        assert resolved_empty['count_basis'] != nothing_resolved['count_basis']

    def test_the_basis_travels_into_the_mismatch_string(self):
        result = audit.check_scope_estimate(
            _scope_inputs(scope_estimate='surgical', realized=None, declared=0)
        )

        # a flagged row explains which source its count came from
        assert 'actual=0' in result['mismatch']
        assert f'basis={audit.COUNT_BASIS_DECLARED}' in result['mismatch']

    def test_the_basis_names_the_answering_tier_when_one_resolves(self):
        result = audit.check_scope_estimate(
            _scope_inputs(scope_estimate='surgical', realized=2, declared=99)
        )

        assert result['count_basis'] == 'modified_files'
        assert result['count_basis'] in audit.FOOTPRINT_TIERS

    def test_the_declared_basis_is_not_a_tier_name(self):
        # the negative control: `declared` names the ABSENCE of a tier, so it must
        # never be confusable with one that answered.
        assert audit.COUNT_BASIS_DECLARED not in audit.FOOTPRINT_TIERS
        assert audit.COUNT_BASIS_DECLARED != audit.FOOTPRINT_TIER_UNRESOLVED
