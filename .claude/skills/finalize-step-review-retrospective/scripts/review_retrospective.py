#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Deterministic per-reviewer review-quality aggregator over a plan's pr-comment findings.

Reads the plan's `pr-comment` findings (each carrying the first-class `author` and
`kind` fields), groups them by `(author, kind)`, and emits a per-reviewer
review-quality retrospective as TOON. Pure deterministic aggregation — NO LLM
logic, NO qualitative judgment. The qualitative judgment and comparative verdict
are produced by the `finalize-step-review-retrospective` SKILL.md workflow body,
which AUGMENTS these numbers; this script never reasons about comment content.

Classification rules (kind -> actionability):
- kind=inline                -> ACTIONABLE
- kind=review_body           -> ACTIONABLE when substantive; META when it is
                                CodeRabbit's status-summary ("Actionable comments
                                posted: N", detected via author=coderabbitai + the
                                status-summary signature in title/detail)
- kind=issue_comment         -> META/non-actionable (CodeRabbit walkthrough/poem)
- record lacking kind        -> bucketed as `unknown` kind, counted in raw_total
                                only (never in actionable_count)

Resolution -> quality mapping (positives vs false-positives):
- fixed                      -> true positive (real issue caught) -> positives
- rejected                   -> the reviewer was wrong            -> false_positives
- accepted / taken_into_account -> acknowledged-without-change    -> NEITHER bucket
- suppressed                 -> borderline
- pending                    -> unresolved / excluded

`accepted` and `taken_into_account` are acknowledgements: the reviewer said
something valid that the triage absorbed without a code change. They are tallied
in their own per-reviewer fields and are evidence of neither a caught defect nor a
wrong claim. `rejected` is the one disposition that means the reviewer was wrong,
so it is what drives `false_positives_count`.

Percentage denominator:
`pct_resolved_as_fixed` divides `actionable_fixed_count` by
`resolved_actionable_count` — the RESOLVED ACTIONABLE set, never `raw_total`.
Both operands filter on the same `_is_actionable` predicate, so META records
cannot dilute the ratio, and both exclude `pending`, so a record still awaiting
triage is not counted as evidence against the reviewer. The numerator is a strict
subset of the denominator by construction, so the value can never exceed 100.
When `resolved_actionable_count` is 0 the metric is `None` (emitted as TOON
`null`), NOT `0.0`: a reviewer with no resolved actionable comments has no rate to
report, and reporting a confident `0.0` would be exactly the wrong-number failure
this metric exists to avoid.

Records lacking an `author` are bucketed under `unattributed`.

Nested `<details>` content inside an inline comment is part of that single record
— it is NEVER split into multiple findings (the upstream producer already emits
one finding per comment).

Stdlib-only. When run via the executor the shared modules (`_findings_core`,
`toon_parser`) are importable from PYTHONPATH; the `main` read path uses them, but
the `aggregate` function is pure (operates on record dicts passed in) so it is
unit-testable without any plan on disk.
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from typing import Any

# Resolution buckets.
_POSITIVE_RESOLUTIONS = {'fixed'}
_FALSE_POSITIVE_RESOLUTIONS = {'rejected'}

# The canonical resolution enum — the only states that get their own per-reviewer
# counter. `_RESOLVED_RESOLUTIONS` is it minus `pending`: every state in which a
# finding has actually been decided, and the membership test behind
# `resolved_actionable_count`, the `pct_resolved_as_fixed` denominator. Derived
# rather than restated so a resolution added to the enum cannot be counted in one
# place and silently missed in the other.
_ALL_RESOLUTIONS = frozenset({'fixed', 'rejected', 'accepted', 'taken_into_account', 'suppressed', 'pending'})
_RESOLVED_RESOLUTIONS = _ALL_RESOLUTIONS - {'pending'}

# CodeRabbit's status-summary review_body is META, not actionable. Detected by the
# author login plus the status-summary signature in the title/detail.
_CODERABBIT_AUTHOR = 'coderabbitai'
_STATUS_SUMMARY_SIGNATURE = 'actionable comments posted'

_UNATTRIBUTED = 'unattributed'
_UNKNOWN_KIND = 'unknown'

