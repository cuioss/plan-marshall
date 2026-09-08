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

# ruff: noqa: E402
import sys
from collections import Counter
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

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

from _manage_metrics_fixtures import ns_generate

from conftest import load_script_module

# kebab-case filename — resolved by (bundle, skill, file) under a unique module
# name, unregistered so this copy cannot displace one another suite holds.
manage_metrics = load_script_module(
    'plan-marshall', 'manage-metrics', 'manage-metrics.py', 'manage_metrics_boundary_pop', register=False
)

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


def _partition_divergence(
    truth_identities: Iterable[Any],
    buckets: dict[str, tuple | list],
    identity: Callable[[Any], Any] = lambda record: record,
) -> dict[str, object]:
    """Compare a scan's buckets against an INDEPENDENTLY recounted identity MULTISET.

    The pure oracle behind both partition assertions below. It takes the truth
    identities as a parameter precisely so they can come from somewhere other than
    the scan being checked: a partition claim compared against the producer's own
    ``len(a) + len(b)`` expression is that expression compared with itself and holds
    for every possible scan result, including one that dropped records.

    The comparison is over OCCURRENCE IDENTITIES, not over totals, because a count
    equality is an ASSERTED commensurability rather than a DERIVED one. A scan that
    drops occurrence A while assigning occurrence B to two buckets cancels exactly:
    the bucket cardinality still equals the recounted cardinality, so an aggregate
    oracle passes a scan that both LOST a record and DOUBLE-COUNTED another. Two
    verdicts are therefore reported, and they are different defects with different
    repairs:

    * ``missing`` — identities the documents carry that the buckets do not claim
      (the scan dropped them, narrowing its derived population — the direction that
      fails toward green).
    * ``duplicated`` — identities the buckets claim MORE OFTEN than the documents
      carry them: two buckets claiming one occurrence, one bucket claiming it
      twice, or a claim on an occurrence the documents do not carry at all.

    ``unaccounted`` — the signed aggregate delta this supersedes — is RETAINED so
    the older, weaker signal stays visible in the failure message, and so the
    cancelling case is legible as ``unaccounted == 0`` sitting beside a non-empty
    ``missing``/``duplicated``.

    Args:
        truth_identities: Occurrence identities recounted from the documents.
        buckets: The scan's published buckets, name → records.
        identity: Maps one bucket record to its canonical occurrence identity.
            Defaults to the record itself, for synthetic identity-valued buckets.
    """
    sizes = {name: len(records) for name, records in buckets.items()}
    truth_counts = Counter(truth_identities)
    bucket_counts = Counter(
        identity(record) for records in buckets.values() for record in records
    )
    independent_total = sum(truth_counts.values())
    return {
        'independent_total': independent_total,
        'bucketed_total': sum(sizes.values()),
        'unaccounted': independent_total - sum(sizes.values()),
        'missing': sorted((truth_counts - bucket_counts).elements()),
        'duplicated': sorted((bucket_counts - truth_counts).elements()),
        'sizes': sizes,
    }


def _bucket_identities(buckets: dict[str, tuple | list]) -> list[Any]:
    """Flatten identity-valued buckets into the occurrences they collectively claim."""
    return [identity for records in buckets.values() for identity in records]


def _without_last_occurrence(buckets: dict[str, tuple | list]) -> tuple[dict[str, tuple], Any]:
    """Return bucket copies that DROPPED the last claimed occurrence, and which one."""
    dropped = _bucket_identities(buckets)[-1]
    mutated = {name: list(records) for name, records in buckets.items()}
    owner = next(name for name in mutated if dropped in mutated[name])
    mutated[owner].remove(dropped)
    return {name: tuple(records) for name, records in mutated.items()}, dropped


def _with_a_second_claim(buckets: dict[str, tuple | list]) -> tuple[dict[str, tuple], Any]:
    """Return bucket copies where a SECOND bucket also claims the first occurrence."""
    claimed = _bucket_identities(buckets)[0]
    mutated = {name: list(records) for name, records in buckets.items()}
    owner = next(name for name in mutated if claimed in mutated[name])
    other = next(name for name in mutated if name != owner)
    mutated[other].append(claimed)
    return {name: tuple(records) for name, records in mutated.items()}, claimed


def _independent_glyph_line_identities(source: str) -> list[int]:
    """Recount the call graph's dispatch-edge glyph occurrences as IDENTITIES.

    Re-reads the document ``scan_dispatch_classes`` read and applies the same
    ``_DISPATCH_EDGE`` filter its loop enters on, so the population is derived from
    the document rather than from the scan's return value. Every matching line puts
    exactly one record into exactly one of the three published buckets, and each of
    those records carries its 1-based ``line`` (manage-metrics.py:903) — so the line
    number IS the canonical occurrence identity, and this is the identity multiset
    those buckets must partition.
    """
    lines = Path(source).read_text(encoding='utf-8').splitlines()
    return [
        index + 1
        for index, line in enumerate(lines)
        if manage_metrics._DISPATCH_EDGE.search(line)
    ]


