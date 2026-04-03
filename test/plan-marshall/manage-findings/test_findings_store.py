#!/usr/bin/env python3
"""Unit tests for _findings_core.py - the storage engine for findings and Q-Gate findings."""

import sys
from pathlib import Path

# Import shared infrastructure
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from conftest import PlanContext

# conftest sets up PYTHONPATH so we can import the store directly
from _findings_core import (  # type: ignore[import-not-found]
    FINDING_TYPES,
    QGATE_PHASES,
    QGATE_SOURCES,
    RESOLUTIONS,
    SEVERITIES,
    add_finding,
    add_qgate_finding,
    clear_qgate_findings,
    get_findings_path,
    get_qgate_path,
    promote_finding,
    query_findings,
    query_qgate_findings,
    resolve_finding,
    resolve_qgate_finding,
)


# =============================================================================
# Test: add_finding
# =============================================================================


def test_add_finding_basic():
    """Test adding a basic finding."""
    with PlanContext(plan_id='store-add-basic'):
        result = add_finding('store-add-basic', 'bug', 'Test bug', 'Detail here')
        assert result['status'] == 'success'
        assert 'hash_id' in result
        assert result['type'] == 'bug'


def test_add_finding_with_optional_fields():
    """Test adding a finding with all optional fields."""
    with PlanContext(plan_id='store-add-opts'):
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


def test_add_finding_invalid_type():
    """Test adding a finding with invalid type returns error."""
    with PlanContext(plan_id='store-add-badtype'):
        result = add_finding('store-add-badtype', 'nonexistent-type', 'Title', 'Detail')
        assert result['status'] == 'error'
        assert 'Invalid finding type' in result['message']


def test_add_finding_invalid_severity():
    """Test adding a finding with invalid severity returns error."""
    with PlanContext(plan_id='store-add-badsev'):
        result = add_finding('store-add-badsev', 'bug', 'Title', 'Detail', severity='critical')
        assert result['status'] == 'error'
        assert 'Invalid severity' in result['message']


# =============================================================================
# Test: query_findings
# =============================================================================


def test_query_findings_empty():
    """Test querying when no findings exist."""
    with PlanContext(plan_id='store-query-empty'):
        result = query_findings('store-query-empty')
        assert result['status'] == 'success'
        assert result['total_count'] == 0
        assert result['filtered_count'] == 0
        assert result['findings'] == []


def test_query_findings_all():
    """Test querying returns all findings."""
    with PlanContext(plan_id='store-query-all'):
        add_finding('store-query-all', 'bug', 'Bug 1', 'Detail 1')
        add_finding('store-query-all', 'improvement', 'Improve 1', 'Detail 2')

        result = query_findings('store-query-all')
        assert result['status'] == 'success'
        assert result['total_count'] == 2
        assert result['filtered_count'] == 2


def test_query_findings_by_type():
    """Test querying with type filter."""
    with PlanContext(plan_id='store-query-type'):
        add_finding('store-query-type', 'bug', 'Bug 1', 'Detail')
        add_finding('store-query-type', 'improvement', 'Improve 1', 'Detail')
        add_finding('store-query-type', 'bug', 'Bug 2', 'Detail')

        result = query_findings('store-query-type', finding_type='bug')
        assert result['status'] == 'success'
        assert result['total_count'] == 3
        assert result['filtered_count'] == 2


def test_query_findings_by_resolution():
    """Test querying with resolution filter."""
    with PlanContext(plan_id='store-query-res'):
        r1 = add_finding('store-query-res', 'bug', 'Bug 1', 'Detail')
        add_finding('store-query-res', 'bug', 'Bug 2', 'Detail')

        # Resolve one
        resolve_finding('store-query-res', r1['hash_id'], 'fixed')

        result = query_findings('store-query-res', resolution='pending')
        assert result['filtered_count'] == 1

        result = query_findings('store-query-res', resolution='fixed')
        assert result['filtered_count'] == 1


def test_query_findings_by_file_pattern():
    """Test querying with file pattern filter."""
    with PlanContext(plan_id='store-query-file'):
        add_finding('store-query-file', 'bug', 'Bug 1', 'Detail', file_path='src/main/java/Foo.java')
        add_finding('store-query-file', 'bug', 'Bug 2', 'Detail', file_path='src/test/java/FooTest.java')

        result = query_findings('store-query-file', file_pattern='src/main/*')
        assert result['filtered_count'] == 1


# =============================================================================
# Test: resolve_finding
# =============================================================================


def test_resolve_finding_success():
    """Test resolving a finding."""
    with PlanContext(plan_id='store-resolve'):
        r = add_finding('store-resolve', 'bug', 'Bug', 'Detail')
        hash_id = r['hash_id']

        result = resolve_finding('store-resolve', hash_id, 'fixed', detail='Fixed in commit abc123')
        assert result['status'] == 'success'
        assert result['hash_id'] == hash_id
        assert result['resolution'] == 'fixed'


def test_resolve_finding_invalid_resolution():
    """Test resolving with invalid resolution string."""
    with PlanContext(plan_id='store-resolve-bad'):
        r = add_finding('store-resolve-bad', 'bug', 'Bug', 'Detail')

        result = resolve_finding('store-resolve-bad', r['hash_id'], 'invalid-resolution')
        assert result['status'] == 'error'
        assert 'Invalid resolution' in result['message']


def test_resolve_finding_not_found():
    """Test resolving a non-existent finding."""
    with PlanContext(plan_id='store-resolve-nf'):
        result = resolve_finding('store-resolve-nf', 'nonexistent', 'fixed')
        assert result['status'] == 'error'
        assert 'not found' in result['message']


