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
* ``CoverageBoundary`` / ``render_coverage_summary`` — the honest coverage verdict
  (D5), in THREE forms. A degraded run must be distinguishable, in the gate's own
  words, from one that genuinely passed; and a run that recorded nothing must be
  distinguishable from both, since "nothing was degraded" is vacuously true of a
  run that checked nothing.
* ``coverage_gaps`` — the dimensions a run did NOT cover, split by WHY. An absence
  named with one reason misdescribes the other two: a scope-limited absence, an
  absence this command can never fill, and a check that was reached over an empty
  scope each imply a different remedy.
* ``parity_population`` — the RECORDED local-gate-vs-CI comparison set (D1),
  asserted NON-EMPTY (D6): a parity table over an empty population looks identical
  to perfect parity. Non-emptiness is all this module asserts about it, and over a
  recorded literal that is a weak guarantee — the cells can all be stale and still
  pass. One cell (``spdx-paths``) is separately bound to the substrate it describes
  in ``test_gate_coverage_parity_substrate.py``.

The module is stdlib-only and lives on the ``script-shared/scripts/build/``
PYTHONPATH entry the root conftest configures, so it is exercised by a plain
import — no build, no subprocess.
"""

from _gate_coverage import (
    MAX_ANALYSIS_THROUGHPUT,
    SUSPECT_MIN_FILES,
    CoverageBoundary,
    analysis_limit,
    classify_check_duration,
    coverage_gaps,
    dimension_stem,
    parity_population,
    render_coverage_summary,
    structural_limits,
)

#: Every analysis kind the limit registry characterises. Several tests need to
#: declare a scope that covers all of them (so no clause fires) or all-but-one (so
#: exactly one does); spelling the set out per test would let the two drift.
ALL_DIMENSIONS = frozenset(
    {'mypy(production)', 'mypy(test)', 'ruff', 'SPDX headers', 'plugin-doctor', 'module-tests'}
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


def test_the_incident_band_throughput_is_flagged():
    """The stale-cache incident this backstop exists to catch is NOT rated plausible.

    The observed incident reported success over 660 files in 2-5 s — 132-330
    files/s. A ceiling set above that band rates the incident itself plausible,
    which is the same absence-read-as-success the backstop exists to refuse; the
    3.0 s point (220 files/s) is the case the ceiling must therefore sit below.
    """
    verdict = classify_check_duration(files_checked=660, elapsed_seconds=3.0)

    assert verdict.plausible is False
    assert verdict.reason is not None


def test_the_ceiling_leaves_headroom_over_this_tree_s_cold_throughput():
    """A cold whole-tree run on this tree stays plausible — the negative control for the ceiling.

    Lowering the ceiling to catch the incident band is only safe while a genuine
    cold run still passes. Measured on this tree: 417 files in 5.84 s = 71 files/s.
    A ceiling that flagged that would fire on every honest run and be disabled.
    """
    verdict = classify_check_duration(files_checked=417, elapsed_seconds=5.84)

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


def test_an_empty_boundary_certifies_nothing_and_says_so():
    """A boundary that recorded nothing is UNKNOWN — never COMPLETE (ADR-009 explicit-unknown).

    ``complete`` used to mean only *"nothing was degraded"*, which an empty
    boundary satisfies vacuously: a run that checked nothing rendered the same
    COMPLETE verdict as a run that checked everything, distinguished only by an
    easily-overlooked ``(nothing)`` in the checked list. That is
    absence-of-change laundered into success — the exact shape this module
    exists to refuse — so COMPLETE now requires an affirmative signal and the
    empty boundary gets its own third verdict.
    """
    boundary = CoverageBoundary()

    assert boundary.complete is False
    summary = render_coverage_summary(boundary)
    assert 'COMPLETE' not in summary
    assert '(nothing)' not in summary
    assert 'UNKNOWN' in summary


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


# ---------------------------------------------------------------------------
# Structural scope limits — what a green does NOT evaluate (plan 130 D0)
# ---------------------------------------------------------------------------


def test_dimension_stem_strips_the_recorded_scope_suffix():
    """The analysis-kind key is the dimension text before its bracketed scope.

    ``build.py`` records dimensions with a scope suffix
    (``mypy(production) [660 files, cache disabled]``). The limit registry is keyed
    by ANALYSIS KIND, so the suffix — which varies per run — must not be part of the
    lookup key, or every real run would miss the registry.
    """
    assert dimension_stem('mypy(production) [660 files, cache disabled]') == 'mypy(production)'
    assert dimension_stem('ruff [marketplace/bundles, test, .claude]') == 'ruff'
    assert dimension_stem('plugin-doctor [marketplace-wide]') == 'plugin-doctor'
    assert dimension_stem('module-tests') == 'module-tests'


def test_every_dimension_build_py_records_has_a_registered_limit():
    """Each analysis kind the gate actually runs states what it cannot evaluate.

    The population is the dimension stems ``build.py`` records — an unregistered one
    would render as an UNKNOWN-coverage disclaimer, which is honest but means the
    gate cannot state its own scope limit for a check it really ran.
    """
    recorded_by_build_py = (
        'mypy(production)',
        'mypy(test)',
        'ruff',
        'SPDX headers',
        'plugin-doctor',
        'module-tests',
    )

    for stem in recorded_by_build_py:
        limit = analysis_limit(stem)
        assert limit is not None, f'{stem} has no registered structural scope limit'
        assert limit.analysis
        assert limit.cannot_evaluate


def test_structural_limits_are_derived_from_the_dimensions_actually_checked():
    """A gate that ran fewer analyses states fewer limits — derived, not boilerplate.

    This is the D0 property: the scope limit comes from what the gate ACTUALLY
    analysed, so two runs that checked different dimensions do not print the same
    limit block.
    """
    narrow = structural_limits(['ruff [marketplace/bundles]'])
    wide = structural_limits(
        ['ruff [marketplace/bundles]', 'module-tests [whole-tree pytest]']
    )

    assert [stem for stem, _ in narrow] == ['ruff']
    assert [stem for stem, _ in wide] == ['ruff', 'module-tests']
    assert narrow != wide


def test_unregistered_dimension_is_reported_unknown_not_omitted():
    """An analysis with no registered limit fails CLOSED to UNKNOWN, never to silence.

    Silently omitting it would let the limit block read as exhaustive over a run that
    included an analysis nobody characterised — the same absence-read-as-coverage
    defect the whole gate-honesty effort exists to close.
    """
    boundary = CoverageBoundary()
    boundary.record_checked('ruff [marketplace/bundles]')
    boundary.record_checked('novel-analysis [whole-tree]')

    summary = render_coverage_summary(boundary)

    assert 'novel-analysis' in summary
    assert 'UNKNOWN' in summary


def test_complete_verdict_states_what_its_green_does_not_cover():
    """A COMPLETE verdict carries its own structural scope limit.

    The defect this closes is not that a gate is narrow — it is that a narrow gate's
    green reads as whole-tree assurance. A cold reader of the COMPLETE form must be
    able to answer "what could still be wrong despite this passing?".
    """
    boundary = CoverageBoundary()
    boundary.record_checked('mypy(production) [660 files, cache disabled]')
    boundary.record_checked('module-tests [whole-tree pytest]')

    summary = render_coverage_summary(boundary)

    assert 'COMPLETE' in summary
    # The green is explicitly disclaimed as non-exhaustive over defect classes.
    assert 'does NOT evaluate' in summary
    # And the disclaimer is per-analysis, naming each one that ran.
    assert 'mypy(production)' in summary
    assert 'module-tests' in summary
    # The limits are structural, not scope-widening advice.
    assert 'widening the scope does not reach' in summary


def test_partial_verdict_also_states_the_structural_limit():
    """PARTIAL names BOTH the un-run dimension and the limits of the ones that ran.

    A PARTIAL verdict already says "X was not checked". Without the structural block
    it still implies the dimensions that DID run cover their subject completely.
    """
    boundary = CoverageBoundary()
    boundary.record_checked('ruff [marketplace/bundles]')
    boundary.record_degraded('mypy(test)', 'freshness suspect')

    summary = render_coverage_summary(boundary)

    assert 'PARTIAL' in summary
    assert 'freshness suspect' in summary
    assert 'does NOT evaluate' in summary
    assert 'ruff' in summary


def test_limits_name_the_defect_classes_review_catches_and_gates_cannot():
    """The registered limits describe behaviour under un-supplied inputs, not scope.

    Each limit must state a defect class the analysis structurally cannot reach —
    the classes an external reviewer routinely finds while every in-house gate is
    green. A limit phrased as "only checks the files it was given" would be a SCOPE
    statement, which the PARTIAL verdict already covers and which widening the scope
    WOULD reach.
    """
    typing = analysis_limit('mypy(production)')
    tests = analysis_limit('module-tests')
    lint = analysis_limit('plugin-doctor')

    assert typing is not None and tests is not None and lint is not None
    # Type analysis cannot judge whether a well-typed value is the RIGHT one.
    assert 'correct' in typing.cannot_evaluate.lower()
    # Test execution says nothing about inputs no test supplies.
    assert 'no test' in tests.cannot_evaluate.lower()
    # Structural lint checks shape, never the TRUTH of a documented claim.
    assert 'true' in lint.cannot_evaluate.lower()


def test_an_analysis_the_gate_never_ran_is_named_not_omitted():
    """A dimension absent from the run leaves no trace — so the verdict names it.

    `quality-gate` runs no pytest and no test-tree mypy. Those dimensions appear
    nowhere in its verdict: not as checked, not as degraded, not at all. A reader
    then cannot tell "this gate does not execute tests" from "tests were fine",
    which is the absence-read-as-coverage shape one level up from the one the
    per-analysis limits close.
    """
    boundary = CoverageBoundary()
    boundary.record_checked('mypy(production) [401 files, cache disabled]')
    boundary.record_checked('ruff [marketplace/bundles]')
    quality_gate = frozenset({'mypy(production)', 'ruff', 'SPDX headers', 'plugin-doctor'})

    summary = render_coverage_summary(boundary, quality_gate, quality_gate)

    assert 'not performed by this gate at all' in summary
    assert 'module-tests' in summary
    assert 'mypy(test)' in summary


def test_the_three_uncovered_clauses_are_distinct_and_imply_different_remedies():
    """An absent dimension is named WITH ITS REASON, because the reasons differ in remedy.

    A single "not run in this gate at all" list read a per-INVOCATION absence as a
    statement about the COMMAND: a module-scoped quality-gate printed that the gate
    never performs `plugin-doctor`, which is false — it performs it whole-tree.
    Three separable clauses replace it, and a cold reader must be able to say which
    remedy each implies: widen the scope, use a different command, or do nothing.
    """
    boundary = CoverageBoundary()
    boundary.record_checked('ruff [marketplace/bundles/thin]')
    boundary.record_checked('SPDX headers [marketplace/bundles/thin]')
    boundary.record_empty_scope(
        'mypy(production)', 'marketplace/bundles/thin — nothing survives the excludes'
    )

    summary = render_coverage_summary(
        boundary,
        frozenset({'mypy(production)', 'ruff', 'SPDX headers'}),
        frozenset({'mypy(production)', 'ruff', 'SPDX headers', 'plugin-doctor'}),
    )

    # (a) The gate performs it, but not at this invocation's scope — widen the scope.
    assert 'not performed at this scope: plugin-doctor' in summary
    assert 'a run at a wider scope reaches them' in summary
    # (b) No invocation of this gate performs it — only another command or CI can.
    never = summary.split('not performed by this gate at all')[1]
    assert 'module-tests' in never
    assert 'mypy(test)' in never
    assert 'widening the scope does not reach them either' in never
    # (c) Reached, but its scope held nothing — nothing to do, nothing withheld.
    assert 'attempted, nothing in scope — mypy(production)' in summary
    assert 'nothing here to re-run' in summary


def test_a_scoped_run_never_claims_the_gate_cannot_do_what_it_does_elsewhere():
    """The false clause, pinned directly: neither an out-of-scope nor an empty-scope
    dimension may appear under "not performed by this gate at all".

    This is the exact wrong output the change replaces — a module-scoped
    quality-gate over a bundle whose mypy scope is empty telling its reader that
    the gate never performs `plugin-doctor` or `mypy(production)`.
    """
    boundary = CoverageBoundary()
    boundary.record_checked('ruff [marketplace/bundles/thin]')
    boundary.record_empty_scope('mypy(production)', 'marketplace/bundles/thin — nothing survives')

    summary = render_coverage_summary(
        boundary,
        frozenset({'mypy(production)', 'ruff', 'SPDX headers'}),
        frozenset({'mypy(production)', 'ruff', 'SPDX headers', 'plugin-doctor'}),
    )

    never = summary.split('not performed by this gate at all')[1]
    assert 'plugin-doctor' not in never
    assert 'mypy(production)' not in never


def test_a_run_covering_every_registered_analysis_names_no_uncovered_ones():
    """The uncovered clauses are derived, so a full run states nothing false.

    Without this direction the section could hard-code a list and claim tests were
    skipped on a `verify` run that did execute them.
    """
    boundary = CoverageBoundary()
    for stem in sorted(ALL_DIMENSIONS):
        boundary.record_checked(stem)

    summary = render_coverage_summary(boundary, ALL_DIMENSIONS, ALL_DIMENSIONS)

    assert 'not performed at this scope' not in summary
    assert 'not performed by this gate at all' not in summary
    assert 'attempted, nothing in scope' not in summary


def test_a_degraded_dimension_is_not_also_reported_as_uncovered():
    """Degraded means "attempted, not fully checked" — PARTIAL already reports it.

    Listing it as uncovered too would report the same gap twice under two different
    names, and would wrongly imply the gate does not perform that analysis at all.
    """
    boundary = CoverageBoundary()
    boundary.record_checked('ruff [marketplace/bundles]')
    boundary.record_degraded('mypy(production)', 'freshness suspect')

    gaps = coverage_gaps(boundary, ALL_DIMENSIONS, ALL_DIMENSIONS)

    assert 'mypy(production)' not in gaps.not_at_this_scope
    assert 'mypy(production)' not in gaps.not_by_this_gate


def test_an_undeclared_scope_renders_an_explicit_unknown_not_a_clean_list():
    """A caller that did not state its scope gets UNKNOWN, never a confident empty list.

    Both derived clauses need the caller's two scope declarations. Without them the
    honest output is "this verdict cannot say"; silence would read as "nothing was
    left out", which is the confident-but-unsubstantiated signal being closed.
    """
    boundary = CoverageBoundary()
    boundary.record_checked('ruff [marketplace/bundles]')

    summary = render_coverage_summary(boundary)

    assert 'uncovered dimensions: UNKNOWN' in summary
    assert 'not performed at this scope' not in summary
    assert 'not performed by this gate at all' not in summary


def test_coverage_gaps_distinguishes_undeclared_scope_from_no_gaps():
    """`scope_declared` is what separates "nothing was left out" from "nobody said".

    Two empty gap sets are indistinguishable without it, and the undeclared case is
    precisely the one that must not be read as full coverage.
    """
    boundary = CoverageBoundary()
    boundary.record_checked('ruff')

    undeclared = coverage_gaps(boundary)
    declared = coverage_gaps(boundary, frozenset({'ruff'}), frozenset({'ruff', 'plugin-doctor'}))

    assert undeclared.scope_declared is False
    assert undeclared.not_at_this_scope == ()
    assert undeclared.not_by_this_gate == ()

    assert declared.scope_declared is True
    assert declared.not_at_this_scope == ('plugin-doctor',)
    assert 'module-tests' in declared.not_by_this_gate


def test_an_empty_scope_record_is_not_an_affirmative_coverage_signal():
    """Reaching a check whose scope held nothing does not make the run COMPLETE.

    An empty-scope record certifies that there was nothing to check — never that
    something checked out — so on its own it leaves the boundary UNKNOWN while
    still naming the attempt, which is what distinguishes it from silence.
    """
    boundary = CoverageBoundary()
    boundary.record_empty_scope('mypy(production)', 'thin-bundle — nothing survives the excludes')

    assert boundary.complete is False
    summary = render_coverage_summary(
        boundary, frozenset({'mypy(production)'}), frozenset({'mypy(production)'})
    )

    assert 'UNKNOWN' in summary
    assert 'COMPLETE' not in summary
    assert 'attempted, nothing in scope — mypy(production)' in summary


def test_empty_boundary_does_not_claim_a_limit_block_it_cannot_populate():
    """A run that checked nothing states no per-analysis limits — and is UNKNOWN, not COMPLETE.

    Rendering a limit block over an empty checked set would attach a scope-limit
    statement to a run that performed no analysis, which reads as though something
    was analysed. The verdict word carries the same weight: the previous form said
    COMPLETE and relegated the emptiness to a parenthesised ``(nothing)`` in the
    checked list, which is the same overstatement in smaller type.
    """
    summary = render_coverage_summary(CoverageBoundary())

    assert 'UNKNOWN' in summary
    assert 'COMPLETE' not in summary
    assert 'does NOT evaluate' not in summary
