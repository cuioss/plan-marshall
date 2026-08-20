#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Unit tests for _findings_core.py - the storage engine for findings and Q-Gate findings.

Its sections, in order:

* query_findings
* pr-comment author / kind first-class fields
* pr-comment reviewed_commit_sha / bot_kind first-class fields
* Q-Gate findings
* resolve_finding
* responded-marker lifecycle (the RESPOND idempotency key)
"""


from _findings_store_fixtures import (
    add_finding,
    add_qgate_finding,
    get_finding,
    mark_finding_responded,
    query_findings,
    query_findings_unified,
    query_qgate_findings,
    resolve_finding,
)

# =============================================================================
# Test: query_findings
# =============================================================================


def test_query_findings_empty(plan_context):
    """Test querying when no findings exist."""
    result = query_findings('store-query-empty')
    assert result['status'] == 'success'
    assert result['total_count'] == 0
    assert result['filtered_count'] == 0
    assert result['findings'] == []


def test_query_findings_all(plan_context):
    """Test querying returns all findings."""
    add_finding('store-query-all', 'bug', 'Bug 1', 'Detail 1')
    add_finding('store-query-all', 'improvement', 'Improve 1', 'Detail 2')

    result = query_findings('store-query-all')
    assert result['status'] == 'success'
    assert result['total_count'] == 2
    assert result['filtered_count'] == 2


def test_query_findings_by_type(plan_context):
    """Test querying with type filter."""
    add_finding('store-query-type', 'bug', 'Bug 1', 'Detail')
    add_finding('store-query-type', 'improvement', 'Improve 1', 'Detail')
    add_finding('store-query-type', 'bug', 'Bug 2', 'Detail')

    result = query_findings('store-query-type', finding_type='bug')
    assert result['status'] == 'success'
    assert result['total_count'] == 3
    assert result['filtered_count'] == 2


def test_query_findings_by_resolution(plan_context):
    """Test querying with resolution filter."""
    r1 = add_finding('store-query-res', 'bug', 'Bug 1', 'Detail')
    add_finding('store-query-res', 'bug', 'Bug 2', 'Detail')

    resolve_finding('store-query-res', r1['hash_id'], 'fixed')

    result = query_findings('store-query-res', resolution='pending')
    assert result['filtered_count'] == 1

    result = query_findings('store-query-res', resolution='fixed')
    assert result['filtered_count'] == 1


def test_query_findings_by_file_pattern(plan_context):
    """Test querying with file pattern filter."""
    add_finding('store-query-file', 'bug', 'Bug 1', 'Detail', file_path='src/main/java/Foo.java')
    add_finding('store-query-file', 'bug', 'Bug 2', 'Detail', file_path='src/test/java/FooTest.java')

    result = query_findings('store-query-file', file_pattern='src/main/*')
    assert result['filtered_count'] == 1


# =============================================================================
# Test: pr-comment author / kind first-class fields
# =============================================================================

def test_query_findings_by_author(plan_context):
    """query_findings filters by exact author match."""
    add_finding('store-prc-byauthor', 'pr-comment', 'C1', 'd', author='alice', kind='inline')
    add_finding('store-prc-byauthor', 'pr-comment', 'C2', 'd', author='bob', kind='inline')
    add_finding('store-prc-byauthor', 'pr-comment', 'C3', 'd', author='alice', kind='review_body')

    result = query_findings('store-prc-byauthor', author='alice')
    assert result['total_count'] == 3
    assert result['filtered_count'] == 2
    assert {f['title'] for f in result['findings']} == {'C1', 'C3'}


def test_query_findings_by_kind(plan_context):
    """query_findings filters by exact kind match."""
    add_finding('store-prc-bykind', 'pr-comment', 'C1', 'd', author='alice', kind='inline')
    add_finding('store-prc-bykind', 'pr-comment', 'C2', 'd', author='bob', kind='review_body')
    add_finding('store-prc-bykind', 'pr-comment', 'C3', 'd', author='carol', kind='inline')

    result = query_findings('store-prc-bykind', kind='inline')
    assert result['filtered_count'] == 2
    assert {f['title'] for f in result['findings']} == {'C1', 'C3'}


def test_query_findings_by_author_and_kind(plan_context):
    """query_findings narrows on author and kind together."""
    add_finding('store-prc-both', 'pr-comment', 'C1', 'd', author='alice', kind='inline')
    add_finding('store-prc-both', 'pr-comment', 'C2', 'd', author='alice', kind='review_body')
    add_finding('store-prc-both', 'pr-comment', 'C3', 'd', author='bob', kind='inline')

    result = query_findings('store-prc-both', author='alice', kind='inline')
    assert result['filtered_count'] == 1
    assert result['findings'][0]['title'] == 'C1'


def test_query_findings_unified_carries_author_and_kind(plan_context):
    """The unified read surfaces author/kind on the merged plan slice."""
    add_finding('store-prc-unified', 'pr-comment', 'Plan comment', 'd', author='dave', kind='issue_comment')

    unified = query_findings_unified('store-prc-unified')
    assert unified['plan_count'] == 1
    record = next(f for f in unified['findings'] if f['title'] == 'Plan comment')
    assert record['author'] == 'dave'
    assert record['kind'] == 'issue_comment'


def test_query_findings_unified_filters_by_author(plan_context):
    """The unified read narrows both plan and Q-Gate slices by author."""
    add_finding('store-prc-unified-auth', 'pr-comment', 'From alice', 'd', author='alice', kind='inline')
    add_finding('store-prc-unified-auth', 'pr-comment', 'From bob', 'd', author='bob', kind='inline')

    unified = query_findings_unified('store-prc-unified-auth', author='alice')
    assert unified['plan_count'] == 1
    assert unified['findings'][0]['title'] == 'From alice'


def test_query_findings_unified_filters_qgate_by_author(plan_context):
    """The unified read excludes Q-Gate findings that do not match the author filter."""
    # Q-Gate findings do not carry author; author filter must exclude them from the result.
    add_qgate_finding(
        'store-qgate-auth-filter', '2-refine', 'qgate', 'pr-comment',
        'Q-Gate finding without author', 'detail',
    )
    add_finding('store-qgate-auth-filter', 'pr-comment', 'Plan finding alice', 'd', author='alice')

    unified = query_findings_unified('store-qgate-auth-filter', author='alice')
    assert unified['plan_count'] == 1
    assert unified['qgate_count'] == 0
    titles = [f['title'] for f in unified['findings']]
    assert 'Plan finding alice' in titles
    assert 'Q-Gate finding without author' not in titles


# =============================================================================
# Test: pr-comment reviewed_commit_sha / bot_kind first-class fields
# =============================================================================

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


# =============================================================================
# Test: Q-Gate findings
# =============================================================================

def test_query_qgate_findings(plan_context):
    """Test querying Q-Gate findings."""
    add_qgate_finding(
        'store-qgate-query',
        '5-execute',
        'qgate',
        'build-error',
        'Error 1',
        'Detail',
    )
    add_qgate_finding(
        'store-qgate-query',
        '5-execute',
        'user_review',
        'pr-comment',
        'Comment 1',
        'Detail',
    )

    result = query_qgate_findings('store-qgate-query', '5-execute')
    assert result['status'] == 'success'
    assert result['total_count'] == 2

    result = query_qgate_findings('store-qgate-query', '5-execute', source='qgate')
    assert result['filtered_count'] == 1


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


# =============================================================================
# Test: responded-marker lifecycle (the RESPOND idempotency key)
#
# The provider RESPOND verbs stamp a `responded` marker after transmitting a
# reply, and skip a finding that already carries it. Re-resolving a finding to a
# DIFFERENT disposition must clear the marker so the corrected decision goes out
# again; an unchanged re-resolve must preserve it so the already-sent reply is
# not re-sent. That clearing is what makes the idempotency a per-(finding,
# disposition) key rather than a permanent suppression, and it must hold at BOTH
# resolve entry points.
# =============================================================================


def test_resolve_finding_clears_responded_marker_on_changed_disposition(plan_context):
    """A resolution or reply-body change clears a stale transmission marker."""
    r = add_finding('store-responded-change', 'pr-comment', 'C', 'detail')
    hash_id = r['hash_id']
    resolve_finding('store-responded-change', hash_id, 'accepted', detail='Accepted: original.')
    mark_finding_responded('store-responded-change', hash_id)
    assert get_finding('store-responded-change', hash_id)['responded'] is True

    # A changed resolution AND body — the marker must be cleared.
    resolve_finding('store-responded-change', hash_id, 'rejected', detail='Rejected: reconsidered.')
    reread = get_finding('store-responded-change', hash_id)
    assert reread['responded'] is False
    assert reread['responded_at'] is None


def test_resolve_finding_keeps_responded_marker_on_unchanged_reresolve(plan_context):
    """An idempotent re-resolve (same disposition) must NOT clear the marker.

    Otherwise the already-sent reply would be needlessly re-transmitted — the very
    defect the marker exists to prevent.
    """
    r = add_finding('store-responded-noop', 'pr-comment', 'C', 'detail')
    hash_id = r['hash_id']
    resolve_finding('store-responded-noop', hash_id, 'accepted', detail='Accepted: same.')
    mark_finding_responded('store-responded-noop', hash_id)

    # Same resolution, same detail — nothing changed, the marker holds.
    resolve_finding('store-responded-noop', hash_id, 'accepted', detail='Accepted: same.')
    assert get_finding('store-responded-noop', hash_id)['responded'] is True

    # Same resolution, detail omitted (None) — also a no-op for the marker.
    resolve_finding('store-responded-noop', hash_id, 'accepted')
    assert get_finding('store-responded-noop', hash_id)['responded'] is True
