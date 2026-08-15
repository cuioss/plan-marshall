#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The review-versus-gate delta: what review caught that the in-house gates did not.

A full green in-house sweep is not evidence of correctness, and nothing quantified
the residual. This module is the measurement — an OBSERVABILITY signal about the
GATES, never a merge verdict and never a statement about a reviewer.

Why the delta needs no per-finding gate attribution
---------------------------------------------------
The in-house gates run BEFORE review: ``pre-push-quality-gate`` at ``order: 5`` and
``pre-submission-self-review`` at ``order: 7``, while ``automatic-review`` is
``order: 30``. So a finding review files against a tree the gates already passed is
something the gates ran over and did not report — a gate escape — with no
per-finding attribution needed. That is why the signal arrives free on every PR
rather than needing a bespoke corpus.

**But "the gates passed" is not the same claim as "the gates saw this tree", and
the difference is not hypothetical here.** Two ``mutates_source: true`` steps run
BETWEEN the gates and review — ``finalize-step-simplify`` (``order: 8``) and
``finalize-step-security-audit`` (``order: 9``) — and the dispatcher's re-entry
check (``phase-6-finalize/SKILL.md`` Step 3 item 1) only re-fires a step the loop
REACHES. A forward pass runs 5 → 7 → 8 → 9 → 11 → 20 → 30 monotonically and never
returns to order 5, so lines those two steps introduce reach the reviewer having
never been gated. Counting a finding on such a line as a gate escape would
attribute to the gates a miss they were never given the chance to make, and would
bias the share in an unknown direction.

The escape claim therefore rests on THREE inputs, each of which fails closed:

* ``gates_green`` — a red gate means nothing escaped anything.
* ``gate_head_sha`` — the tree the gates certified (the ``head_at_completion`` the
  gate step recorded).
* ``reviewed_head_sha`` — the tree review actually reviewed (the
  ``reviewed_commit_sha`` the findings carry).

The two SHAs must be EQUAL, proven rather than assumed. An absent SHA is not
evidence of sameness, and a mismatch is positive evidence of the gap above; both
resolve to ``excluded`` rather than to a confident zero. (The unblocking condition
is for the gate to re-fire after the mutating steps — that is a change to the
finalize step ordering, deliberately not made here.)

Two properties that keep the signal from becoming harmful
---------------------------------------------------------
1. **Refusal-PRs are excluded BY CONSTRUCTION, not filtered afterwards.** The review
   bots refuse frequently — rate windows, hard quotas, size ceilings — so an absence
   of review findings is very often an absence of *review*, not of defects. A metric
   that scored a refusal-PR as "zero escapes" would report **improving parity
   exactly as reviewer coverage collapsed**, which is this epic's named failure mode
   and the reason a metric that can produce it must not ship.

   The guard is structural rather than advisory: ``structural_share`` is emitted
   only at FULL coverage (every enabled reviewer in the roster reviewed the diff).
   A coverage collapse can therefore only ever move the metric from *a number* to
   *no number* — never to a better number. Partial coverage is the dangerous case
   and it is handled the same way, because a partial collapse silently re-weights
   the partition: if the reviewer that finds the gate-addressable defects goes quiet,
   the surviving escapes are all structural and a naive share reports 100% — "the
   gates are perfectly configured" — when the only thing that changed is who spoke.

2. **Partition before any rate.** The escape set is MIXED. Some escapes are
   *gate-addressable*: a lint rule family omitted from the local ``select`` list, an
   unsorted traversal, a symlink-through copy — the bot caught what a gate COULD
   have caught, which is a gate-CONFIGURATION finding rather than evidence of a
   structural bot-only class. Others are *gate-structural*: documentation-prose
   semantics, report-claim consistency, behaviour under inputs no test supplies. A
   share computed before that partition reads a fixable configuration hole as
   irreducible residual. An escape carrying no admissible label is therefore
   :data:`PARTITION_UNPARTITIONED` and WITHHOLDS the share; it is never defaulted
   into a bucket, since defaulting would let a typo move the number.

The counting rule is CONSUMED, not re-derived
---------------------------------------------
Three plans in this epic need per-reviewer finding counts and the epic keeps exactly
one rule, owned by ``automatic-review/standards/bot-participation-contract.md``
§ "The counting rule". This module consumes it:

* the escape count is over **filed** ``pr-comment`` findings, after the producer's
  pre-filter dropped noise, refusals, self-responses and cross-iteration duplicates
  — never a raw comment count;