# =============================================================================
# Test: promote_finding
# =============================================================================


def test_promote_finding_success():
    """Test promoting a finding."""
    with PlanContext(plan_id='store-promote'):
        r = add_finding('store-promote', 'bug', 'Bug', 'Detail')
        hash_id = r['hash_id']

        result = promote_finding('store-promote', hash_id, 'manage-lessons')
        assert result['status'] == 'success'
        assert result['promoted_to'] == 'manage-lessons'

        # Verify the finding is now marked promoted
        query = query_findings('store-promote', promoted=True)
        assert query['filtered_count'] == 1


# =============================================================================
# Test: Q-Gate findings
# =============================================================================


def test_add_qgate_finding_basic():
    """Test adding a Q-Gate finding."""
    with PlanContext(plan_id='store-qgate-add'):
        result = add_qgate_finding(
            'store-qgate-add', '5-execute', 'qgate', 'build-error',
            'Build failure', 'Compilation failed',
        )
        assert result['status'] == 'success'
        assert 'hash_id' in result
        assert result['phase'] == '5-execute'


def test_add_qgate_finding_invalid_phase():
    """Test adding Q-Gate finding with invalid phase."""
    with PlanContext(plan_id='store-qgate-badphase'):
        result = add_qgate_finding(
            'store-qgate-badphase', '1-init', 'qgate', 'build-error',
            'Title', 'Detail',
        )
        assert result['status'] == 'error'
        assert 'Invalid Q-Gate phase' in result['message']


def test_add_qgate_finding_invalid_source():
    """Test adding Q-Gate finding with invalid source."""
    with PlanContext(plan_id='store-qgate-badsrc'):
        result = add_qgate_finding(
            'store-qgate-badsrc', '5-execute', 'invalid-source', 'build-error',
            'Title', 'Detail',
        )
        assert result['status'] == 'error'
        assert 'Invalid Q-Gate source' in result['message']


def test_qgate_dedup_pending():
    """Test Q-Gate deduplication for pending findings with same title."""
    with PlanContext(plan_id='store-qgate-dedup'):
        r1 = add_qgate_finding(
            'store-qgate-dedup', '5-execute', 'qgate', 'build-error',
            'Same title', 'Detail 1',
        )
        assert r1['status'] == 'success'

        r2 = add_qgate_finding(
            'store-qgate-dedup', '5-execute', 'qgate', 'build-error',
            'Same title', 'Detail 2',
        )
        assert r2['status'] == 'deduplicated'
        assert r2['hash_id'] == r1['hash_id']


def test_qgate_reopen_resolved():
    """Test Q-Gate reopens a resolved finding if re-detected."""
    with PlanContext(plan_id='store-qgate-reopen'):
        r1 = add_qgate_finding(
            'store-qgate-reopen', '5-execute', 'qgate', 'build-error',
            'Flaky test', 'Detail',
        )
        # Resolve it
        resolve_qgate_finding('store-qgate-reopen', '5-execute', r1['hash_id'], 'fixed')

        # Re-add same title
        r2 = add_qgate_finding(
            'store-qgate-reopen', '5-execute', 'qgate', 'build-error',
            'Flaky test', 'New detail',
        )
        assert r2['status'] == 'reopened'
        assert r2['hash_id'] == r1['hash_id']


def test_query_qgate_findings():
    """Test querying Q-Gate findings."""
    with PlanContext(plan_id='store-qgate-query'):
        add_qgate_finding(
            'store-qgate-query', '5-execute', 'qgate', 'build-error',
            'Error 1', 'Detail',
        )
        add_qgate_finding(
            'store-qgate-query', '5-execute', 'user_review', 'pr-comment',
            'Comment 1', 'Detail',
        )

        # Query all
        result = query_qgate_findings('store-qgate-query', '5-execute')
        assert result['status'] == 'success'
        assert result['total_count'] == 2

        # Query by source
        result = query_qgate_findings('store-qgate-query', '5-execute', source='qgate')
        assert result['filtered_count'] == 1


def test_resolve_qgate_finding():
    """Test resolving a Q-Gate finding."""
    with PlanContext(plan_id='store-qgate-resolve'):
        r = add_qgate_finding(
            'store-qgate-resolve', '5-execute', 'qgate', 'test-failure',
            'Test failure', 'Detail',
        )

        result = resolve_qgate_finding(
            'store-qgate-resolve', '5-execute', r['hash_id'], 'fixed', detail='Fixed it',
        )
        assert result['status'] == 'success'
        assert result['resolution'] == 'fixed'


def test_clear_qgate_findings():
    """Test clearing all Q-Gate findings for a phase."""
    with PlanContext(plan_id='store-qgate-clear'):
        add_qgate_finding(
            'store-qgate-clear', '5-execute', 'qgate', 'build-error',
            'Error 1', 'Detail',
        )
        add_qgate_finding(
            'store-qgate-clear', '5-execute', 'qgate', 'test-failure',
            'Error 2', 'Detail',
        )

        result = clear_qgate_findings('store-qgate-clear', '5-execute')
        assert result['status'] == 'success'
        assert result['cleared'] == 2

        # Verify cleared
        query = query_qgate_findings('store-qgate-clear', '5-execute')
        assert query['total_count'] == 0


def test_clear_qgate_findings_empty():
    """Test clearing Q-Gate findings when none exist."""
    with PlanContext(plan_id='store-qgate-clear-empty'):
        result = clear_qgate_findings('store-qgate-clear-empty', '5-execute')
        assert result['status'] == 'success'
        assert result['cleared'] == 0
