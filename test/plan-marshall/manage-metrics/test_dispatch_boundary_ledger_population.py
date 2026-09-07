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

# ruff: noqa: I001, E402
import importlib.util
import sys
from pathlib import Path

import pytest

# This module publishes a guard population (see GUARD_POPULATION_SIZE below), and
# the root conftest's ``pytest_report_header`` LOADS it to read that number BEFORE
# collection — i.e. before pytest has prepended this file's own directory to
# ``sys.path``. Without this insert the sibling-fixture import below raises
# ModuleNotFoundError at that point and the header reports UNAVAILABLE for exactly
# the run the number matters on, the passing one. See
# ``pm-plugin-development:plugin-script-architecture`` standards/test-scaffolding.md
# for the canonical prologue this follows.
_FIXTURE_DIR = Path(__file__).parent
if str(_FIXTURE_DIR) not in sys.path:
    sys.path.insert(0, str(_FIXTURE_DIR))

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
# The derived dispatch-class population, run once and published
# =============================================================================

#: Run ONCE at import. The same result feeds the published size below and the
#: equality assertion further down, so the number the session header reports and
#: the number the guard actually swept cannot drift apart.
_DISPATCH_CLASS_SCAN = manage_metrics.scan_dispatch_classes()

# Non-emptiness asserted at IMPORT. Every assertion below is an equality against
# ``population - registering``: over an EMPTY population that difference is empty
# too, so a declaration that had also gone empty would agree with it and the guard
# would pass having derived nothing. This failure direction is the dangerous one —
# the smaller the derived population, the easier the equality is to satisfy.
assert _DISPATCH_CLASS_SCAN['dispatch_classes'], (
    'the call-graph scan derived no dispatch class at all, so every equality '
    f'assertion below would be vacuous: {_DISPATCH_CLASS_SCAN["source"]}'
)

#: Published on EVERY run — passing included — by the root conftest's
#: ``pytest_report_header`` (see ``_ROUTING_GUARD_MODULES`` in
#: ``test/conftest.py``). The import-time assertion above fails an EMPTY
#: population; publishing the size is what makes a SHRUNKEN one visible on the
#: GREEN run, where no failure message is ever rendered.
GUARD_POPULATION_LABEL = 'call-graph dispatch classes'
GUARD_POPULATION_SIZE = len(_DISPATCH_CLASS_SCAN['dispatch_classes'])


