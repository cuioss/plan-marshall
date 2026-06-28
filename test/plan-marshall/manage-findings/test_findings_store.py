#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Unit tests for _findings_core.py - the storage engine for findings and Q-Gate findings."""

from conftest import get_scripts_dir, load_script_module

# Retained for the source-introspection test that reads _findings_core.py text.
_SCRIPTS_DIR = get_scripts_dir('plan-marshall', 'manage-findings')


_findings_core = load_script_module('plan-marshall', 'manage-findings', '_findings_core.py', '_findings_core')

add_finding = _findings_core.add_finding
add_qgate_finding = _findings_core.add_qgate_finding
clear_qgate_findings = _findings_core.clear_qgate_findings
promote_finding = _findings_core.promote_finding
query_findings = _findings_core.query_findings
query_findings_unified = _findings_core.query_findings_unified
query_qgate_findings = _findings_core.query_qgate_findings
resolve_finding = _findings_core.resolve_finding
resolve_findings_by_type = _findings_core.resolve_findings_by_type
resolve_qgate_finding = _findings_core.resolve_qgate_finding

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


def test_query_findings_by_bot_kind(plan_context):
    """query_findings filters by exact bot_kind match."""
    add_finding('store-prc-bybotkind', 'pr-comment', 'C1', 'd', author='coderabbitai[bot]', bot_kind='coderabbit')
    add_finding('store-prc-bybotkind', 'pr-comment', 'C2', 'd', author='gemini-code-assist[bot]', bot_kind='gemini')
    add_finding('store-prc-bybotkind', 'pr-comment', 'C3', 'd', author='coderabbitai[bot]', bot_kind='coderabbit')

    result = query_findings('store-prc-bybotkind', bot_kind='coderabbit')
    assert result['total_count'] == 3
    assert result['filtered_count'] == 2
    assert {f['title'] for f in result['findings']} == {'C1', 'C3'}


def test_query_findings_bot_kind_excludes_unfielded(plan_context):
    """The bot_kind filter excludes pr-comment findings that carry no bot_kind."""
    add_finding('store-prc-botkind-mix', 'pr-comment', 'Legacy', 'd', author='octocat', kind='inline')
    add_finding('store-prc-botkind-mix', 'pr-comment', 'Bot', 'd', bot_kind='gemini')

    result = query_findings('store-prc-botkind-mix', bot_kind='gemini')
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
    add_finding('store-prc-unified-bk', 'pr-comment', 'From gemini', 'd', bot_kind='gemini')

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


def test_resolve_findings_by_type_invalid_resolution(plan_context):
    """An invalid target resolution returns the canonical error shape without mutating state."""
    add_finding('store-bulk-badres', 'bug', 'Bug 1', 'Detail')

    result = resolve_findings_by_type('store-bulk-badres', ('bug',), 'not-a-resolution')
    assert result['status'] == 'error'
    assert 'Invalid resolution' in result['message']

    pending = query_findings('store-bulk-badres', finding_type='bug', resolution='pending')
    assert pending['filtered_count'] == 1, 'invalid resolution must leave the finding unmutated'


def test_resolve_findings_by_type_custom_from_resolution(plan_context):
    """Bulk resolve can re-resolve findings matching a non-default from_resolution."""
    r1 = add_finding('store-bulk-from', 'bug', 'Bug 1', 'Detail')
    add_finding('store-bulk-from', 'bug', 'Bug 2', 'Detail')

    resolve_finding('store-bulk-from', r1['hash_id'], 'accepted')

    result = resolve_findings_by_type(
        'store-bulk-from', ('bug',), 'fixed', from_resolution='accepted'
    )
    assert result['status'] == 'success'
    assert result['resolved_count'] == 1
    assert result['hash_ids'] == [r1['hash_id']]


# =============================================================================
# Test: promote_finding
# =============================================================================


def test_promote_finding_success(plan_context):
    """Test promoting a finding."""
    r = add_finding('store-promote', 'bug', 'Bug', 'Detail')
    hash_id = r['hash_id']

    result = promote_finding('store-promote', hash_id, 'manage-lessons')
    assert result['status'] == 'success'
    assert result['promoted_to'] == 'manage-lessons'

    query = query_findings('store-promote', promoted=True)
    assert query['filtered_count'] == 1


# =============================================================================
# Test: Q-Gate findings
# =============================================================================


def test_add_qgate_finding_basic(plan_context):
    """Test adding a Q-Gate finding."""
    result = add_qgate_finding(
        'store-qgate-add',
        '5-execute',
        'qgate',
        'build-error',
        'Build failure',
        'Compilation failed',
    )
    assert result['status'] == 'success'
    assert 'hash_id' in result
    assert result['phase'] == '5-execute'


def test_add_qgate_finding_invalid_phase(plan_context):
    """Test adding Q-Gate finding with invalid phase."""
    result = add_qgate_finding(
        'store-qgate-badphase',
        '1-init',
        'qgate',
        'build-error',
        'Title',
        'Detail',
    )
    assert result['status'] == 'error'
    assert 'Invalid Q-Gate phase' in result['message']


def test_add_qgate_finding_invalid_source(plan_context):
    """Test adding Q-Gate finding with invalid source."""
    result = add_qgate_finding(
        'store-qgate-badsrc',
        '5-execute',
        'invalid-source',
        'build-error',
        'Title',
        'Detail',
    )
    assert result['status'] == 'error'
    assert 'Invalid Q-Gate source' in result['message']


