#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Unit tests for _findings_core.py - the storage engine for findings and Q-Gate findings."""


from _findings_store_fixtures import (
    add_finding,
    query_findings,
    query_findings_unified,
    resolve_finding,
    resolve_findings_by_type,
)


def test_add_finding_invalid_bot_kind(plan_context):
    """An unknown bot_kind value returns the canonical error shape."""
    result = add_finding(
        'store-prc-badbotkind',
        'pr-comment',
        'Title',
        'Detail',
        bot_kind='sonarcloud',
    )
    assert result['status'] == 'error'
    assert 'Invalid bot_kind' in result['message']


def test_add_finding_accepts_sourcery_bot_kind(plan_context):
    """``sourcery`` is a first-class bot_kind accepted by add_finding."""
    add_finding(
        'store-prc-sourcery',
        'pr-comment',
        'Sourcery comment',
        'Detail',
        author='sourcery-ai[bot]',
        bot_kind='sourcery',
    )

    result = query_findings('store-prc-sourcery', bot_kind='sourcery')
    assert result['filtered_count'] == 1
    assert result['findings'][0]['bot_kind'] == 'sourcery'


def test_query_findings_by_bot_kind(plan_context):
    """query_findings filters by exact bot_kind match."""
    add_finding('store-prc-bybotkind', 'pr-comment', 'C1', 'd', author='coderabbitai[bot]', bot_kind='coderabbit')
    add_finding('store-prc-bybotkind', 'pr-comment', 'C2', 'd', author='cuioss-review-bot[bot]', bot_kind='pr-agent')
    add_finding('store-prc-bybotkind', 'pr-comment', 'C3', 'd', author='coderabbitai[bot]', bot_kind='coderabbit')

    result = query_findings('store-prc-bybotkind', bot_kind='coderabbit')
    assert result['total_count'] == 3
    assert result['filtered_count'] == 2
    assert {f['title'] for f in result['findings']} == {'C1', 'C3'}


def test_query_findings_bot_kind_excludes_unfielded(plan_context):
    """The bot_kind filter excludes pr-comment findings that carry no bot_kind."""
    add_finding('store-prc-botkind-mix', 'pr-comment', 'Legacy', 'd', author='octocat', kind='inline')
    add_finding('store-prc-botkind-mix', 'pr-comment', 'Bot', 'd', bot_kind='pr-agent')

    result = query_findings('store-prc-botkind-mix', bot_kind='pr-agent')
    assert result['total_count'] == 2
    assert result['filtered_count'] == 1
    assert result['findings'][0]['title'] == 'Bot'


def test_query_findings_unified_carries_reviewed_commit_sha_and_bot_kind(plan_context):
    """The unified read surfaces reviewed_commit_sha/bot_kind on the merged plan slice."""
    add_finding(
        'store-prc-rcs-unified',
        'pr-comment',
        'Plan comment',
        'd',
        bot_kind='coderabbit',
        reviewed_commit_sha='deadbeef',
    )

    unified = query_findings_unified('store-prc-rcs-unified')
    assert unified['plan_count'] == 1
    record = next(f for f in unified['findings'] if f['title'] == 'Plan comment')
    assert record['reviewed_commit_sha'] == 'deadbeef'
    assert record['bot_kind'] == 'coderabbit'


def test_query_findings_unified_filters_by_bot_kind(plan_context):
    """The unified read narrows the merged result by bot_kind."""
    add_finding('store-prc-unified-bk', 'pr-comment', 'From coderabbit', 'd', bot_kind='coderabbit')
    add_finding('store-prc-unified-bk', 'pr-comment', 'From pr-agent', 'd', bot_kind='pr-agent')

    unified = query_findings_unified('store-prc-unified-bk', bot_kind='coderabbit')
    assert unified['plan_count'] == 1
    assert unified['findings'][0]['title'] == 'From coderabbit'


def test_add_finding_pr_comment_backward_compatible_without_new_fields(plan_context):
    """Existing pr-comment findings (author/kind only) remain valid and queryable.

    Backward-compatibility guard: a pr-comment finding created with the pre-existing
    author/kind surface and neither reviewed_commit_sha nor bot_kind persists and
    round-trips unchanged, and a bot_kind filter does not surface it.
    """
    add_finding(
        'store-prc-bwcompat',
        'pr-comment',
        'Old-style comment',
        'Pre-enrichment finding',
        author='octocat',
        kind='review_body',
    )

    result = query_findings('store-prc-bwcompat', finding_type='pr-comment')
    assert result['filtered_count'] == 1
    record = result['findings'][0]
    assert record['author'] == 'octocat'
    assert record['kind'] == 'review_body'
    assert 'reviewed_commit_sha' not in record
    assert 'bot_kind' not in record

    filtered = query_findings('store-prc-bwcompat', bot_kind='coderabbit')
    assert filtered['filtered_count'] == 0


# =============================================================================
# Test: resolve_finding
# =============================================================================


def test_resolve_finding_success(plan_context):
    """Test resolving a finding."""
    r = add_finding('store-resolve', 'bug', 'Bug', 'Detail')
    hash_id = r['hash_id']

    result = resolve_finding('store-resolve', hash_id, 'fixed', detail='Fixed in commit abc123')
    assert result['status'] == 'success'
    assert result['hash_id'] == hash_id
    assert result['resolution'] == 'fixed'


