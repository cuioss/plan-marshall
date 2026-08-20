#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Unit tests for _findings_core.py - the storage engine for findings and Q-Gate findings."""


from _findings_store_fixtures import (
    add_finding,
    add_qgate_finding,
    add_qgate_finding_checked,
    query_findings,
    query_qgate_findings,
    resolve_qgate_finding,
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


# =============================================================================
# Test: add_qgate_finding_checked — the centralized persist+partition helper
# =============================================================================
#
# add_qgate_finding_checked wraps add_qgate_finding and partitions its status
# into (hash_id, failure_descriptor). It centralizes the QGATE_PERSIST_OK
# membership check that github_pr/gitlab_pr/sonar previously each duplicated.
# These tests drive the REAL primitive (never a stub) through both halves of
# that partition.


def test_add_qgate_finding_checked_success_yields_hash_id_no_failure(plan_context):
    """A fresh `success` persist yields a hash_id and no failure descriptor."""
    hash_id, failure = add_qgate_finding_checked(
        'store-qgate-checked-success',
        '5-execute',
        'qgate',
        'build-error',
        'Checked probe',
        'Detail',
    )

    assert hash_id is not None
    assert failure is None

    stored = query_qgate_findings('store-qgate-checked-success', '5-execute')
    assert stored['filtered_count'] == 1
    assert stored['findings'][0]['hash_id'] == hash_id


def test_add_qgate_finding_checked_deduplicated_yields_hash_id_no_failure(plan_context):
    """A `deduplicated` persist outcome (identical pending record) still yields
    the existing hash_id and no failure descriptor."""
    pid = 'store-qgate-checked-dedup'
    first_hash, first_failure = add_qgate_finding_checked(
        pid, '5-execute', 'qgate', 'build-error', 'Dup probe', 'Detail',
    )
    assert first_failure is None

    second_hash, second_failure = add_qgate_finding_checked(
        pid, '5-execute', 'qgate', 'build-error', 'Dup probe', 'Detail',
    )

    assert second_hash == first_hash
    assert second_failure is None


def test_add_qgate_finding_checked_reopened_yields_hash_id_no_failure(plan_context):
    """A `reopened` persist outcome (same defect re-detected after resolution)
    yields the reopened hash_id and no failure descriptor."""
    pid = 'store-qgate-checked-reopen'
    first_hash, _ = add_qgate_finding_checked(
        pid, '5-execute', 'qgate', 'build-error', 'Reopen probe', 'Detail',
    )
    resolve_qgate_finding(pid, '5-execute', first_hash, 'fixed')

    second_hash, second_failure = add_qgate_finding_checked(
        pid, '5-execute', 'qgate', 'build-error', 'Reopen probe', 'Detail',
    )

    assert second_hash == first_hash
    assert second_failure is None


def test_add_qgate_finding_checked_rejected_yields_failure_descriptor(plan_context):
    """A rejected persist (invalid finding type) yields (None, failure), where
    `failure` carries the finding's own title/detail plus the primitive's
    rejection message — never silently folded into a benign zero."""
    hash_id, failure = add_qgate_finding_checked(
        'store-qgate-checked-rejected',
        '5-execute',
        'qgate',
        'not-a-finding-type',
        'Rejected probe',
        'Detail',
    )

    assert hash_id is None
    assert failure is not None
    assert failure['title'] == 'Rejected probe'
    assert failure['detail'] == 'Detail'
    assert 'Invalid finding type' in failure['message']

    stored = query_qgate_findings('store-qgate-checked-rejected', '5-execute')
    assert stored['filtered_count'] == 0
