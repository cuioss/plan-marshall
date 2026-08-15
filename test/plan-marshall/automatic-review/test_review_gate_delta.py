#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Unit tests for the review-versus-gate delta signal (plan 130 D2).

*"What did review catch that the in-house gates did not"* is the only direct read
on gate/review parity available, and it arrives free on every PR: the gates run
first (`pre-push-quality-gate` at order 5, self-review just after) and the branch
only reaches review once they are green, so **every finding review then files is,
by construction, a gate escape**. No per-finding gate attribution is needed.

Two properties make the signal usable rather than harmful, and both are tested
here in the direction that matters:

* **Refusal-PRs are excluded BY CONSTRUCTION.** The bots refuse frequently, so an
  absence of review findings is often an absence of *review*, not of defects. A
  metric that counted a refusal-PR as "zero escapes" would report improving parity
  precisely as reviewer coverage collapsed — this epic's named failure mode. The
  guard is structural: the share is emitted only at FULL coverage, so a collapse
  can only ever move the metric from a number to NO number, never to a better one.

* **Partition before any rate.** The escape set is mixed: some escapes are
  *gate-addressable* (a lint family absent from the select list — a gate
  CONFIGURATION finding), others *gate-structural* (documentation-prose semantics,
  behaviour under un-supplied inputs). A share computed before that partition would
  read a configuration gap as evidence of a structural bot-only class. An
  unpartitioned finding therefore withholds the share rather than being bucketed by
  default.
