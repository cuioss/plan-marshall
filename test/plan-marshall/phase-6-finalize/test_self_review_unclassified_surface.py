#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""The self-review surfacing contract keeps BOTH routes to a silent green apart.

A ``pre-submission-self-review`` step can report a clean ``done`` having
established nothing about the diff, and it can get there by two structurally
different routes. Both end in the same outcome, so only the CONTRACT can keep
them apart:

* **Route 1 — no implementor resolves.** A consumer project ships no domain
  surfacer, the zero-generator fallback fires, and no file is searched at all.
  The record must carry the *not-run* verdict — a statement about the executor
  that makes no claim about the diff.
* **Route 2 — a wrong-domain implementor resolves, runs, and observes
  nothing.** A surfacer DID run over a real, non-empty file set and produced no
  candidate from it: a statement about the diff, but a weak one, and not the
  same statement as "candidates were examined and no check fired".

Each route is asserted against ``ext-point-self-review-surfacing.md`` — the
contract every implementor writes to — with the CLASSIFIABLE set as its matched
negative control. The control is not decoration: a guard that only asserts "the
un-observed case is called out" passes equally well against a contract that
calls EVERY case un-observed, which would surface the whole world as
unclassified and say nothing.

**Scope.** The verdict LITERALS and their partition over the workflow document
are owned by ``test_pre_submission_self_review_verdict.py``. This module reads
the ext-point contract that makes the two routes distinguishable, and touches
the workflow document only where a route's predicate is tied to it.
"""

from __future__ import annotations

import re

from _dispatch_roster import section_lines
from conftest import MARKETPLACE_ROOT

_SKILLS = MARKETPLACE_ROOT / 'plan-marshall' / 'skills'
_EXT_POINT_DOC = (
    _SKILLS
    / 'extension-api'
    / 'standards'
    / 'ext-point-self-review-surfacing.md'
)
_WORKFLOW_DOC = (
    _SKILLS / 'phase-6-finalize' / 'workflow' / 'pre-submission-self-review.md'
)

_FAILURE_MODE_HEADING = '## Failure Mode Contract'
_DELTA_COVERAGE_HEADING = (
    '### `delta_coverage` — what the round observed over what it searched'
)
_STOP_PREFIXES = ('### ', '## ', '# ', '---')

#: A markdown table body row: at least two ``|``-delimited cells, and not the
#: ``|---|---|`` separator.
_TABLE_ROW = re.compile(r'^\|(?P<cells>.+)\|\s*$')
_TABLE_SEPARATOR = re.compile(r'^\|[\s:|-]+\|\s*$')


def _ext_point_text() -> str:
    text: str = _EXT_POINT_DOC.read_text(encoding='utf-8')
    return text


def _workflow_text() -> str:
    text: str = _WORKFLOW_DOC.read_text(encoding='utf-8')
    return text


def _section(text: str, heading: str) -> str:
    return '\n'.join(section_lines(text, heading, _STOP_PREFIXES))


def _table_rows(section: str) -> list[tuple[str, str]]:
    """Return ``(condition, output)`` for every body row of a two-column table."""
    rows: list[tuple[str, str]] = []
    for line in section.splitlines():
        stripped = line.strip()
        if not stripped.startswith('|') or _TABLE_SEPARATOR.match(stripped):
            continue
        match = _TABLE_ROW.match(stripped)
        if match is None:
            continue
        cells = [cell.strip() for cell in match.group('cells').split('|')]
        if len(cells) < 2:
            continue
        if cells[0].lower() == 'condition':
            continue
        rows.append((cells[0], ' | '.join(cells[1:])))
    return rows


_FAILURE_MODE_ROWS = _table_rows(_section(_ext_point_text(), _FAILURE_MODE_HEADING))

# Non-emptiness asserted at IMPORT, before anything sweeps the rows. An empty
# table would make every route assertion below pass over nothing, and the
# per-row control could not distinguish "no row is special" from "every row is".
assert _FAILURE_MODE_ROWS, (
    f'No Failure Mode Contract row was parsed from {_EXT_POINT_DOC.name} — both '
    f'route assertions and the classifiable-set control would sweep an empty '
    f'population'
)

#: Published on EVERY run — passing included — by the root conftest's
#: ``pytest_report_header``. The import-time assertion above fails an EMPTY
#: table; publishing the size is what makes a SHRUNKEN one visible on the green
#: run, where no failure message is ever rendered.
GUARD_POPULATION_LABEL = 'self-review failure-mode conditions'
GUARD_POPULATION_SIZE = len(_FAILURE_MODE_ROWS)

#: The not-run verdict literal — the one string that may report route 1. Pinned
#: exactly, because the literal IS the contract: a consumer matching a whole
#: verdict string is what keeps the routes apart at read time.
_NOT_RUN_VERDICT = 'self-review not run: no surfacer implementor resolved'

#: The route-1 condition marker in the Failure Mode Contract's condition cell.
_NO_IMPLEMENTOR_MARKER = re.compile(r'no\s+domain\s+implementor\s+resolved', re.I)

#: The prohibition route 1's output cell must carry: the not-run outcome may not
#: be reported under the same verdict as a round that ran and surfaced zero.
_COLLAPSE_PROHIBITION = re.compile(r'MUST\s+NOT\s+be\s+reported\s+under\s+the\s+same')


def _route_one_rows() -> list[tuple[str, str]]:
    return [
        (condition, output)
        for condition, output in _FAILURE_MODE_ROWS
        if _NO_IMPLEMENTOR_MARKER.search(condition)
    ]


def _classifiable_rows() -> list[tuple[str, str]]:
    """Every failure-mode row that is NOT route 1 — the matched control set."""
    return [
        (condition, output)
        for condition, output in _FAILURE_MODE_ROWS
        if not _NO_IMPLEMENTOR_MARKER.search(condition)
    ]


def _route_one_output() -> str:
    """The output cell of the single no-implementor row.

    Asserted rather than indexed, so a table that lost the row fails naming the
    population size instead of raising an ``IndexError``.
    """
    rows = _route_one_rows()
    assert len(rows) == 1, (
        f'Expected exactly one no-implementor row across the '
        f'{len(_FAILURE_MODE_ROWS)}-row Failure Mode Contract, got {len(rows)}'
    )
    return rows[0][1]


# ---------------------------------------------------------------------------
# Route 1 — no implementor resolves
# ---------------------------------------------------------------------------


def test_route_one_is_declared_exactly_once_as_its_own_condition():
    matched = _route_one_rows()

    assert len(matched) == 1, (
        f'The no-implementor route must be exactly one condition of the '
        f'{len(_FAILURE_MODE_ROWS)}-row Failure Mode Contract — folded into a '
        f'sibling row, or split across several, it stops being separately '
        f'reportable. Matched: {[c for c, _output in matched]}'
    )


def test_route_one_reports_the_not_run_verdict():
    output = _route_one_output()

    assert _NOT_RUN_VERDICT in output, (
        f'The no-implementor condition does not name the not-run verdict '
        f'{_NOT_RUN_VERDICT!r}, so nothing in the contract stops it being '
        f'recorded under a verdict that claims a file set was searched'
    )


def test_route_one_forbids_collapsing_into_a_ran_and_surfaced_zero_verdict():
    output = _route_one_output()

    assert _COLLAPSE_PROHIBITION.search(output), (
        'The no-implementor condition names the not-run verdict but states no '
        'prohibition against reporting it under the same verdict as a round '
        'that RAN and surfaced zero — the collapse that turns absence of '
        'analysis into absence of defects'
    )


# ---------------------------------------------------------------------------
# Route 1's matched control — the classifiable set is still classified
# ---------------------------------------------------------------------------


def test_the_classifiable_conditions_are_a_non_empty_control_set():
    """Route 1 must be the exception, not the rule.

    A contract in which every condition were the un-run one would satisfy every
    assertion above while reporting the entire failure surface as un-analysed —
    the silent green in its widest form.
    """
    classifiable = _classifiable_rows()

    assert classifiable, (
        f'Every one of the {len(_FAILURE_MODE_ROWS)} failure-mode conditions '
        f'matched the no-implementor route, so the contract classifies nothing '
        f'and the route-1 assertions above measure the whole table'
    )
    assert len(classifiable) == len(_FAILURE_MODE_ROWS) - 1


def test_every_classifiable_condition_states_its_own_output():
    classifiable = _classifiable_rows()
    silent = [condition for condition, output in classifiable if not output.strip()]

    assert not silent, (
        f'These classifiable conditions carry no output disposition, so they '
        f'are conditions the contract names without saying what is reported for '
        f'them: {silent} (control set: {len(classifiable)} of '
        f'{len(_FAILURE_MODE_ROWS)} rows)'
    )


def test_no_classifiable_condition_borrows_the_not_run_verdict():
    leaked = [c for c, output in _classifiable_rows() if _NOT_RUN_VERDICT in output]

    assert not leaked, (
        f'These conditions describe a surfacer that RAN, yet report the not-run '
        f'verdict — which would restate an executed analysis as one that never '
        f'happened, collapsing the two routes from the other direction: {leaked}'
    )


# ---------------------------------------------------------------------------
# Route 2 — an implementor resolves, runs, and observes nothing
# ---------------------------------------------------------------------------


def test_route_two_block_is_required_on_every_surface():
    """A block emitted only when something was found cannot distinguish a round
    that observed nothing from a round that was never asked — route 2 exactly."""
    section = _section(_ext_point_text(), _DELTA_COVERAGE_HEADING)
    assert section.strip(), (
        f'{_DELTA_COVERAGE_HEADING!r} is empty in {_EXT_POINT_DOC.name} — every '
        f'route-2 assertion below would be vacuous'
    )

    assert 'emitted on EVERY surface' in section, (
        'The delta_coverage contract no longer requires the block on every '
        'surface, so a round that surfaced nothing can return no coverage block '
        'at all and read as an ordinary clean pass'
    )


def test_route_two_zero_is_readable_only_against_a_non_empty_population():
    """A zero must be qualified by the population it was drawn over.

    ``files_with_candidates: 0`` means "measured, none found" only when the
    round's own ``files`` is non-zero. Without that qualification a wrong-domain
    implementor that searched nothing publishes the same zero as one that
    searched everything.
    """
    section = _section(_ext_point_text(), _DELTA_COVERAGE_HEADING)

    assert 'files > 0' in section, (
        'The delta_coverage contract no longer conditions the zero reading on '
        'the class own `files > 0`, so a zero over nothing and a zero over '
        'something are indistinguishable to a consumer'
    )
    assert 'absence of measurement, not a measurement of absence' in section, (
        'The delta_coverage contract no longer states that a zero over an empty '
        'population is an absence of MEASUREMENT — the reading that separates a '
        'wrong-domain round from a genuinely clean one'
    )


def test_route_two_predicate_is_tied_to_the_zero_observation_verdict():
    """The verdict is the consumer's, but the predicate it keys on is the
    ext-point's ``delta_coverage`` field — which is what ties the two documents
    together, so the tie is read from the workflow."""
    text = _workflow_text()

    assert 'delta_coverage.files_with_candidates == 0' in text, (
        'The workflow selects no verdict on '
        '`delta_coverage.files_with_candidates == 0`, so a round that drew no '
        'observation from a non-empty scope reads as an ordinary clean pass'
    )
    assert 'non-zero `files_in_scope`' in text, (
        'The zero-observation predicate no longer requires a NON-ZERO '
        '`files_in_scope`, so an empty scope selects the same verdict as a real '
        'scope that yielded nothing — collapsing route 2 into the empty case'
    )


# ---------------------------------------------------------------------------
# Route 2's matched control — the classified reading survives
# ---------------------------------------------------------------------------


def test_route_two_control_keeps_the_measured_none_found_reading():
    """Without a classifiable reading the route-2 assertions would be satisfied
    by a contract declaring every zero unmeasurable — reporting the whole
    surface as unclassified, which says nothing about any round."""
    section = _section(_ext_point_text(), _DELTA_COVERAGE_HEADING)

    assert re.search(r'a zero reads as .{0,2}measured, none found', section), (
        'The delta_coverage contract dropped the "measured, none found" '
        'reading, so no zero it publishes is classifiable at all'
    )
    assert re.search(r'missing key reads as .{0,2}not measured', section), (
        'The delta_coverage contract no longer contrasts a MISSING key with a '
        'zero, so the two readings the block exists to separate are not stated'
    )


def test_route_two_class_partition_is_total_over_the_scope():
    """A contract that emitted only the classes it saw would let a wrong-domain
    implementor report a tidy, complete-looking block over the one class it
    happens to understand."""
    section = _section(_ext_point_text(), _DELTA_COVERAGE_HEADING)

    assert 'Every declared content class is emitted, seeded to zero' in section, (
        'The delta_coverage contract no longer requires every declared content '
        'class to be emitted, so a class the round never looked at can be '
        'omitted rather than reported as unmeasured'
    )
    assert 'class partition is total over the scope' in section, (
        'The delta_coverage contract no longer requires the class partition to '
        'be total, so the per-class counts need not account for every file'
    )


# ---------------------------------------------------------------------------
# Mutation guards — the row parser and the route matcher must be able to fail
# ---------------------------------------------------------------------------


def test_table_parser_reads_a_synthetic_two_column_table():
    synthetic = (
        '| Condition | Output |\n'
        '|-----------|--------|\n'
        '| No domain implementor resolved (consumer dispatch) | the not-run verdict |\n'
        '| Live footprint empty | `status: success` with empty candidate lists |\n'
    )

    rows = _table_rows(synthetic)

    assert len(rows) == 2, (
        f'The table parser did not read a synthetic two-row table, so the '
        f'derived failure-mode population would be unrelated to the document. '
        f'Got: {rows}'
    )
    assert rows[0][0].startswith('No domain implementor resolved')
    assert rows[1][1].startswith('`status: success`')


def test_route_matcher_separates_the_no_implementor_row_from_its_siblings():
    synthetic = [
        ('No domain implementor resolved (consumer dispatch)', 'not-run'),
        ('Live footprint empty', 'empty candidate lists'),
        ('Git unavailable or wrong cwd', 'error'),
    ]

    matched = [
        condition
        for condition, _output in synthetic
        if _NO_IMPLEMENTOR_MARKER.search(condition)
    ]

    assert matched == ['No domain implementor resolved (consumer dispatch)'], (
        f'The route-1 matcher does not isolate the no-implementor condition — '
        f'the route assertions and their control set would be drawn from the '
        f'same rows. Got: {matched}'
    )


def test_collapse_prohibition_detector_fires_only_on_the_prohibiting_wording():
    prohibiting = (
        'It MUST NOT be reported under the same verdict as a round that ran and '
        'surfaced zero candidates'
    )
    permissive = (
        'The consumer step succeeds without dispatching the LLM cognitive phase '
        '(outcome=done, empty candidate envelope)'
    )

    assert _COLLAPSE_PROHIBITION.search(prohibiting), (
        'The collapse-prohibition detector does not fire on the shipped '
        'wording, so the route-1 assertion would fail for the wrong reason'
    )
    assert not _COLLAPSE_PROHIBITION.search(permissive), (
        'The collapse-prohibition detector fires on prose carrying no '
        'prohibition, so the route-1 assertion would be vacuously green'
    )
