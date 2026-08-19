#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Unit tests for _findings_core.py - the storage engine for findings and Q-Gate findings."""


from _findings_store_fixtures import (
    add_finding,
    add_qgate_finding,
    query_findings,
    query_findings_unified,
    resolve_finding,
)

# =============================================================================
# Test: add_finding
# =============================================================================


def test_add_finding_basic(plan_context):
    """Test adding a basic finding."""
    result = add_finding('store-add-basic', 'bug', 'Test bug', 'Detail here')
    assert result['status'] == 'success'
    assert 'hash_id' in result
    assert result['type'] == 'bug'


def test_add_finding_with_optional_fields(plan_context):
    """Test adding a finding with all optional fields."""
    result = add_finding(
        'store-add-opts',
        'sonar-issue',
        'S1192 duplicated',
        'String repeated 5 times',
        file_path='src/main/java/Api.java',
        line=42,
        component='api-module',
        module='core',
        rule='java:S1192',
        severity='warning',
    )
    assert result['status'] == 'success'
    assert 'hash_id' in result


def test_add_finding_invalid_type(plan_context):
    """Test adding a finding with invalid type returns error."""
    result = add_finding('store-add-badtype', 'nonexistent-type', 'Title', 'Detail')
    assert result['status'] == 'error'
    assert 'Invalid finding type' in result['message']


def test_add_finding_invalid_severity(plan_context):
    """Test adding a finding with invalid severity returns error."""
    result = add_finding('store-add-badsev', 'bug', 'Title', 'Detail', severity='critical')
    assert result['status'] == 'error'
    assert 'Invalid severity' in result['message']


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


def test_add_finding_persists_author_and_kind(plan_context):
    """A pr-comment finding stores author and kind as first-class fields."""
    add_finding(
        'store-prc-persist',
        'pr-comment',
        'Nit: rename variable',
        'Consider a clearer name',
        author='octocat',
        kind='inline',
    )

    result = query_findings('store-prc-persist', finding_type='pr-comment')
    assert result['filtered_count'] == 1
    record = result['findings'][0]
    assert record['author'] == 'octocat'
    assert record['kind'] == 'inline'


def test_add_finding_omits_author_and_kind_when_absent(plan_context):
    """Findings added without author/kind do not carry those keys."""
    add_finding('store-prc-absent', 'bug', 'Plain bug', 'No reviewer metadata')

    result = query_findings('store-prc-absent', finding_type='bug')
    assert result['filtered_count'] == 1
    record = result['findings'][0]
    assert 'author' not in record
    assert 'kind' not in record


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


def test_add_finding_persists_reviewed_commit_sha_and_bot_kind(plan_context):
    """A pr-comment finding round-trips reviewed_commit_sha and bot_kind."""
    add_finding(
        'store-prc-rcs-persist',
        'pr-comment',
        'CodeRabbit nit',
        'Consider extracting a helper',
        author='coderabbitai[bot]',
        kind='inline',
        reviewed_commit_sha='abc1234def5678',
        bot_kind='coderabbit',
    )

    result = query_findings('store-prc-rcs-persist', finding_type='pr-comment')
    assert result['filtered_count'] == 1
    record = result['findings'][0]
    assert record['reviewed_commit_sha'] == 'abc1234def5678'
    assert record['bot_kind'] == 'coderabbit'


def test_add_finding_omits_reviewed_commit_sha_and_bot_kind_when_absent(plan_context):
    """Findings added without the new fields do not carry those keys."""
    add_finding('store-prc-rcs-absent', 'bug', 'Plain bug', 'No reviewer metadata')

    result = query_findings('store-prc-rcs-absent', finding_type='bug')
    assert result['filtered_count'] == 1
    record = result['findings'][0]
    assert 'reviewed_commit_sha' not in record
    assert 'bot_kind' not in record
