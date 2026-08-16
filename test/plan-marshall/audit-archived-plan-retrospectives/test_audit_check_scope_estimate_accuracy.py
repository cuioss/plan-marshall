#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""``scope-estimate`` accuracy — the estimated-versus-actual scope verdict and the
edge cases where an estimate is unavailable.
"""

from typing import Any

from _audit_fixtures import audit

from conftest import PROJECT_ROOT


def _scope_inputs(
    *,
    scope_estimate: str | None,
    modified: int = 0,
    affected: int = 0,
) -> Any:
    """Build a PlanInputs carrying only the scope-estimate-relevant counts.

    ``check_scope_estimate`` reads ``scope_estimate`` plus the modified/affected
    file counts already collected onto ``PlanInputs`` (it does NOT re-read disk),
    so the instance is constructed directly rather than materialised.
    """
    return audit.PlanInputs(
        plan_id='scope-plan',
        plan_dir=PROJECT_ROOT / '.plan' / 'temp' / 'nonexistent-scope-plan',
        scope_estimate=scope_estimate,
        modified_files_count=modified,
        affected_files_count=affected,
    )


class TestCheckScopeEstimate:
    """``check_scope_estimate`` flags a declared scope band the actual touched
    file count falls outside, prefers modified over affected counts, and tolerates
    an unbanded / absent declaration."""

    def test_in_band_surgical_not_flagged(self):
        # surgical band is [1, 3]; actual 2 sits inside.
        inputs = _scope_inputs(scope_estimate='surgical', modified=2)

        result = audit.check_scope_estimate(inputs)

        assert result['mismatch'] == ''
        assert result['declared_scope'] == 'surgical'
        assert result['actual_file_count'] == 2

    def test_surgical_overshoot_flagged(self):
        # actual 9 exceeds the surgical [1, 3] upper bound.
        inputs = _scope_inputs(scope_estimate='surgical', modified=9)

        result = audit.check_scope_estimate(inputs)

        # the mismatch names the band and the actual count
        assert 'declared=surgical' in result['mismatch']
        assert 'actual=9' in result['mismatch']

    def test_below_band_low_bound_flagged(self):
        # single_module band is [1, 15]; actual 0 sits below the low bound.
        inputs = _scope_inputs(scope_estimate='single_module', modified=0, affected=0)

        result = audit.check_scope_estimate(inputs)

        # actual 0 < low 1 → flagged
        assert 'declared=single_module' in result['mismatch']
        assert 'actual=0' in result['mismatch']

    def test_unbounded_upper_band_never_overshoots(self):
        # multi_module band is [5, None]; a large actual cannot overshoot.
        inputs = _scope_inputs(scope_estimate='multi_module', modified=500)

        result = audit.check_scope_estimate(inputs)

        # no upper bound, actual >= low → not flagged
        assert result['mismatch'] == ''

    def test_modified_count_preferred_over_affected(self):
        # modified (post-execution truth) 2 wins over affected 99.
        inputs = _scope_inputs(scope_estimate='surgical', modified=2, affected=99)

        result = audit.check_scope_estimate(inputs)

        # the in-band modified count is used, not the out-of-band affected
        assert result['actual_file_count'] == 2
        assert result['mismatch'] == ''

    def test_affected_used_when_modified_zero(self):
        # modified 0 falls back to affected 7 (overshoots surgical [1, 3]).
        inputs = _scope_inputs(scope_estimate='surgical', modified=0, affected=7)

        result = audit.check_scope_estimate(inputs)

        # fallback count is used and flags the overshoot
        assert result['actual_file_count'] == 7
        assert 'actual=7' in result['mismatch']

    def test_unmapped_scope_string_flagged(self):
        # a declared scope with no band mapping in SCOPE_FILE_BANDS.
        inputs = _scope_inputs(scope_estimate='gigantic', modified=4)

        result = audit.check_scope_estimate(inputs)

        # the no-band-mapping branch fires
        assert 'no band mapping' in result['mismatch']
        assert result['declared_scope'] == 'gigantic'

    def test_absent_scope_never_flagged(self):
        # no declared scope at all.
        inputs = _scope_inputs(scope_estimate=None, modified=42)

        result = audit.check_scope_estimate(inputs)

        # empty declared scope short-circuits both branches
        assert result['declared_scope'] == ''
        assert result['mismatch'] == ''
