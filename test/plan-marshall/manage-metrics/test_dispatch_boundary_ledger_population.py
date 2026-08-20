#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""D5 tests for the dispatch-boundary ledger as a DECLARED, commensurable population.

Plan 060 (code-intelligence-substrate) — the dispatch-boundary ledger publishes a
coverage figure whose numerator (`dispatch_boundary_rows_recorded`, written by
`record-dispatch-boundary`) and denominator (`subagent_samples`, from enrich's
transcript walk) are drawn from DIFFERENT producers. This suite pins the three
corrected behaviours:

- **D5(a)** — a coverage figure whose numerator EXCEEDS its denominator renders as
  a loud FAILURE that names both populations, never `complete`. (Regression:
  fails pre-fix, where `rows > samples` fell through to "— complete".)
- **D5(b)** — the non-registering dispatch classes are named in an explicit
  exclusion list the coverage figure references (the DECLARED population).
  (Regression: fails pre-fix, where no such declaration exists.)
- **D5(c)** — the reconciliation comparator annotates the three-way distinction
  (smaller / equal / larger) truthfully; exact agreement reads as agreement, not
  as a strict inequality. (Regression: fails pre-fix, where every non-total_tokens
  winner is annotated "> total_tokens" regardless of the true relation.)

Plus a negative control for D3: a phase that dispatched (has `subagent_samples`)
but recorded no boundary is surfaced via the declared exclusion list rather than a
silently shrunk denominator.