def _exclusion_divergence(
    population: tuple[str, ...] | list[str],
    registering: tuple[str, ...] | list[str],
    declared: tuple[str, ...] | list[str],
) -> dict[str, list[str]]:
    """Compare a declared exclusion set against ``population - registering``.

    The pure oracle behind the equality assertion, split out so the two failure
    DIRECTIONS equality makes checkable can each be driven with synthetic input.
    Both are reported separately rather than as one boolean, because they are
    different defects with different repairs: a class the code dispatches and
    nobody declared, versus a declared name no dispatch class answers to.
    """
    expected = set(population) - set(registering)
    return {
        'missing_from_declaration': sorted(expected - set(declared)),
        'absent_from_population': sorted(set(declared) - expected),
    }


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

    def test_exclusion_constant_equals_the_non_registering_half_of_the_population(self):
        """The constant IS ``population - registering``, checked as an equality.

        Two independent producers, neither of them the constant: the FULL dispatch
        class population from ``scan_dispatch_classes`` (the call graph) and the
        REGISTERING subset from ``scan_boundary_registrations`` (the workflow docs
        that issue the verb). The tuple must be exactly their difference.

        This SUPERSEDES the disjointness form, which was strictly weaker in both
        directions and is subsumed here: a class that both registers and is
        declared lands in ``absent_from_population`` below, so the overlap the old
        assertion caught still fails. What disjointness could NOT see is what this
        adds — a new non-registering dispatch class nobody added to the tuple is
        disjoint from the registering set, and a tuple entry that no longer names
        any dispatch class is disjoint from it too. Both left the constant stale
        while the guard stayed green and the report's "excluded by declaration"
        list under-explained the shortfall it exists to explain.

        The failure message names WHICH SIDE diverged, as the disjointness message
        did — the two directions are different defects with different repairs.
        """
        scan = _DISPATCH_CLASS_SCAN
        registrations = manage_metrics.scan_boundary_registrations()

        # Anti-vacuity for BOTH producers, asserted BEFORE the verdict computed
        # over them is read. An empty population makes the difference empty, and an
        # empty registering set makes the difference the whole population — either
        # way the equality stops meaning what it says.
        assert scan['lines_scanned'] > 0, f'read no line of {scan["source"]}'
        assert scan['dispatch_edges_found'] > 0, f'found no dispatch edge in {scan["source"]}'
        assert registrations['documents_scanned'] > 0, 'registration scan walked no documents'
        assert registrations['registering_classes'], 'registration scan derived no registering class'

        population = scan['dispatch_classes']
        registering = registrations['registering_classes']
        # The registering set is derived from a DIFFERENT source than the
        # population, so their agreement is a real cross-check rather than a
        # tautology: a phase that registers a boundary must be a dispatch class the
        # call graph draws. Without this, a registering name the graph does not
        # carry would silently subtract nothing and inflate the expected exclusions.
        assert set(registering) <= set(population), (
            'the dispatching code registers a boundary for phase(s) the call graph '
            f'does not draw as a dispatch class: {sorted(set(registering) - set(population))}. '
            f'Population from {scan["source"]}: {list(population)}'
        )

        divergence = _exclusion_divergence(
            population, registering, manage_metrics.DISPATCH_BOUNDARY_EXCLUDED_CLASSES
        )
        assert divergence == {'missing_from_declaration': [], 'absent_from_population': []}, (
            'DISPATCH_BOUNDARY_EXCLUDED_CLASSES is not the non-registering half of '
            'the derived population. Dispatch classes the call graph names that '
            'register no boundary and the tuple does not declare: '
            f'{divergence["missing_from_declaration"]}. Names the tuple declares '
            'that are not in the derived non-registering set (either no longer a '
            'dispatch class, or the code now registers for them): '
            f'{divergence["absent_from_population"]}. Population ({len(population)}) '
            f'from {scan["source"]}; registering {list(registering)} from '
            f'{[(r["path"], r["line"], r["phase"]) for r in registrations["registering"]]}'
        )

    def test_dispatch_class_scan_reports_every_edge_it_could_not_read(self):
        """The call-graph scan suppresses nothing — ADR-14's reporting obligation.

        A dropped edge shrinks the derived population, and a SMALLER population
        makes the equality above EASIER to satisfy, so this scan's coverage holes
        fail toward green. Every glyph occurrence therefore lands in exactly one
        published bucket, and the one edge shape that legitimately names no class
        carries its own reason so the residue cannot absorb a genuinely unreadable
        edge added later.
        """
        scan = _DISPATCH_CLASS_SCAN

        assert scan['dispatch_edges_found'] == (
            len(scan['resolved_edges']) + len(scan['unparsed'])
        )
        for record in scan['unparsed']:
            # Reported ACTIONABLY: a bucket whose records name no location is a
            # count, not a report.
            assert set(record) >= {'line', 'reason', 'text'}, record

        unreadable = [
            record
            for record in scan['unparsed']
            if record['reason'] != manage_metrics._UNPARSED_NO_ROLE_KEY
        ]
        assert unreadable == [], (
            'the call-graph scan found dispatch edges it could not resolve into a '
            'class, so its derived population is narrower than the real one: '
            f'{unreadable}'
        )

    def test_equality_fails_when_a_non_registering_class_is_absent_from_the_tuple(self):
        # MUTATION ARM 1 — the direction disjointness could not see. A dispatch
        # class the code does NOT register for, and that nobody added to the
        # declaration, is disjoint from the registering set, so the retired
        # assertion stayed green over it. Equality reports it.
        divergence = _exclusion_divergence(
            population=('phase-4-plan', 'phase-5-execute', 'research', 'newly-added-class'),
            registering=('phase-4-plan', 'phase-5-execute'),
            declared=('research',),
        )
        assert divergence['missing_from_declaration'] == ['newly-added-class']
        assert divergence['absent_from_population'] == []

    def test_equality_fails_when_a_tuple_entry_is_absent_from_the_population(self):
        # MUTATION ARM 2 — the other direction disjointness could not see. A name
        # the tuple declares that answers to no dispatch class any longer (the
        # class was renamed or removed) is also disjoint from the registering set.
        divergence = _exclusion_divergence(
            population=('phase-4-plan', 'phase-5-execute', 'research'),
            registering=('phase-4-plan', 'phase-5-execute'),
            declared=('research', 'retired-class'),
        )
        assert divergence['absent_from_population'] == ['retired-class']
        assert divergence['missing_from_declaration'] == []

    def test_equality_still_fails_on_the_overlap_disjointness_used_to_catch(self):
        # The subsumption claim in the equality test's docstring, made checkable
        # rather than asserted: a class the code REGISTERS for that is also
        # declared non-registering — the only defect the retired disjointness
        # assertion could see — still fails here.
        divergence = _exclusion_divergence(
            population=('phase-4-plan', 'phase-5-execute', 'research'),
            registering=('phase-4-plan', 'phase-5-execute'),
            declared=('research', 'phase-5-execute'),
        )
        assert divergence['absent_from_population'] == ['phase-5-execute']

    def test_registration_scan_reports_every_invocation_it_could_not_read(self):
        """The scan suppresses nothing — ADR-14's reporting obligation.

        A scan that silently dropped the invocations it could not parse would
        derive a SMALLER registering set that agrees with the declared constant for
        the wrong reason. Every occurrence must land in exactly one published
        bucket, and the unparsed bucket must be empty for the disjointness verdict
        above to be trustworthy rather than merely narrow.
        """
        scan = manage_metrics.scan_boundary_registrations()

        # The three invocation buckets partition the invocations found — no
        # occurrence is counted twice and none is dropped between them.
        assert scan['invocations_found'] == (
            len(scan['registering']) + len(scan['template']) + len(scan['unparsed'])
        )
        assert not scan['unparsed'], (
            f'the scan found call sites it could not read, so its derived set is '
            f'narrower than the real population: {scan["unparsed"]}'
        )

    def test_shortfall_renders_the_partial_note_alongside_the_exclusion_list(self, plan_context):
        """A phase that dispatched but under-registers is EXPLAINED, not silently shrunk.

        RENAMED to what it actually checks. It was called a "negative control", but
        it removes no registration: of its three assertions only the ``PARTIAL: 1 of
        2`` one depends on the shortfall at all — ``excluded by declaration`` and
        ``q-gate-validation`` are rendered for ANY report carrying a boundary
        surface, so two thirds of it hold whether or not the property under test
        holds. The real control is
        ``test_rendered_exclusion_list_follows_the_declaration`` below.
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

    def test_rendered_exclusion_list_follows_the_declaration(self, plan_context, monkeypatch):
        """The REAL negative control: remove a registration and the render follows.

        The assertions above check that the exclusion list appears. That is
        satisfied by a hardcoded sentence, so it cannot tell a render DRIVEN by the
        declaration from one that merely recites the same names. This removes a
        class from a fixture copy of the declaration and asserts the rendered list
        loses exactly that class and keeps the rest — the discriminating pair the
        positive assertion lacks.
        """
        declared = manage_metrics.DISPATCH_BOUNDARY_EXCLUDED_CLASSES
        dropped = 'q-gate-validation'
        reduced = tuple(name for name in declared if name != dropped)

        # Fixture preconditions — without these the assertions below say nothing.
        assert dropped in declared, f'{dropped} is not declared; pick another class'
        assert reduced, 'reduced declaration is empty — the retained-class check would be vacuous'

        monkeypatch.setattr(manage_metrics, 'DISPATCH_BOUNDARY_EXCLUDED_CLASSES', reduced)
        report = _render_report(
            plan_context,
            'boundary-exclusion-follows-declaration',
            {
                '4-plan': {
                    'total_tokens': 100000,
                    'dispatch_boundary_total': 90000,
                    'dispatch_boundary_rows_recorded': 1,
                    'subagent_samples': 2,
                },
            },
        )

        # The render still declares an exclusion set...
        assert 'excluded by declaration' in report, report
        # ...but the removed class is gone from it, and every retained one remains.
        assert dropped not in report, (
            f'{dropped!r} was removed from the declaration yet still appears in the '
            f'render — the exclusion list is hardcoded prose, not the declaration'
        )
        for retained in reduced:
            assert retained in report, retained


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