# The COMPARISON grade — the instrument's self-assessment of whether the
# review-quality comparison it exists to perform could be performed AT ALL. It is
# distinct from the finalize-lifecycle `--outcome` (which has no `indeterminate`
# member and stays `done` so the non-fatal step never blocks finalize): this grade
# is the instrument grading ITS OWN work, not the step's completion.
#
# The load-bearing case is zero findings. An empty `pr-comment` store is ambiguous
# between two facts a bare "0 findings — nothing to compare" collapses: reviewers
# ran and found nothing (a legitimate no-op), versus NO reviewer produced content
# (the comparison was impossible — exactly the condition the instrument exists to
# detect). The findings store alone cannot tell them apart, because a reviewer that
# `participated_but_empty` files zero findings just like a silent one — so the
# reviewed-at-all signal (`participated` / `participated_but_empty`, per
# review_completeness's `_REVIEWED_STATES`) must be supplied by the caller as
# `reviewed_reviewers`. Absent that signal on a non-empty roster the grade fails
# CLOSED to `indeterminate`: the instrument must not mark a comparison complete it
# could not substantiate.
COMPARISON_MEASURED = 'measured'          # findings exist — the comparison was performed
COMPARISON_CLEAN = 'clean'                # 0 findings, but an ENABLED reviewer reviewed and found nothing
COMPARISON_VACUOUS = 'vacuous'            # 0 findings and NO reviewer roster configured — nothing to compare
COMPARISON_INDETERMINATE = 'indeterminate'  # 0 findings, roster configured, but no enabled reviewer produced content


def _grade_comparison(
    total_findings: int,
    enabled_reviewers: set[str],
    reviewed_reviewers: set[str],
) -> str:
    """Grade whether the review-quality comparison could be performed.

    The four grades are checked in strength order so exactly one is assigned:

    - **`measured`** — at least one finding exists, so there is content to compare.
    - **`vacuous`** — no findings AND no reviewer roster is configured, so nothing
      was ever expected to review. Genuinely nothing to compare — the honest empty.
      Checked BEFORE `clean` so an empty roster is `vacuous` even if some reviewer
      outside it happens to have reviewed: with no roster there is nothing to grade.
    - **`clean`** — no findings, but at least one **enabled** reviewer is positively
      substantiated as having reviewed (an enabled reviewer reviewed and found
      nothing). A legitimate no-op. The substantiation is `enabled_reviewers ∩
      reviewed_reviewers`: a reviewed identity OUTSIDE the enabled roster does not
      make the enabled population's comparison possible, so it cannot earn `clean`.
    - **`indeterminate`** — no findings, a roster IS configured, yet no enabled
      reviewer is substantiated as having reviewed. The comparison could not be
      performed, and the instrument MUST NOT report a benign done: `no reviewer
      produced content` is exactly the condition it exists to surface. This is also
      the fail-closed default when the caller supplies no `reviewed_reviewers` signal
      against a non-empty roster — an unsubstantiated review is never credited clean.

    Args:
        total_findings: the number of `pr-comment` findings in the store.
        enabled_reviewers: the enabled reviewer roster (`author_login` values).
        reviewed_reviewers: the reviewers positively substantiated as having
            reviewed the diff — the reviewed-at-all set (`participated` /
            `participated_but_empty`) from `review_completeness`, as `author_login`
            values. Empty when no such signal was supplied. Only the members that
            also appear in `enabled_reviewers` earn `clean`.

    Returns:
        One of :data:`COMPARISON_MEASURED`, :data:`COMPARISON_CLEAN`,
        :data:`COMPARISON_VACUOUS`, :data:`COMPARISON_INDETERMINATE`.
    """
    if total_findings > 0:
        return COMPARISON_MEASURED
    if not enabled_reviewers:
        return COMPARISON_VACUOUS
    if enabled_reviewers & reviewed_reviewers:
        return COMPARISON_CLEAN
    return COMPARISON_INDETERMINATE


def _is_coderabbit_status_summary(record: dict[str, Any]) -> bool:
    """True when a review_body record is CodeRabbit's META status summary.

    The signature ("Actionable comments posted: N") is matched case-insensitively
    against the record's title and detail, gated on the CodeRabbit author so a
    genuine substantive review_body from another reviewer is never mis-classed.
    """
    if (record.get('author') or '') != _CODERABBIT_AUTHOR:
        return False
    haystack = f"{record.get('title') or ''}\n{record.get('detail') or ''}".lower()
    return _STATUS_SUMMARY_SIGNATURE in haystack