* only **actionable** findings count: ``inline`` and *substantive* ``review_body``,
  while ``issue_comment`` and unknown kinds are meta. "Substantive" carries the
  rule's explicit carve-out — the count is *"never a count of review-body
  summaries"* — so a reviewer's ``"Actionable comments posted: N"`` status summary
  is meta, not an escape. Without that carve-out the numerator would gain one
  phantom escape on essentially every PR that reviewer touches;
* the **reviewed-at-all** predicate is supplied by the caller from
  ``review_completeness``'s ``_REVIEWED_STATES`` (``participated`` /
  ``participated_but_empty``), so this module never invents a second notion of
  whether a reviewer reviewed;
* every figure publishes the **population** it was computed over.

Usage:
    review_gate_delta.py assess --plan-id <id> [--enabled-bots [<csv>]]
        [--reviewed-bots [<csv>]] [--gates-green | --gates-red]
        [--gate-head-sha <sha>] [--reviewed-head-sha <sha>]
        [--partitions [<csv of hash_id:label>]]
    review_gate_delta.py --help
"""

from __future__ import annotations

import argparse
import sys

import bot_registry
from _findings_core import query_findings
from toon_parser import serialize_toon

VERDICT_MEASURED = 'measured'
VERDICT_EXCLUDED = 'excluded'

#: The bot caught what an in-house gate COULD have caught — a gate-CONFIGURATION
#: finding (a rule family absent from the select list, an un-enabled check). It is
#: actionable on our side and is NOT evidence of a structural bot-only class.
PARTITION_GATE_ADDRESSABLE = 'gate_addressable'

#: No in-house gate CLASS can reach this defect however it is configured —
#: documentation-prose semantics, report-claim consistency, behaviour under inputs
#: no test supplies. This is the genuine residual the parity question is about.
PARTITION_GATE_STRUCTURAL = 'gate_structural'

#: No admissible label was supplied. The fail-closed value: it is reported, counted,
#: and it WITHHOLDS the share rather than being bucketed by default.
PARTITION_UNPARTITIONED = 'unpartitioned'

_ADMISSIBLE_PARTITIONS = frozenset({PARTITION_GATE_ADDRESSABLE, PARTITION_GATE_STRUCTURAL})

#: Finding kinds that carry an actionable review claim, per the counting rule. A
#: walkthrough ``issue_comment`` is reviewer boilerplate, not a defect the gates
#: missed, and an absent/unknown kind cannot be shown to be one.
_ACTIONABLE_KINDS = frozenset({'inline', 'review_body'})

#: The finding fields that can carry a comment's BODY, in preference order. The
#: producer quarantines the untrusted body under ``raw_input.body``; the batched
#: ``manage-findings ingest`` pass then validates it and promotes it to the clean
#: TOP-LEVEL ``body`` field, which is the one a consumer reads (the containment
#: invariant in ``plan-marshall/workflow/triage.md`` forbids reading ``raw_input.*``
#: outside audit). ``title`` and ``detail`` are NOT in this list and must not be:
#: ``github_pr.cmd_fetch_findings`` builds them from structured metadata only, so a
#: signature matched against them can never fire on a real record.
_BODY_FIELDS = ('body', 'message')

#: Reasons a PR contributes no delta figure. Each is an honest "this PR is not
#: evidence" rather than a zero.
EXCLUSION_NO_ROSTER = 'no_reviewer_roster'
EXCLUSION_NO_REVIEWER = 'no_reviewer_reviewed'
EXCLUSION_GATES_RED = 'gates_not_green'
EXCLUSION_GATE_UNKNOWN = 'gate_state_unsubstantiated'
#: The gates passed, but over a DIFFERENT tree than the one review reviewed — the
#: post-gate `mutates_source` window the module docstring describes.
EXCLUSION_GATE_TREE_STALE = 'gates_did_not_cover_reviewed_tree'
#: One or both tree identities are missing, so sameness cannot be shown. Absence is
#: never read as sameness.
EXCLUSION_GATE_TREE_UNKNOWN = 'gate_tree_unsubstantiated'

#: Reasons the share is withheld on an otherwise-measured PR.
WITHHELD_PARTIAL_COVERAGE = 'partial_reviewer_coverage'
WITHHELD_UNPARTITIONED = 'unpartitioned_escapes'
WITHHELD_NO_ESCAPES = 'no_escapes_to_partition'

_PROVENANCE = (
    'escapes are the actionable pr-comment findings filed against a tree the '
    'in-house gates had already passed — gate verdict green AND gate_head_sha == '
    'reviewed_head_sha — counted per the counting rule in '
    'automatic-review/standards/bot-participation-contract.md; the reviewed-at-all '
    'set is review_completeness\'s _REVIEWED_STATES, supplied by the caller. '
    'SELECTION EFFECT: on the current finalize step ordering, finalize-step-simplify '
    '(order 8) and finalize-step-security-audit (order 9) mutate source after the '
    'gates (5, 7) and a forward pass never re-gates their edits, so the ONLY '
    'measurable PRs are those where neither step committed anything. That is a '
    'biased population, not a random sample, and few measurements will accumulate '
    'until the gate re-fires after those steps'
)


def resolve_bot_kind(record: dict) -> str:
    """Resolve a finding's ``bot_kind``, falling back to its author login.

    Two selectors, because ``bot_kind`` is not always present: ``add_finding`` OMITS
    the key when the producer could not classify the author, and the GitLab producer
    (``gitlab_pr``) never sets it at all. Keying on ``bot_kind`` alone would silently
    disable every per-bot rule on the whole GitLab path; keying on ``author`` alone
    would miss a record classified without a recognised login. Resolving one from the
    other through the registry's own login map keeps a single answer for both.
    """
    bot_kind = str(record.get('bot_kind') or '')
    if bot_kind:
        return bot_kind
    return bot_registry.login_to_bot_kind().get(str(record.get('author') or ''), '')


def is_status_summary(record: dict) -> bool:
    """True when a ``review_body`` record is the reviewer's META status summary.

    Three properties, each load-bearing:

    1. **The signature comes from the registry** (``review_body_summary_patterns``),
       keyed by :func:`resolve_bot_kind`. No login and no bot-kind literal appears
       here — that identity is the registry's, and a second copy of it in a counter
       is the hard-coded-population archetype.
    2. **It is matched against the BODY**, via :data:`_BODY_FIELDS`. Matching
       ``title`` / ``detail`` — which the producer builds from structured metadata
       and which never contain the comment text — is a carve-out that cannot fire.
    3. **The body must BEGIN with the pattern**, after leading whitespace and
       markdown emphasis are stripped. A status summary is a body that *opens* with
       its status line; a genuine review that merely mentions the phrase further down
       is not one.

    **Why begins-with and not "the status line is the only line".** An earlier
    attempt tested whether any later line followed, which inverted the result on both
    realistic shapes: a real summary is ``**Actionable comments posted: 3**`` followed
    by a details block, so it was COUNTED, while a one-line body carrying the phrase
    plus same-line substance was DROPPED. Line position does not carry "is there
    review content"; opening position does carry "is this a status line".

    **Known residual, stated rather than hidden.** A genuine review whose body opens
    by quoting the phrase and continues on the same line is still classified meta.
    That under-counts by at most one finding per reviewer per PR, and it is the
    direction that flatters the gates — so it is a real, bounded cost, accepted
    because the alternative (matching nowhere, or anywhere) is wrong on the far more
    common pure-summary shape. Narrowing it further needs a content predicate this
    text match cannot supply; the registry's ``contentless_review_markers`` /
    ``actionable_content_markers`` pair is the mechanism for that, and CodeRabbit
    declares neither today.

    A bot declaring no summary pattern can never reach ``True``: every one of its
    ``review_body`` records stays counted.
    """
    patterns = bot_registry.review_body_summary_patterns(resolve_bot_kind(record))
    body = next((str(record[f]) for f in _BODY_FIELDS if record.get(f)), '')
    # Normalise BOTH sides of a registry comparison (the project's rule — see
    # `github_pr._is_contentless_boilerplate`): a padded registry entry must not
    # silently disable the carve-out, and an empty entry must not match everything.
    opening = body.lstrip().lstrip('*_# ').lower()
    if not opening:
        return False
    return any(
        opening.startswith(cleaned)
        for cleaned in (p.strip().lower() for p in patterns)
        if cleaned
    )


def _is_actionable(record: dict) -> bool:
    """Classify one finding as an actionable review claim, per the counting rule.

    ``inline`` is actionable; ``review_body`` is actionable UNLESS it is the status
    summary the rule explicitly excludes; everything else (``issue_comment``, an
    absent or unknown kind) is meta.
    """
    kind = record.get('kind') or ''
    if kind == 'review_body':
        return not is_status_summary(record)
    return kind in _ACTIONABLE_KINDS


def assess_delta(
    findings: list[dict],
    enabled_bots: list[str],
    reviewed_bots: list[str],
    gates_green: bool | None,
    gate_head_sha: str | None = None,
    reviewed_head_sha: str | None = None,
    partitions: dict[str, str] | None = None,
) -> dict:
    """Measure what review caught on a PR whose in-house gates were already green.

    Args:
        findings: The plan's ``pr-comment`` finding records. Only actionable ones
            (per the counting rule) count as escapes.
        enabled_bots: The enabled reviewer roster (``bot_kind`` values) — the
            coverage denominator.
        reviewed_bots: The reviewers positively substantiated as having reviewed the
            diff, from ``review_completeness``'s reviewed-at-all set. Coverage is
            the INTERSECTION with the roster: an off-roster reviewer cannot complete
            a roster none of whose members reviewed.
        gates_green: Whether the in-house gates passed before review ran. ``None``
            means the caller supplied no signal, which fails CLOSED to
            ``excluded`` — crediting an un-instrumented PR as a clean measurement is
            the absence-read-as-evidence defect.
        gate_head_sha: The tree the gates CERTIFIED — the ``head_at_completion`` the
            gate step recorded on its terminal ``mark-step-done``.
        reviewed_head_sha: The tree review actually REVIEWED — the
            ``reviewed_commit_sha`` the findings carry. Must equal
            ``gate_head_sha``; see the module docstring for the post-gate
            ``mutates_source`` window that makes them diverge on an ordinary
            forward pass. An absent value is not evidence of sameness.
        partitions: ``finding hash_id -> partition label``. A finding with no
            admissible label is :data:`PARTITION_UNPARTITIONED`.

    Returns:
        A TOON-serialisable dict. ``verdict`` is :data:`VERDICT_MEASURED` or
        :data:`VERDICT_EXCLUDED`; ``structural_share`` is a percentage or ``None``
        with ``share_withheld`` naming the reason. Every figure is accompanied by
        the population it was computed over, and the envelope restates the ceiling
        (``proves: gate_escape_only``, ``gates_merge: false``) so a consumer cannot
        read it as a merge verdict.

        **A withheld share is not a withheld observation.** The escapes a partial
        round did surface are real and are still reported; only the ratio — the
        thing a shrinking denominator corrupts — is withheld.
    """
    labels = dict(partitions or {})
    roster = sorted(set(enabled_bots))
    reviewed = sorted(set(reviewed_bots))
    covered = sorted(set(roster) & set(reviewed))
    coverage = f'{len(covered)}/{len(roster)}'

    escapes = [
        {
            'finding_id': str(record.get('hash_id') or ''),
            'bot_kind': str(record.get('bot_kind') or ''),
            'partition': (
                labels.get(str(record.get('hash_id') or ''), PARTITION_UNPARTITIONED)
                if labels.get(str(record.get('hash_id') or '')) in _ADMISSIBLE_PARTITIONS
                else PARTITION_UNPARTITIONED
            ),
        }
        for record in findings
        if _is_actionable(record)
    ]
    by_partition = {
        PARTITION_GATE_ADDRESSABLE: sum(
            1 for e in escapes if e['partition'] == PARTITION_GATE_ADDRESSABLE
        ),
        PARTITION_GATE_STRUCTURAL: sum(
            1 for e in escapes if e['partition'] == PARTITION_GATE_STRUCTURAL
        ),
        PARTITION_UNPARTITIONED: sum(
            1 for e in escapes if e['partition'] == PARTITION_UNPARTITIONED
        ),
    }

    payload: dict = {
        'status': 'success',
        # A statement about the GATES' reach, never about a reviewer and never a
        # merge decision — restated machine-readably so it cannot be read as one.
        'proves': 'gate_escape_only',
        'gates_merge': False,
        'reviewer_coverage': coverage,
        'enabled_bots': roster,
        'reviewed_bots': reviewed,
        'escapes_total': len(escapes),
        'by_partition': by_partition,
        'escapes': escapes,
        'structural_share': None,
        'share_withheld': None,
        # The two tree identities the escape claim rests on, echoed so a reader can
        # see WHICH trees were compared rather than trusting that they were.
        'gate_head_sha': gate_head_sha or '',
        'reviewed_head_sha': reviewed_head_sha or '',
        'provenance': _PROVENANCE,
    }

    exclusion = _exclusion_reason(roster, covered, gates_green, gate_head_sha, reviewed_head_sha)
    if exclusion is not None:
        payload['verdict'] = VERDICT_EXCLUDED
        payload['exclusion_reason'] = exclusion
        # An excluded PR contributes NO delta figure. The escape list stays for
        # visibility, but the totals must not read as a measurement.
        payload['share_withheld'] = exclusion
        return payload

    payload['verdict'] = VERDICT_MEASURED
    payload['share_withheld'] = _share_withheld_reason(covered, roster, by_partition, len(escapes))
    if payload['share_withheld'] is None:
        structural = by_partition[PARTITION_GATE_STRUCTURAL]
        payload['structural_share'] = round(100.0 * structural / len(escapes), 1)
    return payload


def _exclusion_reason(
    roster: list[str],
    covered: list[str],
    gates_green: bool | None,
    gate_head_sha: str | None,
    reviewed_head_sha: str | None,
) -> str | None:
    """Return why this PR is not evidence, or ``None`` when it is.

    Checked in strength order so exactly one reason is assigned. The gate reasons
    come FIRST because a red gate, an unknown gate state, or a gate that certified a
    different tree each invalidate the escape claim ITSELF, whereas the coverage
    reasons invalidate only the population the claim is computed over.
    """
    if gates_green is None:
        return EXCLUSION_GATE_UNKNOWN
    if not gates_green:
        return EXCLUSION_GATES_RED
    if not gate_head_sha or not reviewed_head_sha:
        return EXCLUSION_GATE_TREE_UNKNOWN
    if gate_head_sha != reviewed_head_sha:
        return EXCLUSION_GATE_TREE_STALE
    if not roster:
        # 0/0 is not full coverage. Treating an empty roster as complete would make
        # every un-reviewed repository report perfect parity.
        return EXCLUSION_NO_ROSTER
    if not covered:
        return EXCLUSION_NO_REVIEWER
    return None


def _share_withheld_reason(
    covered: list[str], roster: list[str], by_partition: dict[str, int], total: int
) -> str | None:
    """Return why the share cannot be computed, or ``None`` when it can.

    Partial coverage is withheld for the reason the module docstring gives: a
    collapse re-weights the partition, so the ratio would move for a reason that has
    nothing to do with the gates.
    """
    if len(covered) < len(roster):
        return WITHHELD_PARTIAL_COVERAGE
    if by_partition[PARTITION_UNPARTITIONED]:
        return WITHHELD_UNPARTITIONED
    if not total:
        # Full coverage, everything partitioned, and nothing escaped. A real and
        # good outcome — but 0/0 is not a share, and reporting 100% or 0% here
        # would be inventing a number.
        return WITHHELD_NO_ESCAPES
    return None


def _split_csv(raw: str | None) -> list[str]:
    """Split a bare-form CSV flag into its non-empty members."""
    return [item.strip() for item in (raw or '').split(',') if item.strip()]


def _parse_partitions(raw: str | None) -> dict[str, str]:
    """Parse a ``hash_id:label`` CSV into a finding -> partition-label map.

    A malformed token is SKIPPED rather than rejected, and the finding it named then
    resolves to :data:`PARTITION_UNPARTITIONED` — which withholds the share. The
    fail-closed direction is already the permissive one here, so a loud rejection
    would buy nothing a withheld share does not already buy.
    """
    labels: dict[str, str] = {}
    for entry in (raw or '').split(','):
        entry = entry.strip()
        if not entry:
            continue
        hash_id, sep, label = entry.partition(':')
        if not sep or not hash_id.strip() or not label.strip():
            continue
        labels[hash_id.strip()] = label.strip()
    return labels


def _emit_toon(payload: dict) -> None:
    """Serialise the payload through the shared TOON writer.

    Deliberately NOT a hand-rolled emitter. The workflow doc instructs a reader to
    parse these fields, and a bespoke renderer is a second serialisation format that
    can drift from the shared one with no test to notice — the shape of a defect
    that ships green.
    """
    print(serialize_toon(payload))


def cmd_assess(args: argparse.Namespace) -> int:
    """Read the plan's pr-comment findings, assess the delta, emit TOON."""
    try:
        findings = query_findings(args.plan_id, finding_type='pr-comment')['findings']
    except (OSError, ValueError) as exc:
        _emit_toon({'status': 'error', 'error': 'load_failure', 'detail': str(exc)})
        return 1
    payload = assess_delta(
        findings,
        _split_csv(args.enabled_bots),
        _split_csv(args.reviewed_bots),
        args.gates_green,
        gate_head_sha=args.gate_head_sha,
        reviewed_head_sha=args.reviewed_head_sha,
        partitions=_parse_partitions(args.partitions),
    )
    _emit_toon(payload)
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the argparse parser with a single ``assess`` subcommand."""
    parser = argparse.ArgumentParser(
        description=(
            'Measure what review caught that the in-house gates did not. An '
            'observability signal about the GATES — never a merge verdict, never a '
            'statement about a reviewer.'
        ),
        allow_abbrev=False,
    )
    sub = parser.add_subparsers(dest='command', required=True)

    assess = sub.add_parser(
        'assess',
        help='Assess the review-versus-gate delta for one PR',
        allow_abbrev=False,
    )
    assess.add_argument('--plan-id', required=True, help='Plan identifier.')
    assess.add_argument(
        '--enabled-bots',
        nargs='?',
        const='',
        default='',
        help=(
            'Comma-separated enabled reviewer bot_kinds — the coverage DENOMINATOR '
            '(required_bots ∪ optional_bots). An empty roster is excluded rather '
            'than vacuously complete: 0/0 is not full coverage. May be supplied bare '
            '(no value), which reads as the empty roster.'
        ),
    )
    assess.add_argument(
        '--reviewed-bots',
        nargs='?',
        const='',
        default='',
        help=(
            'Comma-separated bot_kinds positively substantiated as having REVIEWED '
            'the diff — review_completeness\'s reviewed-at-all set (participated / '
            'participated_but_empty). Coverage is the intersection with the roster, '
            'so an off-roster reviewer cannot complete it. May be supplied bare (no '
            'value), which reads as nobody reviewed — an excluded PR, never a clean '
            'zero.'
        ),
    )
    gate_state = assess.add_mutually_exclusive_group()
    gate_state.add_argument(
        '--gates-green',
        dest='gates_green',
        action='store_true',
        default=None,
        help=(
            'Pass when the in-house gates PASSED before review ran, which is what '
            'makes every subsequent review finding a gate escape. Omitting BOTH gate '
            'flags leaves the state unsubstantiated and excludes the PR — an absent '
            'signal is never read as green.'
        ),
    )
    gate_state.add_argument(
        '--gates-red',
        dest='gates_green',
        action='store_false',
        help=(
            'Pass when the in-house gates FAILED. Nothing escaped a gate that had '
            'not passed, so the PR is excluded rather than scored.'
        ),
    )
    assess.add_argument(
        '--gate-head-sha',
        dest='gate_head_sha',
        default='',
        help=(
            'The tree the gates CERTIFIED — the head_at_completion the '
            'pre-push-quality-gate step recorded. Must equal --reviewed-head-sha: '
            'two mutates_source steps (finalize-step-simplify order 8, '
            'finalize-step-security-audit order 9) run between the gates and review '
            'on an ordinary forward pass, so a differing SHA means the reviewer saw '
            'lines the gates never did. Omitting it excludes the PR — an absent SHA '
            'is not evidence of sameness.'
        ),
    )
    assess.add_argument(
        '--reviewed-head-sha',
        dest='reviewed_head_sha',
        default='',
        help=(
            'The tree review actually REVIEWED — the reviewed_commit_sha the '
            'pr-comment findings carry. See --gate-head-sha for why the two must '
            'match and why an absent value excludes rather than assumes.'
        ),
    )
    assess.add_argument(
        '--partitions',
        nargs='?',
        const='',
        default='',
        help=(
            'Comma-separated hash_id:label pairs partitioning each escape by whether '
            'an in-house gate COULD have caught it: gate_addressable (a gate '
            'configuration finding) or gate_structural (no gate class can reach it). '
            'An escape with no admissible label is unpartitioned and WITHHOLDS the '
            'structural share — the partition comes before any rate, never after. '
            'May be supplied bare (no value), which reads as no labels at all.'
        ),
    )
    assess.set_defaults(func=cmd_assess)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point."""
    args = build_parser().parse_args(argv)
    rc: int = args.func(args)
    return rc


if __name__ == '__main__':
    sys.exit(main())
