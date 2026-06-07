#!/usr/bin/env python3
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

    # Resolve one
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

    # All bugs are now resolved; none remain pending.
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

    # The improvement finding must remain pending.
    pending_improve = query_findings(
        'store-bulk-other', finding_type='improvement', resolution='pending'
    )
    assert pending_improve['filtered_count'] == 1


def test_resolve_findings_by_type_skips_already_resolved(plan_context):
    """An already-resolved finding is not double-counted on a subsequent bulk resolve."""
    r1 = add_finding('store-bulk-dup', 'bug', 'Bug 1', 'Detail')
    add_finding('store-bulk-dup', 'bug', 'Bug 2', 'Detail')

    # Resolve one finding ahead of the bulk call.
    resolve_finding('store-bulk-dup', r1['hash_id'], 'fixed')

    # Bulk resolve should only pick up the one still-pending finding.
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

    # The tip finding is outside the type set and remains pending.
    pending_tip = query_findings('store-bulk-multi', finding_type='tip', resolution='pending')
    assert pending_tip['filtered_count'] == 1


def test_resolve_findings_by_type_invalid_resolution(plan_context):
    """An invalid target resolution returns the canonical error shape without mutating state."""
    add_finding('store-bulk-badres', 'bug', 'Bug 1', 'Detail')

    result = resolve_findings_by_type('store-bulk-badres', ('bug',), 'not-a-resolution')
    assert result['status'] == 'error'
    assert 'Invalid resolution' in result['message']

    # No finding was mutated.
    pending = query_findings('store-bulk-badres', finding_type='bug', resolution='pending')
    assert pending['filtered_count'] == 1


def test_resolve_findings_by_type_custom_from_resolution(plan_context):
    """Bulk resolve can re-resolve findings matching a non-default from_resolution."""
    r1 = add_finding('store-bulk-from', 'bug', 'Bug 1', 'Detail')
    add_finding('store-bulk-from', 'bug', 'Bug 2', 'Detail')

    # Move one finding to 'accepted'; the other stays pending.
    resolve_finding('store-bulk-from', r1['hash_id'], 'accepted')

    # Bulk re-resolve only the 'accepted' finding to 'fixed'.
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

    # Verify the finding is now marked promoted
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
    # Resolve it
    resolve_qgate_finding('store-qgate-reopen', '5-execute', r1['hash_id'], 'fixed')

    # Re-add same title
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

    # Query all
    result = query_qgate_findings('store-qgate-query', '5-execute')
    assert result['status'] == 'success'
    assert result['total_count'] == 2

    # Query by source
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

    # Verify cleared
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