def test_resolve_finding_invalid_resolution(plan_context):
    """Test resolving with invalid resolution string."""
    r = add_finding('store-resolve-bad', 'bug', 'Bug', 'Detail')

    result = resolve_finding('store-resolve-bad', r['hash_id'], 'invalid-resolution')
    assert result['status'] == 'error'
    assert 'Invalid resolution' in result['message']


def test_resolve_finding_not_found(plan_context):
    """Test resolving a non-existent finding."""
    result = resolve_finding('store-resolve-nf', 'nonexistent', 'fixed')
    assert result['status'] == 'error'
    assert 'not found' in result['message']


def test_resolve_finding_rejected_is_valid(plan_context):
    """`rejected` is a valid resolution accepted by the validator.

    Added by the ext-point-verify findings pipeline: `rejected` joins the
    terminal resolution set and is accepted by `resolve_finding` without the
    `Invalid resolution` error path firing.
    """
    r = add_finding('store-resolve-rejected', 'sonar-issue', 'Refuted finding', 'Detail')

    result = resolve_finding(
        'store-resolve-rejected', r['hash_id'], 'rejected', detail='Adversarially refuted'
    )

    assert result['status'] == 'success'
    assert result['resolution'] == 'rejected'


def test_resolve_findings_by_type_accepts_rejected(plan_context):
    """Bulk resolve accepts `rejected` as a valid target resolution."""
    add_finding('store-bulk-rejected', 'lint-issue', 'Lint 1', 'Detail')
    add_finding('store-bulk-rejected', 'lint-issue', 'Lint 2', 'Detail')

    result = resolve_findings_by_type('store-bulk-rejected', ('lint-issue',), 'rejected')

    assert result['status'] == 'success'
    assert result['resolved_count'] == 2

    rejected = query_findings('store-bulk-rejected', finding_type='lint-issue', resolution='rejected')
    assert rejected['filtered_count'] == 2
    pending = query_findings('store-bulk-rejected', finding_type='lint-issue', resolution='pending')
    assert pending['filtered_count'] == 0


# =============================================================================
# Test: resolve_findings_by_type (bulk resolve)
# =============================================================================


def test_resolve_findings_by_type_bulk_count(plan_context):
    """Bulk-resolving all pending findings of a type returns the correct count."""
    add_finding('store-bulk-count', 'bug', 'Bug 1', 'Detail')
    add_finding('store-bulk-count', 'bug', 'Bug 2', 'Detail')
    add_finding('store-bulk-count', 'bug', 'Bug 3', 'Detail')

    result = resolve_findings_by_type('store-bulk-count', ('bug',), 'fixed')
    assert result['status'] == 'success'
    assert result['resolved_count'] == 3
    assert len(result['hash_ids']) == 3

    pending = query_findings('store-bulk-count', finding_type='bug', resolution='pending')
    assert pending['filtered_count'] == 0
    resolved = query_findings('store-bulk-count', finding_type='bug', resolution='fixed')
    assert resolved['filtered_count'] == 3


def test_resolve_findings_by_type_leaves_other_types(plan_context):
    """Findings not matching the type predicate are left unresolved."""
    add_finding('store-bulk-other', 'bug', 'Bug 1', 'Detail')
    add_finding('store-bulk-other', 'bug', 'Bug 2', 'Detail')
    add_finding('store-bulk-other', 'improvement', 'Improve 1', 'Detail')

    result = resolve_findings_by_type('store-bulk-other', ('bug',), 'fixed')
    assert result['status'] == 'success'
    assert result['resolved_count'] == 2

    pending_improve = query_findings(
        'store-bulk-other', finding_type='improvement', resolution='pending'
    )
    assert pending_improve['filtered_count'] == 1


def test_resolve_findings_by_type_skips_already_resolved(plan_context):
    """An already-resolved finding is not double-counted on a subsequent bulk resolve."""
    r1 = add_finding('store-bulk-dup', 'bug', 'Bug 1', 'Detail')
    add_finding('store-bulk-dup', 'bug', 'Bug 2', 'Detail')

    resolve_finding('store-bulk-dup', r1['hash_id'], 'fixed')

    result = resolve_findings_by_type('store-bulk-dup', ('bug',), 'fixed')
    assert result['status'] == 'success'
    assert result['resolved_count'] == 1
    assert r1['hash_id'] not in result['hash_ids']


def test_resolve_findings_by_type_empty_when_no_match(plan_context):
    """Bulk resolve returns a zero count when no findings match the type predicate."""
    add_finding('store-bulk-empty', 'improvement', 'Improve 1', 'Detail')

    result = resolve_findings_by_type('store-bulk-empty', ('bug',), 'fixed')
    assert result['status'] == 'success'
    assert result['resolved_count'] == 0
    assert result['hash_ids'] == []


def test_resolve_findings_by_type_multiple_types(plan_context):
    """Bulk resolve spans multiple finding types in a single call."""
    add_finding('store-bulk-multi', 'bug', 'Bug 1', 'Detail')
    add_finding('store-bulk-multi', 'improvement', 'Improve 1', 'Detail')
    add_finding('store-bulk-multi', 'tip', 'Tip 1', 'Detail')

    result = resolve_findings_by_type('store-bulk-multi', ('bug', 'improvement'), 'fixed')
    assert result['status'] == 'success'
    assert result['resolved_count'] == 2

    pending_tip = query_findings('store-bulk-multi', finding_type='tip', resolution='pending')
    assert pending_tip['filtered_count'] == 1
