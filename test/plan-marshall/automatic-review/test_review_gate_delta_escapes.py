#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Unit tests for the review-versus-gate delta signal (plan 130 D2).

*"What did review catch that the in-house gates did not"* is the only direct read
on gate/review parity available, and it arrives free on every PR: the gates run
before review (`pre-push-quality-gate` at order 5, self-review at 7, against
`automatic-review` at 30), so a finding filed against a tree the gates already
passed IS a gate escape. No per-finding gate attribution is needed.

**But "the gates passed" is not "the gates saw this tree".** Source-mutating steps
run between certification and review — `finalize-step-simplify` (8) and
`finalize-step-security-audit` (9), and the gate itself (5), whose own item-5f
commit lands after the tree it just certified — and a forward pass never returns to
order 5 to re-gate their edits, so the escape claim rests on the gate-certified tree
and the reviewed tree being the SAME tree, proven by SHA rather than assumed. No
count is pinned here: membership is whatever each step's declared `mutates_source`
makes it, so a step that declares the fact later is covered by its own declaration.

Three properties make the signal usable rather than harmful, and all are tested
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

* **The escape claim is anchored to a tree.** A gate verdict, a gate-certified SHA,
  and a reviewed SHA — each absent or mismatched one excludes the PR, so a finding
  on a line the gates never saw is never counted as a miss they made.
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

_ROSTER = ['coderabbit', 'cuioss-review-bot', 'sourcery']

#: The tree the gates certified and the tree review reviewed — equal in the
#: measurable case, and the whole subject of the post-gate-mutation exclusion.
_SHA = 'a' * 40


def _finding(hash_id, bot_kind='coderabbit', kind='inline'):
    return {'hash_id': hash_id, 'bot_kind': bot_kind, 'kind': kind}