def _is_actionable(record: dict[str, Any]) -> bool:
    """Classify a single record as actionable vs meta/non-actionable by kind.

    - inline           -> actionable
    - review_body      -> actionable unless it is CodeRabbit's status summary
    - issue_comment    -> meta (walkthrough/poem)
    - missing/unknown  -> not actionable (counted in raw_total only)
    """
    kind = record.get('kind')
    if kind == 'inline':
        return True
    if kind == 'review_body':
        return not _is_coderabbit_status_summary(record)
    # issue_comment, unknown, or missing kind.
    return False


def _empty_reviewer() -> dict[str, Any]:
    return {
        'raw_total': 0,
        'actionable_count': 0,
        'meta_count': 0,
        'fixed': 0,
        'accepted': 0,
        'taken_into_account': 0,
        'rejected': 0,
        'suppressed': 0,
        'pending': 0,
        'positives_count': 0,
        'false_positives_count': 0,
        'resolved_actionable_count': 0,
        'actionable_fixed_count': 0,
        'pct_resolved_as_fixed': None,
        'by_kind': defaultdict(int),
    }


def aggregate(
    records: list[dict[str, Any]],
    enabled_reviewers: list[str] | None = None,
    reviewed_reviewers: list[str] | None = None,
) -> dict[str, Any]:
    """Aggregate pr-comment finding records into a per-reviewer retrospective.

    Pure function — no I/O, no LLM. `records` is a list of finding dicts as stored
    by `manage-findings` (each may carry `author`, `kind`, `resolution`, `title`,
    `detail`). Returns a TOON-friendly dict:

        total_findings: N
        reviewers[]{author,participation,raw_total,actionable_count,meta_count,fixed,
                    accepted,taken_into_account,rejected,suppressed,pending,
                    positives_count,false_positives_count,
                    resolved_actionable_count,actionable_fixed_count,
                    pct_resolved_as_fixed}
        by_author_kind[]{author,kind,count}
        mappings: { kind->actionability, resolution->quality }

    `raw_total` and `actionable_count` are DISTINCT fields: meta comments
    (CodeRabbit status-summary review_body + walkthrough issue_comment + unknown
    kind) are counted into raw_total and meta_count but never inflate
    actionable_count. `resolved_actionable_count` and `actionable_fixed_count` are
    narrower still — both filter on that same `actionable_count` predicate AND on
    the record's resolution, and together they are the denominator and numerator of
    `pct_resolved_as_fixed`. `raw_total` feeds no ratio; it is a volume field only.
    Both operands are emitted as first-class fields so the percentage's denominator
    is visible to the reader rather than implied.

    **The row population is the ENABLED roster ∪ the observed authors, never the
    responding set alone.** `enabled_reviewers` is the set of `author_login` values
    for the reviewers this PR enabled (derived from the registry, see the SKILL.md).
    A reviewer that produced no comments, one that never ran, and one that was
    enabled-invoked-and-refused all leave the findings store with NO record — so
    deriving rows from the responding authors alone gives them no row at all, which
    renders those three distinct facts identically (the vacuous-set archetype: the
    detector's population becomes a strict subset of its own domain). Emitting a row
    per enabled reviewer closes that: an enabled reviewer with no record still gets a
    row, carrying `participation: unmeasurable` — the store substantiates neither
    participation nor absence for it, so it is named rather than silently omitted,
    and it is never scored or ranked (its metrics are all zero / `None`). A reviewer
    WITH at least one record carries `participation: measured`. When
    `enabled_reviewers` is omitted the population is the observed authors alone (the
    prior behaviour), so an existing caller is unchanged.

    **The `comparison` grade distinguishes a comparison that HAPPENED from one that
    was IMPOSSIBLE.** A zero-findings store is ambiguous: reviewers may have reviewed
    and found nothing (a legitimate no-op) or NO reviewer may have produced content
    (the comparison could not be performed). The findings store cannot tell them
    apart — a `participated_but_empty` reviewer files zero findings just like a
    silent one — so `reviewed_reviewers` supplies the reviewed-at-all signal
    (`participated` / `participated_but_empty` per `review_completeness`, as
    `author_login` values). The emitted `comparison` is `measured` (findings exist),
    `clean` (0 findings, a reviewer reviewed), `vacuous` (0 findings, no roster), or
    `indeterminate` (0 findings, a roster is configured, no reviewer reviewed). The
    last is the fail-closed default when `reviewed_reviewers` is omitted against a
    non-empty roster: the instrument never marks a comparison complete it could not
    substantiate. This grade is the instrument's assessment of its OWN work; it is
    not the finalize `--outcome`, which stays `done` so the non-fatal step never
    blocks finalize.
    """
    per_reviewer: dict[str, dict[str, Any]] = defaultdict(_empty_reviewer)
    per_author_kind: dict[tuple[str, str], int] = defaultdict(int)

    for record in records:
        author = record.get('author') or _UNATTRIBUTED
        kind = record.get('kind') or _UNKNOWN_KIND
        resolution = record.get('resolution') or 'pending'

        bucket = per_reviewer[author]
        bucket['raw_total'] += 1
        bucket['by_kind'][kind] += 1
        per_author_kind[(author, kind)] += 1

        actionable = _is_actionable(record)
        if actionable:
            bucket['actionable_count'] += 1
        else:
            bucket['meta_count'] += 1

        # Resolution buckets — only count the canonical enum.
        if resolution in _ALL_RESOLUTIONS:
            bucket[resolution] += 1

        if resolution in _POSITIVE_RESOLUTIONS:
            bucket['positives_count'] += 1
        elif resolution in _FALSE_POSITIVE_RESOLUTIONS:
            bucket['false_positives_count'] += 1

        # The pct_resolved_as_fixed operands — both gated on the SAME actionability
        # result computed above, so no second notion of "is this a real review
        # comment" can drift from `_is_actionable`.
        if actionable and resolution in _RESOLVED_RESOLUTIONS:
            bucket['resolved_actionable_count'] += 1
        if actionable and resolution in _POSITIVE_RESOLUTIONS:
            bucket['actionable_fixed_count'] += 1

    # The row population is the ENABLED roster ∪ the observed authors. An enabled
    # reviewer with no record still gets a row (D3), so "produced nothing", "never
    # ran", and "enabled-invoked-refused" no longer collapse into no-row. Accessing
    # ``per_reviewer[author]`` for an enabled-but-silent author materialises a zero
    # bucket via the defaultdict, which reads as ``participation: unmeasurable``.
    row_authors = sorted(set(per_reviewer) | set(enabled_reviewers or []))
    reviewers: list[dict[str, Any]] = []
    for author in row_authors:
        bucket = per_reviewer[author]
        raw_total = bucket['raw_total']
        resolved_actionable = bucket['resolved_actionable_count']
        # `None` — never 0.0 — when nothing resolved-and-actionable was measured.
        pct = (
            round(100.0 * bucket['actionable_fixed_count'] / resolved_actionable, 1)
            if resolved_actionable
            else None
        )
        # A row with at least one attributed record is `measured`; an enabled
        # reviewer the store is silent on is `unmeasurable` — named, never scored.
        participation = 'measured' if raw_total > 0 else 'unmeasurable'
        reviewers.append({
            'author': author,
            'participation': participation,
            'raw_total': raw_total,
            'actionable_count': bucket['actionable_count'],
            'meta_count': bucket['meta_count'],
            'fixed': bucket['fixed'],
            'accepted': bucket['accepted'],
            'taken_into_account': bucket['taken_into_account'],
            'rejected': bucket['rejected'],
            'suppressed': bucket['suppressed'],
            'pending': bucket['pending'],
            'positives_count': bucket['positives_count'],
            'false_positives_count': bucket['false_positives_count'],
            'resolved_actionable_count': resolved_actionable,
            'actionable_fixed_count': bucket['actionable_fixed_count'],
            'pct_resolved_as_fixed': pct,
        })

    by_author_kind = [
        {'author': author, 'kind': kind, 'count': count}
        for (author, kind), count in sorted(per_author_kind.items())
    ]

    # Grade whether the comparison could be performed at all — so a zero-findings
    # run that rests on NO reviewer having produced content is `indeterminate`,
    # never a benign done. The reviewed-at-all signal comes from the caller
    # (`reviewed_reviewers`); absent it on a non-empty roster the grade fails closed.
    comparison = _grade_comparison(
        len(records),
        set(enabled_reviewers or []),
        set(reviewed_reviewers or []),
    )

    return {
        'status': 'success',
        'total_findings': len(records),
        'reviewer_count': len(reviewers),
        'enabled_reviewers': sorted(enabled_reviewers or []),
        # The reviewers positively substantiated as having reviewed the diff, echoed
        # so the population behind the `comparison` grade is visible, never implied.
        'reviewed_reviewers': sorted(reviewed_reviewers or []),
        # The instrument's self-grade: did the review-quality comparison happen?
        # `indeterminate` marks a comparison that COULD NOT be performed (no reviewer
        # produced content), which a bare "0 findings — nothing to compare" hides.
        'comparison': comparison,
        'reviewers': reviewers,
        'by_author_kind': by_author_kind,
        'participation_states': {
            'measured': 'at least one record attributed — the reviewer can be judged',
            'unmeasurable': 'enabled but no record — store substantiates neither participation nor absence; never scored or ranked',
        },
        # Keys are the COMPARISON_* constants themselves, not string literals, so the
        # serialized legend cannot drift from the grades _grade_comparison can assign.
        'comparison_states': {
            COMPARISON_MEASURED: 'findings exist — the review-quality comparison was performed',
            COMPARISON_CLEAN: '0 findings, but an enabled reviewer reviewed and found nothing — a legitimate no-op',
            COMPARISON_VACUOUS: '0 findings and no reviewer roster configured — nothing was expected to compare',
            COMPARISON_INDETERMINATE: '0 findings, a roster was configured, but no enabled reviewer produced content — the comparison could NOT be performed; never a benign done',
        },
        'kind_actionability': {
            'inline': 'actionable',
            'review_body': 'actionable (meta when CodeRabbit status-summary)',
            'issue_comment': 'meta',
            'unknown': 'meta (raw_total only)',
        },
        'resolution_quality': {
            'fixed': 'true_positive',
            'accepted': 'acknowledged',
            'taken_into_account': 'acknowledged',
            'rejected': 'false_positive',
            'suppressed': 'borderline',
            'pending': 'excluded',
        },
    }


