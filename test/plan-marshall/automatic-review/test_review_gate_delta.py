#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Unit tests for the review-versus-gate delta signal (plan 130 D2).

*"What did review catch that the in-house gates did not"* is the only direct read
on gate/review parity available, and it arrives free on every PR: the gates run
before review (`pre-push-quality-gate` at order 5, self-review at 7, against
`automatic-review` at 30), so a finding filed against a tree the gates already
passed IS a gate escape. No per-finding gate attribution is needed.

**But "the gates passed" is not "the gates saw this tree".** Two `mutates_source`
steps run between them — `finalize-step-simplify` (8) and
`finalize-step-security-audit` (9) — and a forward pass never returns to order 5 to
re-gate their edits, so the escape claim rests on the gate-certified tree and the
reviewed tree being the SAME tree, proven by SHA rather than assumed.

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
        gate_head_sha=_SHA,
        reviewed_head_sha=_SHA,
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
        findings=[_finding('f2', bot_kind='cuioss-review-bot'), _finding('f3', bot_kind='cuioss-review-bot')],
        enabled_bots=_ROSTER,
        reviewed_bots=['cuioss-review-bot'],
        gates_green=True,
        gate_head_sha=_SHA,
        reviewed_head_sha=_SHA,
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
        findings=[_finding('f2', bot_kind='cuioss-review-bot')],
        enabled_bots=_ROSTER,
        reviewed_bots=['cuioss-review-bot'],
        gates_green=True,
        gate_head_sha=_SHA,
        reviewed_head_sha=_SHA,
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
        gate_head_sha=_SHA,
        reviewed_head_sha=_SHA,
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
        gate_head_sha=_SHA,
        reviewed_head_sha=_SHA,
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