def test_qgate_dedup_pending(plan_context):
    """Test Q-Gate deduplication for pending findings with same title."""
    r1 = add_qgate_finding(
        'store-qgate-dedup',
        '5-execute',
        'qgate',
        'build-error',
        'Same title',
        'Detail 1',
    )
    assert r1['status'] == 'success'

    r2 = add_qgate_finding(
        'store-qgate-dedup',
        '5-execute',
        'qgate',
        'build-error',
        'Same title',
        'Detail 2',
    )
    assert r2['status'] == 'deduplicated'
    assert r2['hash_id'] == r1['hash_id']


def test_qgate_reopen_resolved(plan_context):
    """Test Q-Gate reopens a resolved finding if re-detected."""
    r1 = add_qgate_finding(
        'store-qgate-reopen',
        '5-execute',
        'qgate',
        'build-error',
        'Flaky test',
        'Detail',
    )
    resolve_qgate_finding('store-qgate-reopen', '5-execute', r1['hash_id'], 'fixed')

    r2 = add_qgate_finding(
        'store-qgate-reopen',
        '5-execute',
        'qgate',
        'build-error',
        'Flaky test',
        'New detail',
    )
    assert r2['status'] == 'reopened'
    assert r2['hash_id'] == r1['hash_id']


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


def test_resolve_qgate_finding(plan_context):
    """Test resolving a Q-Gate finding."""
    r = add_qgate_finding(
        'store-qgate-resolve',
        '5-execute',
        'qgate',
        'test-failure',
        'Test failure',
        'Detail',
    )

    result = resolve_qgate_finding(
        'store-qgate-resolve',
        '5-execute',
        r['hash_id'],
        'fixed',
        detail='Fixed it',
    )
    assert result['status'] == 'success'
    assert result['resolution'] == 'fixed'


def test_resolve_qgate_finding_rejected_is_valid(plan_context):
    """`rejected` is accepted as a valid Q-Gate resolution by the validator."""
    r = add_qgate_finding(
        'store-qgate-resolve-rejected',
        '5-execute',
        'qgate',
        'test-failure',
        'Refuted Q-Gate finding',
        'Detail',
    )

    result = resolve_qgate_finding(
        'store-qgate-resolve-rejected',
        '5-execute',
        r['hash_id'],
        'rejected',
        detail='Adversarially refuted at the verify stage',
    )
    assert result['status'] == 'success'
    assert result['resolution'] == 'rejected'


def test_rejected_qgate_finding_is_non_pending_in_unified_read(plan_context):
    """A `rejected` Q-Gate finding is non-blocking: excluded from the unified read.

    The findings-gate invariant in `query_findings_unified` merges ONLY pending
    Q-Gate records. A finding resolved to `rejected` is therefore treated as
    non-pending exactly like `fixed` / `accepted` — it never surfaces through the
    unified gate read and so does not block the gate.
    """
    pid = 'store-qgate-rejected-nonpending'
    pending = add_qgate_finding(
        pid, '5-execute', 'qgate', 'test-failure', 'Stays pending', 'Detail'
    )
    refuted = add_qgate_finding(
        pid, '5-execute', 'qgate', 'test-failure', 'Gets rejected', 'Detail'
    )
    resolve_qgate_finding(pid, '5-execute', refuted['hash_id'], 'rejected')

    unified = query_findings_unified(pid)

    assert unified['qgate_count'] == 1
    titles = {f['title'] for f in unified['findings']}
    assert titles == {'Stays pending'}
    assert pending['hash_id'] in {f['hash_id'] for f in unified['findings']}


def test_clear_qgate_findings(plan_context):
    """Test clearing all Q-Gate findings for a phase."""
    add_qgate_finding(
        'store-qgate-clear',
        '5-execute',
        'qgate',
        'build-error',
        'Error 1',
        'Detail',
    )
    add_qgate_finding(
        'store-qgate-clear',
        '5-execute',
        'qgate',
        'test-failure',
        'Error 2',
        'Detail',
    )

    result = clear_qgate_findings('store-qgate-clear', '5-execute')
    assert result['status'] == 'success'
    assert result['cleared'] == 2

    query = query_qgate_findings('store-qgate-clear', '5-execute')
    assert query['total_count'] == 0


def test_clear_qgate_findings_empty(plan_context):
    """Test clearing Q-Gate findings when none exist."""
    result = clear_qgate_findings('store-qgate-clear-empty', '5-execute')
    assert result['status'] == 'success'
    assert result['cleared'] == 0


def test_script_source_uses_canonical_local_plans_path():
    """The script source references .plan/local/plans, not the legacy form.

    Regression guard for the path-consolidation sweep: the module docstring's
    Storage block and the ``get_findings_dir`` / ``get_findings_path`` /
    ``get_qgate_path`` / ``get_assessments_path`` docstrings must spell the
    findings location as ``.plan/local/plans/`` — the legacy bare
    ``.plan/plans/`` form is incorrect since runtime state moved under
    ``.plan/local``.
    """
    import re

    source = (_SCRIPTS_DIR / '_findings_core.py').read_text(encoding='utf-8')
    assert '.plan/local/plans/' in source
    legacy = re.findall(r'(?<!local/)\.plan/plans/', source)
    assert legacy == [], f'Legacy .plan/plans/ strings remain: {legacy}'