def _read_pr_comment_findings(plan_id: str) -> list[dict[str, Any]]:
    """Read the plan's pr-comment findings via the shared findings read path.

    Imported lazily so `aggregate` stays importable (and unit-testable) without the
    executor PYTHONPATH that supplies `_findings_core`.
    """
    from _findings_core import query_findings

    result = query_findings(plan_id, finding_type='pr-comment')
    if result.get('status') == 'error':
        raise RuntimeError(result.get('message') or 'Failed to query findings')
    findings: list[dict[str, Any]] = result.get('findings', [])
    return findings


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Deterministic per-reviewer review-quality aggregator over a plan's "
            "pr-comment findings. Emits TOON. No LLM logic."
        ),
        allow_abbrev=False,
    )
    parser.add_argument('command', choices=['run'], help='Subcommand (only `run`).')
    parser.add_argument('--plan-id', required=True, help='Plan identifier.')
    parser.add_argument(
        '--enabled-reviewers',
        nargs='?',
        const='',
        default='',
        help=(
            'Comma-separated author_login values for the reviewers this PR ENABLED '
            '(the registry roster — see the SKILL.md). Every enabled reviewer gets a '
            'row even when it produced no comments, carrying participation: '
            'unmeasurable, so "produced nothing" / "never ran" / "enabled-invoked-'
            'refused" no longer collapse into having no row. May be supplied bare (no '
            'value), which reads as the empty roster — the prior observed-authors-only '
            'behaviour.'
        ),
    )
    parser.add_argument(
        '--reviewed-reviewers',
        nargs='?',
        const='',
        default='',
        help=(
            'Comma-separated author_login values for the reviewers positively '
            'substantiated as having REVIEWED the diff — the reviewed-at-all set '
            '(participated / participated_but_empty) from review_completeness. Feeds '
            'the `comparison` grade: on a zero-findings run it is what separates '
            '`clean` (a reviewer reviewed and found nothing) from `indeterminate` (no '
            'reviewer produced content — the comparison could not be performed). May '
            'be supplied bare (no value), which reads as the empty set; against a '
            'non-empty enabled roster that yields `indeterminate` — the instrument '
            'never credits an unsubstantiated review as a clean one.'
        ),
    )
    args = parser.parse_args(argv)

    try:
        from toon_parser import serialize_toon

        enabled_reviewers = [r.strip() for r in (args.enabled_reviewers or '').split(',') if r.strip()]
        reviewed_reviewers = [r.strip() for r in (args.reviewed_reviewers or '').split(',') if r.strip()]
        records = _read_pr_comment_findings(args.plan_id)
        result = aggregate(
            records,
            enabled_reviewers=enabled_reviewers,
            reviewed_reviewers=reviewed_reviewers,
        )
        sys.stdout.write(serialize_toon(result) + '\n')
        return 0
    except Exception as e:
        import json

        error_result = {'status': 'error', 'message': str(e)}
        sys.stdout.write(json.dumps(error_result) + '\n')
        return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