"""

import pytest
from review_gate_delta import (
    PARTITION_GATE_ADDRESSABLE,
    PARTITION_GATE_STRUCTURAL,
    PARTITION_UNPARTITIONED,
    VERDICT_EXCLUDED,
    VERDICT_MEASURED,
    assess_delta,
)

_ROSTER = ['coderabbit', 'pr-agent', 'sourcery']


def _finding(hash_id, bot_kind='coderabbit', kind='inline'):
    return {'hash_id': hash_id, 'bot_kind': bot_kind, 'kind': kind}


def _full_coverage(**overrides):
    """A fully-reviewed PR with a complete partition — the only shape that yields a share."""
    kwargs = {
        'findings': [_finding('f1'), _finding('f2'), _finding('f3')],
        'enabled_bots': _ROSTER,
        'reviewed_bots': list(_ROSTER),
        'gates_green': True,
        'partitions': {
            'f1': PARTITION_GATE_ADDRESSABLE,
            'f2': PARTITION_GATE_STRUCTURAL,
            'f3': PARTITION_GATE_STRUCTURAL,
        },
    }
    kwargs.update(overrides)
    return assess_delta(**kwargs)


# ---------------------------------------------------------------------------
# The measured case
# ---------------------------------------------------------------------------


def test_full_coverage_with_a_complete_partition_yields_a_share():
    """The one shape that produces a number: everyone reviewed, everything partitioned."""
    result = _full_coverage()

    assert result['verdict'] == VERDICT_MEASURED
    assert result['escapes_total'] == 3
    assert result['by_partition'][PARTITION_GATE_STRUCTURAL] == 2
    assert result['by_partition'][PARTITION_GATE_ADDRESSABLE] == 1
    assert result['structural_share'] == pytest.approx(66.7, abs=0.1)
    assert result['share_withheld'] is None


def test_the_verdict_publishes_its_population_and_provenance():
    """Every figure carries the population it was computed over — never a bare number."""
    result = _full_coverage()

    assert result['reviewer_coverage'] == '3/3'
    assert result['enabled_bots'] == sorted(_ROSTER)
    assert result['reviewed_bots'] == sorted(_ROSTER)
    assert result['provenance']


def test_each_escape_is_reported_individually_with_its_partition():
    """Three escapes are three rows — a bundled count loses the per-instance record."""
    result = _full_coverage()

    assert len(result['escapes']) == 3
    assert {e['finding_id'] for e in result['escapes']} == {'f1', 'f2', 'f3'}
    assert all(e['partition'] for e in result['escapes'])


# ---------------------------------------------------------------------------
# The refusal exclusion — the inversion this metric must not produce
# ---------------------------------------------------------------------------


def test_a_pr_no_reviewer_reviewed_is_excluded_not_scored_zero():
    """Zero escapes from a PR nobody reviewed is not evidence the gates caught everything.

    Counting it as a clean data point is what makes a parity metric report
    improving parity as coverage collapses.
    """
    result = assess_delta(
        findings=[],
        enabled_bots=_ROSTER,
        reviewed_bots=[],
        gates_green=True,
        partitions={},
    )

    assert result['verdict'] == VERDICT_EXCLUDED
    assert result['exclusion_reason'] == 'no_reviewer_reviewed'
    assert result['structural_share'] is None


def test_collapsing_coverage_withholds_the_share_it_never_improves_it():
    """THE inversion check the plan names: coverage collapses, parity must NOT improve.

    Same diff, same escapes, same partition — only the reviewer coverage changes.
    A metric that reported a HIGHER structural share here would be saying "the gates
    are better configured" when the only thing that happened is that the reviewer
    which finds the addressable defects went silent.
    """
    full = _full_coverage()
    assert full['structural_share'] == pytest.approx(66.7, abs=0.1)

    # The reviewer that filed the gate-addressable escape refuses. Its findings
    # never arrive, so the surviving escapes are ALL structural.
    collapsed = assess_delta(
        findings=[_finding('f2', bot_kind='pr-agent'), _finding('f3', bot_kind='pr-agent')],
        enabled_bots=_ROSTER,
        reviewed_bots=['pr-agent'],
        gates_green=True,
        partitions={'f2': PARTITION_GATE_STRUCTURAL, 'f3': PARTITION_GATE_STRUCTURAL},
    )

    # A naive metric would report 100% structural — "the gates are perfect".
    assert collapsed['structural_share'] is None
    assert collapsed['share_withheld'] == 'partial_reviewer_coverage'
    assert collapsed['reviewer_coverage'] == '1/3'


def test_partial_coverage_still_reports_the_escapes_it_saw():
    """Withholding the SHARE is not withholding the observation.

    The escapes a partial round did surface are real and are reported; only the
    ratio — the thing a shrinking denominator corrupts — is withheld.
    """
    result = assess_delta(
        findings=[_finding('f2', bot_kind='pr-agent')],
        enabled_bots=_ROSTER,
        reviewed_bots=['pr-agent'],
        gates_green=True,
        partitions={'f2': PARTITION_GATE_STRUCTURAL},
    )

    assert result['verdict'] == VERDICT_MEASURED
    assert result['escapes_total'] == 1
    assert result['structural_share'] is None


def test_a_reviewed_bot_outside_the_roster_does_not_earn_coverage():
    """Coverage is `enabled ∩ reviewed` — an off-roster reviewer cannot complete it.

    Without the intersection, naming any reviewer at all would satisfy full
    coverage over a roster none of whose members reviewed.
    """
    result = assess_delta(
        findings=[_finding('f1')],
        enabled_bots=_ROSTER,
        reviewed_bots=['some-other-bot'],
        gates_green=True,
        partitions={'f1': PARTITION_GATE_STRUCTURAL},
    )

    assert result['verdict'] == VERDICT_EXCLUDED
    assert result['reviewer_coverage'] == '0/3'


def test_an_empty_roster_is_excluded_rather_than_vacuously_complete():
    """No configured reviewer means no parity question — 0/0 is not full coverage.

    Treating an empty roster as complete would make every un-reviewed repository
    report perfect parity, which is the empty-looks-like-perfect signal again.
    """
    result = assess_delta(
        findings=[],
        enabled_bots=[],
        reviewed_bots=[],
        gates_green=True,
        partitions={},
    )

    assert result['verdict'] == VERDICT_EXCLUDED
    assert result['exclusion_reason'] == 'no_reviewer_roster'


# ---------------------------------------------------------------------------
# Partition before any rate
# ---------------------------------------------------------------------------


def test_an_unpartitioned_escape_withholds_the_share():
    """A share computed over a partly-unlabelled set is a rate with an unknown numerator."""
    result = _full_coverage(partitions={'f1': PARTITION_GATE_ADDRESSABLE})

    assert result['verdict'] == VERDICT_MEASURED
    assert result['by_partition'][PARTITION_UNPARTITIONED] == 2
    assert result['structural_share'] is None
    assert result['share_withheld'] == 'unpartitioned_escapes'


def test_an_unrecognised_partition_label_falls_to_unpartitioned():
    """A label outside the closed set is UNKNOWN, never silently bucketed as structural.

    Defaulting an unknown label into either bucket would let a typo move the share.
    """
    result = _full_coverage(
        partitions={'f1': 'probably_structural', 'f2': PARTITION_GATE_STRUCTURAL, 'f3': PARTITION_GATE_STRUCTURAL}
    )

    assert result['by_partition'][PARTITION_UNPARTITIONED] == 1
    assert result['structural_share'] is None


def test_partition_is_reported_even_when_the_share_is_withheld():
    """The partition counts are the useful observation; only the ratio is gated."""
    result = _full_coverage(partitions={'f1': PARTITION_GATE_ADDRESSABLE})

    assert result['by_partition'][PARTITION_GATE_ADDRESSABLE] == 1
    assert result['by_partition'][PARTITION_UNPARTITIONED] == 2


# ---------------------------------------------------------------------------
# Gate state — an escape claim needs a green gate to be an escape at all
# ---------------------------------------------------------------------------


def test_red_gates_exclude_the_pr_because_nothing_escaped():
    """A finding on a PR whose gates were RED is not a gate escape.

    The gates had not passed, so review finding something says nothing about what
    the gates cannot see.
    """
    result = _full_coverage(gates_green=False)

    assert result['verdict'] == VERDICT_EXCLUDED
    assert result['exclusion_reason'] == 'gates_not_green'


def test_an_unsubstantiated_gate_state_fails_closed_to_excluded():
    """Absent evidence the gates were green, the escape claim is unsubstantiated.

    `None` is the "caller supplied no gate signal" value and must not read as
    green — that would credit every un-instrumented PR as a clean measurement.
    """
    result = _full_coverage(gates_green=None)

    assert result['verdict'] == VERDICT_EXCLUDED
    assert result['exclusion_reason'] == 'gate_state_unsubstantiated'


# ---------------------------------------------------------------------------
# The counting rule — consumed, never re-derived
# ---------------------------------------------------------------------------


def test_meta_findings_are_not_counted_as_escapes():
    """The escape count is over ACTIONABLE findings, per the epic's counting rule.

    A walkthrough issue_comment is not a defect the gates missed; counting it would
    inflate every escape figure with reviewer boilerplate.
    """
    result = assess_delta(
        findings=[
            _finding('f1', kind='inline'),
            _finding('meta1', kind='issue_comment'),
        ],
        enabled_bots=_ROSTER,
        reviewed_bots=list(_ROSTER),
        gates_green=True,
        partitions={'f1': PARTITION_GATE_STRUCTURAL, 'meta1': PARTITION_GATE_STRUCTURAL},
    )

    assert result['escapes_total'] == 1
    assert {e['finding_id'] for e in result['escapes']} == {'f1'}


def test_the_envelope_states_that_it_gates_nothing():
    """An observability signal about the gates, never a merge verdict."""
    result = _full_coverage()

    assert result['proves'] == 'gate_escape_only'
    assert result['gates_merge'] is False