The D5(c) three-way test carries one CHARACTERIZATION arm (the `larger` relation,
which already renders correctly today) alongside the two regression arms
(`equal`, `smaller`); the whole test still fails pre-fix because the regression
arms do.
"""

# ruff: noqa: I001
import importlib.util

import pytest

from _manage_metrics_fixtures import ns_generate, SCRIPT_PATH

# kebab-case filename — load via importlib under a unique module name.
_spec = importlib.util.spec_from_file_location('manage_metrics_boundary_pop', SCRIPT_PATH)
assert _spec is not None and _spec.loader is not None
manage_metrics = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(manage_metrics)

cmd_generate = manage_metrics.cmd_generate
write_metrics = manage_metrics.write_metrics
read_metrics_raw = manage_metrics.read_metrics_raw


# =============================================================================
# require_plan_exists guard seeder (mirrors test_print_phase_breakdown*.py)
# =============================================================================

_UNSEEDED_PLAN_IDS: set[str] = set()


@pytest.fixture(autouse=True)
def _seed_guarded_plan_dirs(plan_context, monkeypatch):
    """Auto-seed the ``status.json`` sentinel at the require_plan_exists chokepoint."""
    _UNSEEDED_PLAN_IDS.clear()
    real_require = manage_metrics.require_plan_exists
    real_get_plan_dir = manage_metrics.get_plan_dir

    def _seeding_require(plan_id):
        if plan_id not in _UNSEEDED_PLAN_IDS:
            plan_dir = real_get_plan_dir(plan_id)
            plan_dir.mkdir(parents=True, exist_ok=True)
            sentinel = plan_dir / 'status.json'
            if not sentinel.is_file():
                sentinel.write_text('{}', encoding='utf-8')
        return real_require(plan_id)

    monkeypatch.setattr(manage_metrics, 'require_plan_exists', _seeding_require)
    return plan_context


def _render_report(plan_context, plan_id: str, phases: dict) -> str:
    """Seed a metrics.toon from ``phases``, run generate, return the metrics.md text."""
    write_metrics(plan_id, {'phases': phases})
    result = cmd_generate(ns_generate(plan_id))
    assert result['status'] == 'success', result
    md_path = plan_context.plan_dir_for(plan_id) / 'metrics.md'
    content: str = md_path.read_text(encoding='utf-8')
    return content


def _boundary_bullet(report: str) -> str:
    return next(
        line for line in report.splitlines()
        if line.startswith('- **Dispatch-boundary total**:')
    )


# =============================================================================
# D5(a) — an impossible ratio (numerator > denominator) is a loud FAILURE
# =============================================================================


class TestImpossibleRatioIsAFailure:
    """`dispatch_boundary_rows_recorded > subagent_samples` is a population failure.

    The two counts come from different producers, so a numerator larger than the
    denominator is not over-coverage — it is proof the ratio is not commensurable.
    Rendering it `complete` (as pre-fix code does) certifies an impossible figure.
    """

    def test_over_coverage_renders_failure_naming_both_populations(self, plan_context):
        report = _render_report(
            plan_context,
            'boundary-over-coverage',
            {
                '5-execute': {
                    'total_tokens': 100000,
                    'dispatch_boundary_total': 900000,
                    'dispatch_boundary_rows_recorded': 8,
                    'subagent_samples': 3,
                },
            },
        )
        bullet = _boundary_bullet(report)

        # A loud failure verdict — never 'complete'.
        assert 'FAILURE' in bullet, bullet
        assert 'complete' not in bullet, bullet
        # Both populations behind the two figures are named in the output.
        assert 'record-dispatch-boundary' in bullet, bullet  # numerator producer
        assert 'subagent_samples' in bullet, bullet  # denominator producer
        # The impossible measure never wins the reconciliation maximum.
        assert 'did not win the maximum' in bullet, bullet

    def test_over_covering_measure_is_ineligible_for_the_maximum(self):
        """A numerator-exceeds-denominator boundary sum cannot win the max.

        It is the largest number on the row; a coverage-blind max would pick the
        inflated (double-counted) figure and over-report the dispatched Total.
        """
        row = {
            'total_tokens': 100000,
            'dispatch_boundary_total': 900000,
            'dispatch_boundary_rows_recorded': 8,
            'subagent_samples': 3,
        }
        assert manage_metrics._reconcile_dispatched_measures(row) == ('total_tokens', 100000)


# =============================================================================
# D5(b) / D3 — the ledger names the classes it excludes (declared population)
# =============================================================================


class TestDeclaredExclusionList:
    """Non-registering dispatch classes are named in an explicit exclusion list."""

    def test_excluded_classes_are_named_in_the_report(self, plan_context):
        report = _render_report(
            plan_context,
            'boundary-declared-exclusions',
            {
                '5-execute': {
                    'total_tokens': 100000,
                    'dispatch_boundary_total': 100000,
                    'dispatch_boundary_rows_recorded': 4,
                    'subagent_samples': 4,
                },
            },
        )

        assert 'excluded by declaration' in report, report
        # Every source-derived non-registering class is named (D1 derivation).
        for excluded in (
            'phase-2-refine',
            'phase-3-outline',
            'q-gate-validation',
            'verification-feedback',
            'research',
            'enrich-module',
        ):
            assert excluded in report, f'{excluded!r} not named in the exclusion list'

    def test_exclusion_constant_is_source_derived_not_a_registering_phase(self):
        """The constant lists non-registering classes and excludes the registering ones.

        Guards the D1 derivation: phase-4-plan / phase-5-execute / phase-6-finalize
        DO register a boundary, so they must never appear in the exclusion list.
        """
        excluded = manage_metrics.DISPATCH_BOUNDARY_EXCLUDED_CLASSES
        assert 'phase-2-refine' in excluded
        assert 'q-gate-validation' in excluded
        for registering in ('phase-4-plan', 'phase-5-execute', 'phase-6-finalize'):
            assert registering not in excluded, f'{registering} registers a boundary'

    def test_negative_control_dispatched_phase_shortfall_is_declared_not_silent(self, plan_context):
        """A phase that dispatched but under-registers is EXPLAINED, not silently shrunk.

        D3 negative control: a phase with more `subagent_samples` than boundary rows
        (a class within it did not register) must render both the PARTIAL coverage
        note AND the declared exclusion list — the shortfall is named, never a bare
        smaller denominator.
        """
        report = _render_report(
            plan_context,
            'boundary-negative-control',
            {
                '4-plan': {
                    'total_tokens': 100000,
                    'dispatch_boundary_total': 90000,
                    'dispatch_boundary_rows_recorded': 1,
                    'subagent_samples': 2,
                },
            },
        )
        bullet = _boundary_bullet(report)

        assert 'PARTIAL: 1 of 2 dispatch(es) recorded' in bullet, bullet
        # The shortfall is declared, not silent.
        assert 'excluded by declaration' in report, report
        assert 'q-gate-validation' in report, report


# =============================================================================
# D5(c) — the comparator annotates the three-way distinction truthfully
# =============================================================================


class TestComparatorThreeWayDistinction:
    """Equal is not smaller: the annotation reflects the true value-vs-total relation."""

    def _annotation_line(self, report: str) -> str:
        return next(
            line for line in report.splitlines()
            if 'Tokens reconciled across the competing measures' in line
        )

    def test_equal_boundary_and_total_annotated_as_agreement(self, plan_context):
        """value == total_tokens → agreement, NOT a strict "> total_tokens" claim.

        Reaches the equal branch via an inline-population row, where total_tokens is
        excluded from the dispatched maximum and a dispatched measure numerically
        equal to it wins — the case pre-fix code mislabels as under-count.
        """
        report = _render_report(
            plan_context,
            'boundary-equal-agreement',
            {
                '4-plan': {
                    'total_tokens': 5000,
                    'total_tokens_population': manage_metrics.POPULATION_INLINE,
                    'subagent_total_tokens': 5000,
                },
            },
        )
        annotation = self._annotation_line(report)

        assert '= total_tokens 5,000' in annotation, annotation
        assert 'measures agree' in annotation, annotation
        # The retired strict-inequality claim is gone for the equal case.
        assert '(> total_tokens 5,000)' not in annotation, annotation

    def test_smaller_dispatched_winner_annotated_as_below_total(self, plan_context):
        """value < total_tokens → "< total_tokens", never "> total_tokens"."""
        report = _render_report(
            plan_context,
            'boundary-smaller',
            {
                '4-plan': {
                    'total_tokens': 5000,
                    'total_tokens_population': manage_metrics.POPULATION_INLINE,
                    'subagent_total_tokens': 3000,
                },
            },
        )
        annotation = self._annotation_line(report)

        assert '< total_tokens 5,000' in annotation, annotation
        assert '(> total_tokens 5,000)' not in annotation, annotation

    def test_larger_dispatched_winner_annotated_as_above_total(self, plan_context):
        """CHARACTERIZATION arm: value > total_tokens → "> total_tokens" (correct today).

        Pins the arm that already renders correctly so the fix cannot regress it
        while correcting the equal / smaller arms.
        """
        report = _render_report(
            plan_context,
            'boundary-larger',
            {
                '4-plan': {
                    'total_tokens': 439628,
                    'subagent_total_tokens': 577452,
                },
            },
        )
        annotation = self._annotation_line(report)

        assert 'subagent_total_tokens 577,452' in annotation, annotation
        assert '(> total_tokens 439,628)' in annotation, annotation
