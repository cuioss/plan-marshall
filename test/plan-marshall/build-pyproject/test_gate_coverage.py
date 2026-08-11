#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Unit tests for the pure ``_gate_coverage`` gate-honesty helpers.

Covers the three pure responsibilities that back plan 160's build-gate coverage
parity:

* ``classify_check_duration`` — the freshness backstop (D4). Demonstrated in BOTH
  directions: an implausibly fast success over a substantial file set is flagged,
  and a legitimately-timed run (or a small scope) is not. A check that flagged
  every fast gate would be disabled within a week, so the negative direction is
  as load-bearing as the positive one.
* ``CoverageBoundary`` / ``render_coverage_summary`` — the honest partial-vs-full
  verdict (D5). A degraded run must be distinguishable, in the gate's own words,
  from one that genuinely passed.
* ``parity_population`` — the derived local-gate-vs-CI comparison set (D1),
  asserted NON-EMPTY (D6): a parity table over an empty population looks identical
  to perfect parity.

The module is stdlib-only and lives on the ``script-shared/scripts/build/``
PYTHONPATH entry the root conftest configures, so it is exercised by a plain
import — no build, no subprocess.
"""

from _gate_coverage import (
    MAX_ANALYSIS_THROUGHPUT,
    SUSPECT_MIN_FILES,
    CoverageBoundary,
    classify_check_duration,
    parity_population,
    render_coverage_summary,
)

# ---------------------------------------------------------------------------
# Freshness — classify_check_duration (D4, both directions)
# ---------------------------------------------------------------------------


def test_large_scope_reported_in_near_zero_time_is_flagged():
    """A big file set reporting success in a blink did no analysis — flagged."""
    verdict = classify_check_duration(files_checked=660, elapsed_seconds=0.05)

    assert verdict.plausible is False
    assert verdict.reason is not None
    assert '660 files' in verdict.reason


def test_large_scope_with_real_elapsed_is_not_flagged():
    """A cold whole-tree run that takes real time is legitimate — NOT flagged.

    This is the negative direction the plan requires: a check that flags a
    genuinely-slow run is a false alarm, and a gate that cries wolf gets disabled.
    """
    verdict = classify_check_duration(files_checked=660, elapsed_seconds=15.0)

    assert verdict.plausible is True
    assert verdict.reason is None


def test_small_scope_fast_is_not_flagged():
    """A tiny file set is legitimately fast — the duration verdict does not apply.

    This is what keeps a scoped ``compile {bundle}`` of a thin module, or a warm
    single-file check, from tripping the backstop: 'distinguish plausible-fast
    from impossible-fast', not 'flag every fast gate'.
    """
    verdict = classify_check_duration(files_checked=SUSPECT_MIN_FILES - 1, elapsed_seconds=0.01)

    assert verdict.plausible is True
    assert verdict.reason is None


def test_zero_elapsed_over_large_scope_is_flagged_not_divided():
    """Zero/negative elapsed over a substantial scope is infinite throughput — flagged, no crash."""
    verdict = classify_check_duration(files_checked=500, elapsed_seconds=0.0)

    assert verdict.plausible is False
    assert verdict.reason is not None
    assert 'no measurable work' in verdict.reason


def test_throughput_boundary_is_the_discriminator():
    """The verdict keys on throughput vs the ceiling, not on raw speed.

    A run just under the throughput ceiling is plausible; one well over it is not.
    Pins that the discriminator is files-per-second, so scope is accounted for
    rather than a bare wall-time threshold being applied.
    """
    files = 1000
    just_under = files / (MAX_ANALYSIS_THROUGHPUT * 0.5)  # half the ceiling throughput
    well_over = files / (MAX_ANALYSIS_THROUGHPUT * 4.0)  # quadruple the ceiling throughput

    assert classify_check_duration(files, just_under).plausible is True
    assert classify_check_duration(files, well_over).plausible is False


# ---------------------------------------------------------------------------
# Coverage boundary — CoverageBoundary / render_coverage_summary (D5)
# ---------------------------------------------------------------------------


def test_complete_boundary_renders_a_complete_verdict():
    """With nothing degraded, the summary is COMPLETE and names what was checked."""
    boundary = CoverageBoundary()
    boundary.record_checked('mypy(production)')
    boundary.record_checked('ruff')

    assert boundary.complete is True
    summary = render_coverage_summary(boundary)
    assert 'COMPLETE' in summary
    assert 'mypy(production)' in summary
    assert 'ruff' in summary


def test_degraded_boundary_renders_a_partial_verdict_that_names_the_gap():
    """A degraded dimension makes the verdict PARTIAL, names the gap, and disclaims certification.

    The cold-read property: a reader asked 'is it safe to push?' against this text
    must read NO — the gate did not check X — never a clean pass.
    """
    boundary = CoverageBoundary()
    boundary.record_checked('mypy(production)')
    boundary.record_degraded('mypy(test)', 'freshness suspect: reported success implausibly fast')

    assert boundary.complete is False
    summary = render_coverage_summary(boundary)
    assert 'PARTIAL' in summary
    assert 'mypy(test)' in summary
    assert 'freshness suspect' in summary
    assert 'NOT a full pass' in summary


def test_partial_verdict_is_textually_distinct_from_complete_verdict():
    """A partially-checked footprint produces a DISTINGUISHABLE verdict, not a clean one.

    The two verdicts must not be confusable — that confusability is the defect.
    """
    complete = CoverageBoundary()
    complete.record_checked('mypy(production)')

    partial = CoverageBoundary()
    partial.record_checked('mypy(production)')
    partial.record_degraded('.claude', 'omitted — no collectable files')

    assert render_coverage_summary(complete) != render_coverage_summary(partial)
    assert 'COMPLETE' in render_coverage_summary(complete)
    assert 'PARTIAL' in render_coverage_summary(partial)


# ---------------------------------------------------------------------------
# Parity population — parity_population (D1 / D6)
# ---------------------------------------------------------------------------


def test_parity_population_is_non_empty():
    """The derived parity table's population must be NON-EMPTY (D6).

    A parity table computed over an empty population is indistinguishable from
    perfect parity — the confident-but-empty signal this whole effort prevents.
    """
    population = parity_population()

    assert len(population) > 0


def test_parity_population_spans_both_axes():
    """The population covers scope AND freshness — the two dimensions the goal names."""
    dimensions = {cell.dimension for cell in parity_population()}

    assert 'freshness' in dimensions
    assert 'coverage-boundary' in dimensions
    # At least one scope dimension is present too.
    assert dimensions & {'mypy-production', 'ruff-rules', 'mypy-test', 'pytest-scope'}


def test_parity_cells_carry_a_verdict_and_evidence():
    """Every cell states a verdict and a non-empty note — a table row without evidence is a lead, not a finding."""
    for cell in parity_population():
        assert cell.verdict in {'equal', 'subset', 'closed'}
        assert cell.note