def test_a_tree_the_gates_never_saw_is_excluded():
    """Two source-mutating finalize steps run BETWEEN the gates and review.

    `pre-push-quality-gate` is order 5 and self-review 7, but `finalize-step-simplify`
    (8) and `finalize-step-security-audit` (9) are `mutates_source: true` and run
    after them; the dispatcher's re-entry check only re-fires a step the loop
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


def test_a_padded_registry_entry_still_matches(monkeypatch):
    """Both sides of a registry comparison are normalised — the project's rule.

    A padded entry must not silently disable the carve-out. The padding is INJECTED
    here: asserting against the real (unpadded) registry entry would pass with or
    without the `.strip()`, which is a guard that pins nothing.
    """
    import bot_registry
    from review_gate_delta import is_status_summary

    monkeypatch.setattr(
        bot_registry, 'review_body_summary_patterns', lambda _k: ['  Actionable comments posted:  ']
    )

    assert is_status_summary(
        {'bot_kind': 'coderabbit', 'kind': 'review_body', 'body': 'Actionable comments posted: 5'}
    )


def test_an_empty_registry_entry_does_not_match_everything(monkeypatch):
    """An empty entry must not drop every review_body from that bot.

    Without the `if cleaned` filter, `''` is a prefix of every string, so a stray
    `- ""` in a registry doc would silently classify the bot's whole review output
    as boilerplate — a total, invisible suppression.
    """
    import bot_registry
    from review_gate_delta import is_status_summary

    monkeypatch.setattr(bot_registry, 'review_body_summary_patterns', lambda _k: ['', '   '])

    assert not is_status_summary(
        {'bot_kind': 'coderabbit', 'kind': 'review_body', 'body': 'A real review comment.'}
    )


def test_a_bot_login_carrying_the_bot_suffix_still_resolves(monkeypatch):
    """The author fallback normalises the login, so `[bot]` and casing still classify.

    Exercised through the classifier rather than the resolver alone, because the
    failure mode is silent: an unresolved login yields no patterns, so the carve-out
    simply never fires and every status summary counts as an escape.
    """
    from review_gate_delta import is_status_summary

    for login in ('coderabbitai[bot]', 'CodeRabbitAI', 'CodeRabbitAI[bot]'):
        assert is_status_summary(
            {'author': login, 'kind': 'review_body', 'body': 'Actionable comments posted: 5'}
        ), login


def test_a_bot_declaring_no_summary_pattern_keeps_every_review_body():
    """The fail-closed default is COUNTED, because dropping is the dangerous direction."""
    from review_gate_delta import is_status_summary

    assert not is_status_summary(
        {'bot_kind': 'sourcery', 'kind': 'review_body', 'body': 'Actionable comments posted: 2'}
    )


def test_a_substantive_review_body_from_another_author_is_still_an_escape():
    """The carve-out is gated on the author AND the signature — not on the kind.

    Dropping every `review_body` would discard the surface where the review bots
    file their consolidated findings, which is the bulk of what they report.
    """
    findings = [
        {
            'hash_id': 'real',
            'bot_kind': 'sourcery',
            'kind': 'review_body',
            'author': 'sourcery-ai',
            'title': 'Guard coerces UNKNOWN into a positive',
            'detail': '',
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


# ---------------------------------------------------------------------------
# CLI surface — the contract the workflow docs actually invoke
# ---------------------------------------------------------------------------


class TestCLI:
    """The ``assess`` verb's argparse surface and emitted TOON block.

    The pure function above is where the logic lives, but the CLI is what
    `finalize-step-review-retrospective` invokes and what a reader parses. An
    emitter or flag defect ships green if only the pure function is exercised.
    """

    def test_emits_toon_and_zero_exit(self, plan_context):
        from conftest import get_script_path, run_script

        script = get_script_path('plan-marshall', 'automatic-review', 'review_gate_delta.py')
        plan_id = 'rgd-cli'
        plan_context.plan_dir_for(plan_id)

        result = run_script(
            script,
            'assess',
            '--plan-id',
            plan_id,
            '--enabled-bots',
            'coderabbit,sourcery',
            '--reviewed-bots',
            'coderabbit,sourcery',
            '--gates-green',
            '--gate-head-sha',
            _SHA,
            '--reviewed-head-sha',
            _SHA,
        )

        assert result.success, result.stderr
        assert 'status: success' in result.stdout
        assert 'proves: gate_escape_only' in result.stdout
        assert 'gates_merge: false' in result.stdout
        assert 'reviewer_coverage: 2/2' in result.stdout

    def test_omitting_both_gate_flags_excludes_rather_than_assuming_green(self, plan_context):
        """The fail-closed default reaches the CLI, not only the pure function."""
        from conftest import get_script_path, run_script

        script = get_script_path('plan-marshall', 'automatic-review', 'review_gate_delta.py')
        plan_id = 'rgd-cli-nogate'
        plan_context.plan_dir_for(plan_id)

        result = run_script(script, 'assess', '--plan-id', plan_id)

        assert result.success, result.stderr
        assert 'verdict: excluded' in result.stdout
        assert 'gate_state_unsubstantiated' in result.stdout

    def test_gates_red_and_gates_green_are_mutually_exclusive(self):
        """Passing both is a caller error argparse refuses, not a silent last-wins."""
        from review_gate_delta import build_parser

        with pytest.raises(SystemExit):
            build_parser().parse_args(
                ['assess', '--plan-id', 'p', '--gates-green', '--gates-red']
            )

    def test_bare_list_flags_read_as_empty(self):
        """A caller interpolating an empty variable gets the empty list, not a rejection."""
        from review_gate_delta import build_parser

        args = build_parser().parse_args(
            ['assess', '--plan-id', 'p', '--enabled-bots', '--reviewed-bots', '--partitions']
        )

        assert args.enabled_bots == ''
        assert args.reviewed_bots == ''
        assert args.partitions == ''
        # No gate flag passed at all — the fail-closed sentinel, never False.
        assert args.gates_green is None

    def test_partitions_flag_parses_pairs_and_skips_malformed_tokens(self):
        from review_gate_delta import _parse_partitions

        assert _parse_partitions('a:gate_structural,b:gate_addressable') == {
            'a': 'gate_structural',
            'b': 'gate_addressable',
        }
        # A bare token carries no label; skipping it leaves the finding
        # unpartitioned, which withholds the share — already the fail-closed side.
        assert _parse_partitions('a:gate_structural,bare,,c:') == {'a': 'gate_structural'}