def _full_coverage(**overrides):
    """A fully-reviewed PR with a complete partition — the only shape that yields a share."""
    kwargs = {
        'findings': [_finding('f1'), _finding('f2'), _finding('f3')],
        'enabled_bots': _ROSTER,
        'reviewed_bots': list(_ROSTER),
        'gates_green': True,
        'gate_head_sha': _SHA,
        'reviewed_head_sha': _SHA,
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


def test_a_tree_the_gates_never_saw_is_excluded():
    """Source-mutating finalize steps run BETWEEN gate certification and review.

    `pre-push-quality-gate` is order 5 and self-review 7, but `finalize-step-simplify`
    (8) and `finalize-step-security-audit` (9) are `mutates_source: true` and run
    after them — as is the gate itself, whose item-5f commit lands after the tree it
    certified; the dispatcher's re-entry check only re-fires a step the loop
    REACHES, and a forward pass never returns to order 5. So a line those steps
    introduced reaches the reviewer at order 30 having never been gated.

    Counting a finding on such a line as a "gate escape" attributes to the gates a
    miss they were never given the chance to make. The gate-certified tree and the
    reviewed tree must therefore be the SAME tree, proven by SHA rather than
    asserted.
    """
    result = _full_coverage(reviewed_head_sha='b' * 40)

    assert result['verdict'] == VERDICT_EXCLUDED
    assert result['exclusion_reason'] == 'gates_did_not_cover_reviewed_tree'
    assert result['structural_share'] is None


def test_an_absent_tree_identity_fails_closed_to_excluded():
    """Without both SHAs the trees cannot be shown equal, so the escape claim is unproven.

    Absence must not read as "same tree" — that is the assumption the finding above
    showed to be false in the ordinary forward pass.
    """
    for missing in ({'gate_head_sha': ''}, {'reviewed_head_sha': ''}):
        result = _full_coverage(**missing)
        assert result['verdict'] == VERDICT_EXCLUDED, missing
        assert result['exclusion_reason'] == 'gate_tree_unsubstantiated', missing


def test_the_coderabbit_status_summary_is_not_an_escape():
    """The counting rule excludes review-body SUMMARIES — consumed, not re-derived.

    `bot-participation-contract.md` § "The counting rule" says the count is "never a
    count of review-body summaries", naming `"Actionable comments posted: N"`. The
    review-retrospective aggregator already implements that carve-out; a second
    counter without it would count CodeRabbit's status summary as a gate escape on
    essentially every PR CodeRabbit reviews, inflating the numerator that the
    structural share divides.
    """
    findings = [
        _finding('f1', kind='inline'),
        {
            'hash_id': 'summary',
            'bot_kind': 'coderabbit',
            'kind': 'review_body',
            'author': 'coderabbitai',
            # The REACHABLE field. `github_pr` builds title/detail from structured
            # metadata and quarantines the comment text under raw_input.body, which
            # the batched ingest pass promotes to top-level `body`. A fixture that
            # puts the signature in `title` would pass against a carve-out that can
            # never fire on a real record — which is exactly how one shipped.
            'title': 'PR #42 review_body comment by coderabbitai (99)',
            'detail': 'pr_number: 42\nkind: review_body\nauthor: coderabbitai',
            'body': 'Actionable comments posted: 3',
        },
    ]

    result = assess_delta(
        findings=findings,
        enabled_bots=_ROSTER,
        reviewed_bots=list(_ROSTER),
        gates_green=True,
        gate_head_sha=_SHA,
        reviewed_head_sha=_SHA,
        partitions={'f1': PARTITION_GATE_STRUCTURAL, 'summary': PARTITION_GATE_STRUCTURAL},
    )

    assert result['escapes_total'] == 1
    assert {e['finding_id'] for e in result['escapes']} == {'f1'}


def test_the_signature_in_title_or_detail_does_not_drop_a_finding():
    """The carve-out reads the BODY only — the field the comment text reaches.

    `github_pr.cmd_fetch_findings` builds `title` from structured metadata and
    quarantines the text under `raw_input.body`. A carve-out matched against
    title/detail can never fire on a real record; one matched against BOTH could be
    tricked by metadata that merely mentions the phrase.
    """
    findings = [
        {
            'hash_id': 'real',
            'bot_kind': 'coderabbit',
            'kind': 'review_body',
            'author': 'coderabbitai',
            'title': 'Actionable comments posted: 3',
            'detail': 'Actionable comments posted: 3',
            'body': 'The guard coerces UNKNOWN into a positive.',
        },
    ]

    result = assess_delta(
        findings=findings,
        enabled_bots=_ROSTER,
        reviewed_bots=list(_ROSTER),
        gates_green=True,
        gate_head_sha=_SHA,
        reviewed_head_sha=_SHA,
        partitions={'real': PARTITION_GATE_STRUCTURAL},
    )

    assert result['escapes_total'] == 1


def test_a_real_summary_with_its_details_block_is_meta():
    """The shape a real status summary takes: the status line, then a details block.

    An earlier attempt tested whether any LATER LINE followed, which inverted the
    result on exactly this shape — it was counted as an escape. Opening position is
    what carries "this is a status line"; line count does not.
    """
    from review_gate_delta import is_status_summary

    assert is_status_summary(
        {
            'bot_kind': 'coderabbit',
            'kind': 'review_body',
            'body': '**Actionable comments posted: 3**\n\n<details>\nwalkthrough\n</details>',
        }
    )


def test_a_review_mentioning_the_phrase_mid_body_is_still_an_escape():
    """Only a body that OPENS with the status line is a summary.

    A genuine review that refers to the phrase further down is not boilerplate, and
    dropping it would under-count escapes — the direction that flatters the gates.
    """
    findings = [
        {
            'hash_id': 'mentions',
            'bot_kind': 'coderabbit',
            'kind': 'review_body',
            'author': 'coderabbitai',
            'body': 'The guard coerces UNKNOWN into a positive.\n\nActionable comments posted: 1',
        },
    ]

    result = assess_delta(
        findings=findings,
        enabled_bots=_ROSTER,
        reviewed_bots=list(_ROSTER),
        gates_green=True,
        gate_head_sha=_SHA,
        reviewed_head_sha=_SHA,
        partitions={'mentions': PARTITION_GATE_STRUCTURAL},
    )

    assert result['escapes_total'] == 1


def test_the_known_residual_is_pinned_rather_than_hidden():
    """A body opening with the status line AND carrying same-line substance is meta.

    This is the rule's documented cost, pinned so it is a KNOWN limitation rather
    than an undiscovered one: it under-counts by at most one finding per reviewer per
    PR, in the direction that flatters the gates. Narrowing it needs a content
    predicate a text match cannot supply (the registry's contentless /
    actionable-content marker pair is that mechanism, and CodeRabbit declares
    neither). Change this assertion only alongside the docstring that states the
    cost.
    """
    from review_gate_delta import is_status_summary

    assert is_status_summary(
        {
            'bot_kind': 'coderabbit',
            'kind': 'review_body',
            'body': 'Actionable comments posted: 1. Guard the array bound here.',
        }
    )


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
        gate_head_sha=_SHA,
        reviewed_head_sha=_SHA,
        partitions={'f1': PARTITION_GATE_STRUCTURAL, 'meta1': PARTITION_GATE_STRUCTURAL},
    )

    assert result['escapes_total'] == 1
    assert {e['finding_id'] for e in result['escapes']} == {'f1'}


def test_the_envelope_states_that_it_gates_nothing():
    """An observability signal about the gates, never a merge verdict."""
    result = _full_coverage()

    assert result['proves'] == 'gate_escape_only'
    assert result['gates_merge'] is False
