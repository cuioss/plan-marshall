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

# The canonical resolution enum minus `pending` — every state in which a finding
# has actually been decided. This is the membership test behind
# `resolved_actionable_count`, the `pct_resolved_as_fixed` denominator.
_RESOLVED_RESOLUTIONS = frozenset({'fixed', 'rejected', 'accepted', 'taken_into_account', 'suppressed'})

# CodeRabbit's status-summary review_body is META, not actionable. Detected by the
# author login plus the status-summary signature in the title/detail.
_CODERABBIT_AUTHOR = 'coderabbitai'
_STATUS_SUMMARY_SIGNATURE = 'actionable comments posted'

_UNATTRIBUTED = 'unattributed'
_UNKNOWN_KIND = 'unknown'


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


def aggregate(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate pr-comment finding records into a per-reviewer retrospective.

    Pure function — no I/O, no LLM. `records` is a list of finding dicts as stored
    by `manage-findings` (each may carry `author`, `kind`, `resolution`, `title`,
    `detail`). Returns a TOON-friendly dict:

        total_findings: N
        reviewers[]{author,raw_total,actionable_count,meta_count,fixed,accepted,
                    taken_into_account,rejected,suppressed,pending,
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

        # Resolution buckets — only count the canonical six.
        if resolution in ('fixed', 'accepted', 'taken_into_account', 'rejected', 'suppressed', 'pending'):
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

    reviewers: list[dict[str, Any]] = []
    for author in sorted(per_reviewer):
        bucket = per_reviewer[author]
        raw_total = bucket['raw_total']
        resolved_actionable = bucket['resolved_actionable_count']
        # `None` — never 0.0 — when nothing resolved-and-actionable was measured.
        pct = (
            round(100.0 * bucket['actionable_fixed_count'] / resolved_actionable, 1)
            if resolved_actionable
            else None
        )
        reviewers.append({
            'author': author,
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

    return {
        'status': 'success',
        'total_findings': len(records),
        'reviewer_count': len(reviewers),
        'reviewers': reviewers,
        'by_author_kind': by_author_kind,
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
    args = parser.parse_args(argv)

    try:
        from toon_parser import serialize_toon

        records = _read_pr_comment_findings(args.plan_id)
        result = aggregate(records)
        sys.stdout.write(serialize_toon(result) + '\n')
        return 0
    except Exception as e:
        import json

        error_result = {'status': 'error', 'message': str(e)}
        sys.stdout.write(json.dumps(error_result) + '\n')
        return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
