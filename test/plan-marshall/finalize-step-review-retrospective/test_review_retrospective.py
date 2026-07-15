#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Unit tests for the project-local ``review_retrospective.py`` aggregator.

Drives the pure ``aggregate(records)`` function directly. The aggregator ships
as a project-local script under ``.claude/skills/finalize-step-review-retrospective/
scripts/`` (NOT in a marketplace bundle), so ``conftest.get_script_path`` — which
only resolves ``marketplace/bundles/...`` — cannot reach it. Instead the scripts
dir is resolved relative to ``conftest.PROJECT_ROOT`` and inserted on ``sys.path``
(the project-local mirror of the canonical scaffolding prologue in
``plugin-script-architecture/standards/test-scaffolding.md``).

``aggregate`` is pure (operates on record dicts passed in), so it is importable
and exercisable without any plan on disk and without the executor PYTHONPATH that
supplies ``_findings_core``/``toon_parser`` (those are imported lazily inside the
module's ``main`` read path, never at import time).

Coverage:
- grouping by ``(author, kind)`` (``by_author_kind`` + per-reviewer ``raw_total``);
- ``raw_total`` vs ``actionable_count`` vs ``meta_count`` distinction;
- per-reviewer resolution buckets and ``positives``/``false_positives``/
  ``pct_resolved_as_fixed`` math;
- ``unattributed`` bucket for records lacking ``author``;
- ``unknown``-kind handling (raw_total only, never actionable);
- empty-input;
- the PR #726-shaped CodeRabbit case (5 inline + 1 status-summary review_body
  + 1 walkthrough issue_comment => raw_total=7, actionable=5, meta=2).