def _independent_verb_line_identities(scan_root: str) -> list[tuple[str, int]]:
    """Recount boundary-verb occurrences from the DOCUMENTS themselves, as IDENTITIES.

    The registration-scan counterpart of
    :func:`_independent_glyph_line_identities`: walks the same tree
    ``scan_boundary_registrations`` walks, independently of that scan's return
    value. Every record that scan files carries ``path`` + ``line``
    (manage-metrics.py:683), so the identity is that pair — and the recount must
    mirror the scan's exact normalization or every identity mismatches:

    * a READABLE document is keyed by ``str(document.relative_to(root))``, exactly
      as the scan keys it;
    * an UNREADABLE one is keyed by the ABSOLUTE ``str(document)`` with line 0,
      which is the single synthetic coverage-gap record the scan files for it
      (manage-metrics.py:674-676). Minting the SAME identity preserves the existing
      contract that a document neither side can read stays a reported hole rather
      than becoming a spurious partition failure.
    """
    root = Path(scan_root)
    identities: list[tuple[str, int]] = []
    for document in sorted(root.rglob('*.md')):
        try:
            text = document.read_text(encoding='utf-8')
        except OSError:
            identities.append((str(document), 0))
            continue
        identities.extend(
            (str(document.relative_to(root)), index + 1)
            for index, line in enumerate(text.splitlines())
            if manage_metrics._BOUNDARY_VERB in line
        )
    return identities


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

        The partition is checked against the line IDENTITIES recounted from the
        call-graph document, not against the scan's own ``len(resolved) +
        len(unparsed)`` expression (the producer's arithmetic compared with itself,
        which held for every scan result, dropped edges included) and not against a
        recounted TOTAL either: a total cancels a dropped edge against a
        double-assigned one and passes both.
        """
        scan = _DISPATCH_CLASS_SCAN

        # Anti-vacuity for the recount itself, BEFORE the partition computed over
        # it is read: a recount that returned nothing would make the comparison
        # below nothing against nothing — the same failure class one layer up.
        glyph_identities = _independent_glyph_line_identities(scan['source'])
        assert glyph_identities, (
            f'the recount found no dispatch-edge glyph in {scan["source"]}, so the '
            'partition below would compare nothing against nothing'
        )

        divergence = _partition_divergence(
            glyph_identities,
            {
                'resolved_edges': scan['resolved_edges'],
                'unparsed': scan['unparsed'],
                'glyph_mentions': scan['glyph_mentions'],
            },
            identity=lambda record: record['line'],
        )
        assert (divergence['missing'], divergence['duplicated']) == ([], []), (
            'the three published buckets do not partition the dispatch-edge glyph '
            f'lines the document actually carries: {divergence}. "missing" names '
            'lines the document carries that no bucket claims (the scan dropped '
            'them, narrowing its derived population — the direction that fails '
            'toward green); "duplicated" names lines claimed more than once (two '
            'buckets claiming one edge, or one bucket claiming it twice). The '
            'aggregate "unaccounted" is reported alongside but is NOT the verdict: '
            f'it reads 0 whenever those two directions cancel. Source: {scan["source"]}'
        )
        # The published edge count is that partition minus the non-edge bucket,
        # checked against the recounted total so a wrong expression is visible.
        assert scan['dispatch_edges_found'] == len(glyph_identities) - len(scan['glyph_mentions']), (
            f'dispatch_edges_found ({scan["dispatch_edges_found"]}) is not the '
            f'{len(glyph_identities)} recounted glyph lines minus the '
            f'{len(scan["glyph_mentions"])} that name no target'
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

        The partition is checked against the ``(path, line)`` IDENTITIES recounted
        from the scanned documents, not against the scan's own ``len(registering) +
        len(template) + len(unparsed)`` expression (the producer's arithmetic
        compared with itself, which held for every scan result, dropped invocations
        included) and not against a recounted TOTAL either: a total cancels a
        dropped invocation against a double-assigned one and passes both.
        """
        scan = manage_metrics.scan_boundary_registrations()

        # Anti-vacuity for the recount itself, BEFORE the partition computed over
        # it is read — an empty recount would compare nothing against nothing.
        verb_identities = _independent_verb_line_identities(scan['scan_root'])
        assert verb_identities, (
            f'the recount found no boundary-verb occurrence under {scan["scan_root"]}, '
            'so the partition below would compare nothing against nothing'
        )

        # The FOUR published buckets partition every verb occurrence the documents
        # carry — prose_mentions included, since a call site that stopped being
        # recognised as a dispatch moves into it rather than vanishing.
        divergence = _partition_divergence(
            verb_identities,
            {
                'registering': scan['registering'],
                'template': scan['template'],
                'unparsed': scan['unparsed'],
                'prose_mentions': scan['prose_mentions'],
            },
            identity=lambda record: (record['path'], record['line']),
        )
        assert (divergence['missing'], divergence['duplicated']) == ([], []), (
            'the four published buckets do not partition the boundary-verb lines '
            f'the documents actually carry: {divergence}. "missing" names '
            'occurrences the documents carry that no bucket claims (the scan dropped '
            'them, giving a narrower registering set that agrees with the declared '
            'constant for the wrong reason); "duplicated" names occurrences claimed '
            'more than once (two buckets claiming one line, or one bucket claiming '
            'it twice). The aggregate "unaccounted" is reported alongside but is NOT '
            'the verdict: it reads 0 whenever those two directions cancel. Root: '
            f'{scan["scan_root"]}'
        )
        # The published invocation count is that partition minus the non-invocation
        # bucket, checked against the recounted total rather than against itself.
        assert scan['invocations_found'] == len(verb_identities) - len(scan['prose_mentions']), (
            f'invocations_found ({scan["invocations_found"]}) is not the '
            f'{len(verb_identities)} recounted verb lines minus the '
            f'{len(scan["prose_mentions"])} that dispatch nothing'
        )
        assert not scan['unparsed'], (
            f'the scan found call sites it could not read, so its derived set is '
            f'narrower than the real population: {scan["unparsed"]}'
        )

    @pytest.mark.parametrize(
        'buckets',
        [
            pytest.param(
                {'resolved_edges': (1, 2, 3), 'unparsed': (4,), 'glyph_mentions': (5, 6)},
                id='dispatch-class-scan-buckets',
            ),
            pytest.param(
                {'registering': (1, 2), 'template': (3,), 'unparsed': (), 'prose_mentions': (4, 5)},
                id='registration-scan-buckets',
            ),
        ],
    )
    def test_partition_reports_a_record_the_buckets_do_not_account_for(self, buckets):
        """MUTATION ARM for both partition assertions, in each site's bucket shape.

        Drives the shared oracle with synthetic scans that mis-partition their
        occurrences, and pairs each failing arm with the passing one that makes it
        discriminating.

        The COMBINED arm is the one that matters, and it is why the oracle compares
        identities rather than totals. A scan that drops occurrence A while
        assigning occurrence B to two buckets keeps its bucket cardinality equal to
        the recounted cardinality, so the aggregate ``unaccounted`` reads 0 — the
        control asserted below — and a count-only oracle certifies a scan that both
        LOST a record and DOUBLE-COUNTED another. A drop-only arm proves nothing
        new here: the aggregate already catches that direction.
        """
        truth = _bucket_identities(buckets)

        # Positive control — buckets that DO account for every occurrence, once.
        clean = _partition_divergence(truth, buckets)
        assert (clean['missing'], clean['duplicated'], clean['unaccounted']) == ([], [], 0)

        # A record the scan dropped: the document carries one the buckets lost.
        absent = max(truth) + 1
        dropped_only = _partition_divergence([*truth, absent], buckets)
        assert dropped_only['unaccounted'] == 1
        assert (dropped_only['missing'], dropped_only['duplicated']) == ([absent], [])

        # The other direction — one occurrence claimed by two buckets.
        doubled_buckets, double_claimed = _with_a_second_claim(buckets)
        doubled = _partition_divergence(truth, doubled_buckets)
        assert doubled['unaccounted'] == -1
        assert (doubled['missing'], doubled['duplicated']) == ([], [double_claimed])

        # COMBINED — one occurrence dropped AND another double-assigned, so the
        # bucket cardinality still equals the truth cardinality and the two errors
        # cancel in every aggregate.
        short_buckets, dropped = _without_last_occurrence(buckets)
        combined_buckets, redoubled = _with_a_second_claim(short_buckets)
        combined = _partition_divergence(truth, combined_buckets)

        # DISCRIMINATING CONTROL — the pre-fix aggregate oracle PASSES this input,
        # which is what makes the identity assertion below strictly stronger rather
        # than a restatement of the count check.
        assert combined['unaccounted'] == 0
        assert combined['bucketed_total'] == combined['independent_total']
        # The identity multiset rejects it, naming exactly the two identities and
        # keeping the two defects separate — they have different repairs.
        assert combined['missing'] == [dropped]
        assert combined['duplicated'] == [redoubled]

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
