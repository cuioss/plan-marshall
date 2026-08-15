#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The review-versus-gate delta: what review caught that the in-house gates did not.

A full green in-house sweep is not evidence of correctness, and nothing quantified
the residual. This module is the measurement — an OBSERVABILITY signal about the
GATES, never a merge verdict and never a statement about a reviewer.

Why the delta needs no per-finding gate attribution
---------------------------------------------------
The in-house gates run FIRST: ``pre-push-quality-gate`` at ``order: 5``,
``pre-submission-self-review`` immediately after, and the branch only reaches
``push`` / ``create-pr`` / ``automatic-review`` (``order: 30``) once they are green.
So on a PR whose gates passed, **every finding review then files is by construction
a gate escape** — something the gates ran over and did not report. That is why the
signal arrives free on every PR rather than needing a bespoke corpus.

The gate state is therefore load-bearing input, not decoration. On a RED-gate PR
nothing escaped anything, and absent any gate signal at all the escape claim is
unsubstantiated — both resolve to ``excluded`` rather than to a confident zero.

Two properties that keep the signal from becoming harmful
---------------------------------------------------------
1. **Refusal-PRs are excluded BY CONSTRUCTION, not filtered afterwards.** The review
   bots refuse frequently — rate windows, hard quotas, size ceilings — so an absence
   of review findings is very often an absence of *review*, not of defects. A metric
   that scored a refusal-PR as "zero escapes" would report **improving parity
   exactly as reviewer coverage collapsed**, which is this epic's named failure mode
   and the reason a metric that can produce it must not ship.

   The guard is structural rather than advisory: :data:`STRUCTURAL_SHARE` is emitted
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
* only **actionable** findings count, by the same ``kind`` classification the
  review-retrospective applies (``inline`` and substantive ``review_body``;
  ``issue_comment`` and unknown kinds are meta);
* the **reviewed-at-all** predicate is supplied by the caller from
  ``review_completeness``'s ``_REVIEWED_STATES`` (``participated`` /
  ``participated_but_empty``), so this module never invents a second notion of
  whether a reviewer reviewed;
* every figure publishes the **population** it was computed over.

Usage:
    review_gate_delta.py assess --plan-id <id> [--enabled-bots [<csv>]]
        [--reviewed-bots [<csv>]] [--gates-green | --gates-red]
        [--partitions [<csv of hash_id:label>]]
    review_gate_delta.py --help
"""

from __future__ import annotations

import argparse
import sys

from _findings_core import query_findings

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

#: Reasons a PR contributes no delta figure. Each is an honest "this PR is not
#: evidence" rather than a zero.
EXCLUSION_NO_ROSTER = 'no_reviewer_roster'
EXCLUSION_NO_REVIEWER = 'no_reviewer_reviewed'
EXCLUSION_GATES_RED = 'gates_not_green'
EXCLUSION_GATE_UNKNOWN = 'gate_state_unsubstantiated'

#: Reasons the share is withheld on an otherwise-measured PR.
WITHHELD_PARTIAL_COVERAGE = 'partial_reviewer_coverage'
WITHHELD_UNPARTITIONED = 'unpartitioned_escapes'
WITHHELD_NO_ESCAPES = 'no_escapes_to_partition'

_PROVENANCE = (
    'escapes are the actionable pr-comment findings filed on a PR whose in-house '
    'gates had already passed (pre-push-quality-gate order 5, self-review next, '
    'automatic-review order 30), counted per the counting rule in '
    'automatic-review/standards/bot-participation-contract.md; the reviewed-at-all '
    'set is review_completeness\'s _REVIEWED_STATES, supplied by the caller'
)


def _is_actionable(record: dict) -> bool:
    """Classify one finding as an actionable review claim, per the counting rule."""
    return (record.get('kind') or '') in _ACTIONABLE_KINDS


def assess_delta(
    findings: list[dict],
    enabled_bots: list[str],
    reviewed_bots: list[str],
    gates_green: bool | None,
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
        'provenance': _PROVENANCE,
    }

    exclusion = _exclusion_reason(roster, covered, gates_green)
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


def _exclusion_reason(roster: list[str], covered: list[str], gates_green: bool | None) -> str | None:
    """Return why this PR is not evidence, or ``None`` when it is.

    Checked in strength order so exactly one reason is assigned. The gate state is
    checked FIRST because a red or unknown gate invalidates the escape claim itself,
    whereas the coverage reasons invalidate only the population.
    """
    if gates_green is None:
        return EXCLUSION_GATE_UNKNOWN
    if not gates_green:
        return EXCLUSION_GATES_RED
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
    """Print the delta TOON block."""
    print(f'status: {payload.get("status", "success")}')
    if payload.get('status') == 'error':
        print(f'error: {payload.get("error", "unknown")}')
        if 'detail' in payload:
            print(f'detail: {payload["detail"]}')
        return
    print(f'verdict: {payload["verdict"]}')
    if payload.get('exclusion_reason'):
        print(f'exclusion_reason: {payload["exclusion_reason"]}')
    print(f'proves: {payload["proves"]}')
    print('gates_merge: ' + ('true' if payload['gates_merge'] else 'false'))
    print(f'reviewer_coverage: {payload["reviewer_coverage"]}')
    print(f'escapes_total: {payload["escapes_total"]}')
    share = payload['structural_share']
    print('structural_share: ' + ('null' if share is None else f'{share}'))
    if payload.get('share_withheld'):
        print(f'share_withheld: {payload["share_withheld"]}')
    print(f'provenance: {payload["provenance"]}')
    counts = payload['by_partition']
    print(f'by_partition[{len(counts)}]{{partition,count}}:')
    for partition, count in counts.items():
        print(f'  {partition},{count}')
    for field in ('enabled_bots', 'reviewed_bots'):
        values = payload[field]
        if values:
            print(f'{field}[{len(values)}]:')
            for value in values:
                print(f'  - {value}')
    escapes = payload['escapes']
    if escapes:
        print(f'escapes[{len(escapes)}]{{finding_id,bot_kind,partition}}:')
        for record in escapes:
            print(f'  {record["finding_id"]},{record["bot_kind"]},{record["partition"]}')


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
        _parse_partitions(args.partitions),
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