"""

from __future__ import annotations

import sys

import pytest

from conftest import PROJECT_ROOT

_SCRIPTS_DIR = (
    PROJECT_ROOT
    / '.claude'
    / 'skills'
    / 'finalize-step-review-retrospective'
    / 'scripts'
)
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import review_retrospective as rr  # type: ignore[import-untyped]  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _reviewer(result: dict, author: str) -> dict:
    """Return the single ``reviewers[]`` row for ``author`` (asserts uniqueness)."""
    rows = [r for r in result['reviewers'] if r['author'] == author]
    assert len(rows) == 1, f'expected exactly one reviewer row for {author!r}, got {rows}'
    row: dict = rows[0]
    return row


def _kind_count(result: dict, author: str, kind: str) -> int:
    """Return the ``by_author_kind`` count for ``(author, kind)`` (0 when absent)."""
    for row in result['by_author_kind']:
        if row['author'] == author and row['kind'] == kind:
            count: int = row['count']
            return count
    return 0


# ---------------------------------------------------------------------------
# Empty input
# ---------------------------------------------------------------------------


def test_empty_input_produces_empty_report():
    result = rr.aggregate([])

    assert result['status'] == 'success'
    assert result['total_findings'] == 0
    assert result['reviewer_count'] == 0
    assert result['reviewers'] == []
    assert result['by_author_kind'] == []
    # Mapping legends are static and present even for empty input.
    assert 'kind_actionability' in result
    assert 'resolution_quality' in result


# ---------------------------------------------------------------------------
# Grouping by (author, kind)
# ---------------------------------------------------------------------------


def test_grouping_by_author_and_kind():
    records = [
        {'author': 'alice', 'kind': 'inline'},
        {'author': 'alice', 'kind': 'inline'},
        {'author': 'alice', 'kind': 'review_body'},
        {'author': 'bob', 'kind': 'inline'},
    ]

    result = rr.aggregate(records)

    assert result['total_findings'] == 4
    assert result['reviewer_count'] == 2
    assert _kind_count(result, 'alice', 'inline') == 2
    assert _kind_count(result, 'alice', 'review_body') == 1
    assert _kind_count(result, 'bob', 'inline') == 1
    assert _reviewer(result, 'alice')['raw_total'] == 3
    assert _reviewer(result, 'bob')['raw_total'] == 1


def test_reviewers_sorted_by_author():
    records = [
        {'author': 'zoe', 'kind': 'inline'},
        {'author': 'alice', 'kind': 'inline'},
        {'author': 'mike', 'kind': 'inline'},
    ]

    result = rr.aggregate(records)

    authors = [r['author'] for r in result['reviewers']]
    assert authors == ['alice', 'mike', 'zoe']


def test_by_author_kind_is_sorted():
    records = [
        {'author': 'bob', 'kind': 'review_body'},
        {'author': 'alice', 'kind': 'inline'},
        {'author': 'alice', 'kind': 'issue_comment'},
    ]

    result = rr.aggregate(records)

    pairs = [(row['author'], row['kind']) for row in result['by_author_kind']]
    assert pairs == sorted(pairs)


# ---------------------------------------------------------------------------
# raw_total vs actionable_count vs meta_count
# ---------------------------------------------------------------------------


def test_inline_is_actionable():
    result = rr.aggregate([{'author': 'alice', 'kind': 'inline'}])

    row = _reviewer(result, 'alice')
    assert row['raw_total'] == 1
    assert row['actionable_count'] == 1
    assert row['meta_count'] == 0


def test_substantive_review_body_is_actionable():
    # Gemini's typical shape: a single substantive review_body, no status-summary
    # signature, so it counts as actionable.
    result = rr.aggregate([
        {
            'author': 'gemini-code-assist',
            'kind': 'review_body',
            'title': 'Consider extracting the validation helper',
            'detail': 'The block at L40 duplicates L88.',
        }
    ])

    row = _reviewer(result, 'gemini-code-assist')
    assert row['raw_total'] == 1
    assert row['actionable_count'] == 1
    assert row['meta_count'] == 0


def test_issue_comment_is_meta():
    result = rr.aggregate([{'author': 'coderabbitai', 'kind': 'issue_comment'}])

    row = _reviewer(result, 'coderabbitai')
    assert row['raw_total'] == 1
    assert row['actionable_count'] == 0
    assert row['meta_count'] == 1


def test_coderabbit_status_summary_review_body_is_meta():
    # CodeRabbit status-summary review_body: author=coderabbitai + the
    # "Actionable comments posted" signature => META, never actionable.
    result = rr.aggregate([
        {
            'author': 'coderabbitai',
            'kind': 'review_body',
            'title': 'Actionable comments posted: 5',
            'detail': '',
        }
    ])

    row = _reviewer(result, 'coderabbitai')
    assert row['raw_total'] == 1
    assert row['actionable_count'] == 0
    assert row['meta_count'] == 1


def test_status_summary_signature_only_meta_for_coderabbit_author():
    # The status-summary signature is gated on the CodeRabbit author — the same
    # title from another reviewer is a genuine substantive review_body.
    result = rr.aggregate([
        {
            'author': 'gemini-code-assist',
            'kind': 'review_body',
            'title': 'Actionable comments posted: 5',
            'detail': '',
        }
    ])

    row = _reviewer(result, 'gemini-code-assist')
    assert row['actionable_count'] == 1
    assert row['meta_count'] == 0


def test_status_summary_signature_matched_in_detail_case_insensitively():
    # Signature lives in detail, mixed case — still matched (haystack lowercased).
    result = rr.aggregate([
        {
            'author': 'coderabbitai',
            'kind': 'review_body',
            'title': 'Review summary',
            'detail': 'ACTIONABLE Comments Posted: 3',
        }
    ])

    row = _reviewer(result, 'coderabbitai')
    assert row['actionable_count'] == 0
    assert row['meta_count'] == 1


# ---------------------------------------------------------------------------
# unknown-kind handling
# ---------------------------------------------------------------------------


def test_missing_kind_bucketed_as_unknown_and_meta():
    # A record lacking kind is bucketed under 'unknown', counted in raw_total
    # only — never in actionable_count.
    result = rr.aggregate([{'author': 'alice'}])

    row = _reviewer(result, 'alice')
    assert row['raw_total'] == 1
    assert row['actionable_count'] == 0
    assert row['meta_count'] == 1
    assert _kind_count(result, 'alice', 'unknown') == 1


def test_explicit_unknown_kind_is_meta():
    result = rr.aggregate([{'author': 'alice', 'kind': 'unknown'}])

    row = _reviewer(result, 'alice')
    assert row['actionable_count'] == 0
    assert row['meta_count'] == 1
    assert _kind_count(result, 'alice', 'unknown') == 1


# ---------------------------------------------------------------------------
# unattributed bucket
# ---------------------------------------------------------------------------


def test_missing_author_bucketed_as_unattributed():
    result = rr.aggregate([
        {'kind': 'inline'},
        {'author': '', 'kind': 'review_body', 'title': 'x'},
    ])

    row = _reviewer(result, 'unattributed')
    assert row['raw_total'] == 2
    # inline => actionable; substantive review_body => actionable.
    assert row['actionable_count'] == 2
    assert _kind_count(result, 'unattributed', 'inline') == 1
    assert _kind_count(result, 'unattributed', 'review_body') == 1


def test_unattributed_status_summary_not_special_cased():
    # The status-summary META carve-out is gated on author=coderabbitai, so an
    # unattributed record with that signature is still a substantive (actionable)
    # review_body.
    result = rr.aggregate([
        {'kind': 'review_body', 'title': 'Actionable comments posted: 9'}
    ])

    row = _reviewer(result, 'unattributed')
    assert row['actionable_count'] == 1
    assert row['meta_count'] == 0


# ---------------------------------------------------------------------------
# Resolution buckets + positives / false_positives / pct math
# ---------------------------------------------------------------------------


def test_resolution_buckets_and_quality_math():
    records = [
        {'author': 'alice', 'kind': 'inline', 'resolution': 'fixed'},
        {'author': 'alice', 'kind': 'inline', 'resolution': 'fixed'},
        {'author': 'alice', 'kind': 'inline', 'resolution': 'accepted'},
        {'author': 'alice', 'kind': 'inline', 'resolution': 'taken_into_account'},
        {'author': 'alice', 'kind': 'inline', 'resolution': 'suppressed'},
        {'author': 'alice', 'kind': 'inline', 'resolution': 'pending'},
    ]

    result = rr.aggregate(records)
    row = _reviewer(result, 'alice')

    assert row['raw_total'] == 6
    assert row['fixed'] == 2
    assert row['accepted'] == 1
    assert row['taken_into_account'] == 1
    assert row['suppressed'] == 1
    assert row['pending'] == 1
    # positives = fixed; false_positives = accepted + taken_into_account.
    assert row['positives_count'] == 2
    assert row['false_positives_count'] == 2
    # pct_resolved_as_fixed = 100 * fixed / raw_total = 100 * 2 / 6 = 33.3.
    assert row['pct_resolved_as_fixed'] == pytest.approx(33.3)


def test_missing_resolution_defaults_to_pending():
    result = rr.aggregate([{'author': 'alice', 'kind': 'inline'}])

    row = _reviewer(result, 'alice')
    assert row['pending'] == 1
    assert row['fixed'] == 0
    assert row['positives_count'] == 0
    assert row['false_positives_count'] == 0
    assert row['pct_resolved_as_fixed'] == 0.0


def test_unrecognized_resolution_not_bucketed_but_counts_in_raw_total():
    # A resolution outside the canonical five is excluded from every resolution
    # bucket, yet still increments raw_total and its (author, kind) group.
    result = rr.aggregate([
        {'author': 'alice', 'kind': 'inline', 'resolution': 'wontfix'}
    ])

    row = _reviewer(result, 'alice')
    assert row['raw_total'] == 1
    assert row['fixed'] == 0
    assert row['accepted'] == 0
    assert row['taken_into_account'] == 0
    assert row['suppressed'] == 0
    assert row['pending'] == 0
    assert row['positives_count'] == 0
    assert row['false_positives_count'] == 0
    # Not a positive nor a false positive, so 0% resolved-as-fixed.
    assert row['pct_resolved_as_fixed'] == 0.0


def test_pct_resolved_as_fixed_all_fixed():
    result = rr.aggregate([
        {'author': 'alice', 'kind': 'inline', 'resolution': 'fixed'},
        {'author': 'alice', 'kind': 'inline', 'resolution': 'fixed'},
    ])

    row = _reviewer(result, 'alice')
    assert row['pct_resolved_as_fixed'] == 100.0


# ---------------------------------------------------------------------------
# PR #726-shaped CodeRabbit case
# ---------------------------------------------------------------------------


def test_pr_726_coderabbit_shape():
    # CodeRabbit on PR #726: 5 inline actionable comments + 1 status-summary
    # review_body (META) + 1 walkthrough issue_comment (META).
    # => raw_total=7, actionable=5, meta=2.
    records = [
        {'author': 'coderabbitai', 'kind': 'inline', 'resolution': 'fixed'},
        {'author': 'coderabbitai', 'kind': 'inline', 'resolution': 'fixed'},
        {'author': 'coderabbitai', 'kind': 'inline', 'resolution': 'accepted'},
        {'author': 'coderabbitai', 'kind': 'inline', 'resolution': 'suppressed'},
        {'author': 'coderabbitai', 'kind': 'inline', 'resolution': 'pending'},
        {
            'author': 'coderabbitai',
            'kind': 'review_body',
            'title': 'Actionable comments posted: 5',
            'detail': '',
        },
        {
            'author': 'coderabbitai',
            'kind': 'issue_comment',
            'title': 'Walkthrough',
            'detail': 'A poem about the changes.',
        },
    ]

    result = rr.aggregate(records)

    assert result['total_findings'] == 7
    assert result['reviewer_count'] == 1

    row = _reviewer(result, 'coderabbitai')
    assert row['raw_total'] == 7
    assert row['actionable_count'] == 5
    assert row['meta_count'] == 2

    # Resolution buckets over the 7 records (only the 5 inline carry the
    # canonical resolutions; the two META records default to pending).
    assert row['fixed'] == 2
    assert row['accepted'] == 1
    assert row['suppressed'] == 1
    # pending: 1 inline pending + the 2 META records (default pending) = 3.
    assert row['pending'] == 3
    assert row['positives_count'] == 2
    assert row['false_positives_count'] == 1

    # by_author_kind breakdown reflects the structural asymmetry.
    assert _kind_count(result, 'coderabbitai', 'inline') == 5
    assert _kind_count(result, 'coderabbitai', 'review_body') == 1
    assert _kind_count(result, 'coderabbitai', 'issue_comment') == 1


def test_multi_reviewer_coderabbit_vs_gemini():
    # Comparative shape: CodeRabbit (inline-heavy + META layers) vs Gemini
    # (single substantive review_body). Confirms per-reviewer isolation.
    records = [
        {'author': 'coderabbitai', 'kind': 'inline', 'resolution': 'fixed'},
        {'author': 'coderabbitai', 'kind': 'inline', 'resolution': 'accepted'},
        {
            'author': 'coderabbitai',
            'kind': 'review_body',
            'title': 'Actionable comments posted: 2',
        },
        {
            'author': 'gemini-code-assist',
            'kind': 'review_body',
            'title': 'Overall the change is sound; one concern at L12.',
            'resolution': 'fixed',
        },
    ]

    result = rr.aggregate(records)

    assert result['reviewer_count'] == 2

    cr = _reviewer(result, 'coderabbitai')
    assert cr['raw_total'] == 3
    assert cr['actionable_count'] == 2
    assert cr['meta_count'] == 1
    assert cr['positives_count'] == 1
    assert cr['false_positives_count'] == 1

    gem = _reviewer(result, 'gemini-code-assist')
    assert gem['raw_total'] == 1
    assert gem['actionable_count'] == 1
    assert gem['meta_count'] == 0
    assert gem['positives_count'] == 1
    assert gem['pct_resolved_as_fixed'] == 100.0
