#!/usr/bin/env python3
"""Tests for manage-findings.py script."""

import sys
from pathlib import Path

# Import shared infrastructure
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from conftest import PlanContext, get_script_path, run_script

# Get script path
SCRIPT_PATH = get_script_path('pm-workflow', 'manage-findings', 'manage-findings.py')

# Import toon_parser - conftest sets up PYTHONPATH
from toon_parser import parse_toon  # type: ignore[import-not-found]  # noqa: E402

# Alias for backward compatibility
TestContext = PlanContext


# =============================================================================
# Test: Finding Add Command
# =============================================================================


def test_finding_add_basic():
    """Test adding a basic finding."""
    with TestContext():
        result = run_script(
            SCRIPT_PATH,
            'add',
            '--plan-id', 'test-plan',
            '--type', 'bug',
            '--title', 'Test failure in CacheTest',
            '--detail',
            'AssertionError: expected 5 but got 3',
        )
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert 'hash_id' in data
        assert data['type'] == 'bug'


def test_finding_add_with_file_info():
    """Test adding finding with file location."""
    with TestContext():
        result = run_script(
            SCRIPT_PATH,
            'add',
            '--plan-id', 'test-plan',
            '--type', 'sonar-issue',
            '--title', 'S1192: String literals duplicated',
            '--detail',
            'String "application/json" appears 5 times',
            '--file-path',
            'src/main/java/Api.java',
            '--line',
            '42',
            '--rule',
            'java:S1192',
            '--severity',
            'warning',
        )
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'


def test_finding_add_all_types():
    """Test that all finding types are accepted."""
    finding_types = [
        'bug',
        'improvement',
        'anti-pattern',
        'triage',
        'tip',
        'insight',
        'best-practice',
        'build-error',
        'test-failure',
        'lint-issue',
        'sonar-issue',
        'pr-comment',
    ]
    with TestContext():
        for ftype in finding_types:
            result = run_script(
                SCRIPT_PATH, 'add', '--plan-id', 'test-plan', '--type', ftype, '--title', f'Test {ftype}', '--detail', f'Testing {ftype} type'
            )
            assert result.success, f'Failed for type {ftype}: {result.stderr}'


# =============================================================================
# Test: Finding Query Command
# =============================================================================


def test_finding_query_empty():
    """Test querying with no findings."""
    with TestContext():
        result = run_script(SCRIPT_PATH, 'query', '--plan-id', 'test-plan')
        assert result.success
        data = parse_toon(result.stdout)
        assert data['total_count'] == 0


def test_finding_query_by_type():
    """Test filtering findings by type."""
    with TestContext():
        run_script(SCRIPT_PATH, 'add', '--plan-id', 'test-plan', '--type', 'bug', '--title', 'Bug 1', '--detail', 'd')
        run_script(SCRIPT_PATH, 'add', '--plan-id', 'test-plan', '--type', 'tip', '--title', 'Tip 1', '--detail', 'd')
        run_script(SCRIPT_PATH, 'add', '--plan-id', 'test-plan', '--type', 'bug', '--title', 'Bug 2', '--detail', 'd')

        result = run_script(SCRIPT_PATH, 'query', '--plan-id', 'test-plan', '--type', 'bug')
        assert result.success
        data = parse_toon(result.stdout)
        assert data['filtered_count'] == 2


def test_finding_query_by_resolution():
    """Test filtering findings by resolution."""
    with TestContext():
        # Add a finding
        add_result = run_script(SCRIPT_PATH, 'add', '--plan-id', 'test-plan', '--type', 'bug', '--title', 'Bug to fix', '--detail', 'd')
        hash_id = str(parse_toon(add_result.stdout)['hash_id'])

        # Resolve it
        run_script(SCRIPT_PATH, 'resolve', '--plan-id', 'test-plan', '--hash-id', hash_id, '--resolution', 'fixed', '--detail', 'Fixed in commit abc')

        # Query by resolution
        result = run_script(SCRIPT_PATH, 'query', '--plan-id', 'test-plan', '--resolution', 'fixed')
        assert result.success
        data = parse_toon(result.stdout)
        assert data['filtered_count'] == 1


# =============================================================================
# Test: Finding Resolve Command
# =============================================================================


def test_finding_resolve():
    """Test resolving a finding."""
    with TestContext():
        add_result = run_script(
            SCRIPT_PATH, 'add', '--plan-id', 'test-plan', '--type', 'build-error', '--title', 'Compilation error', '--detail', 'Missing import'
        )
        hash_id = str(parse_toon(add_result.stdout)['hash_id'])

        result = run_script(
            SCRIPT_PATH,
            'resolve',
            '--plan-id', 'test-plan',
            '--hash-id', hash_id,
            '--resolution', 'fixed',
            '--detail',
            'Added missing import statement',
        )
        assert result.success
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert data['resolution'] == 'fixed'


def test_finding_resolve_all_statuses():
    """Test all resolution statuses."""
    resolutions = ['pending', 'fixed', 'suppressed', 'accepted']
    with TestContext():
        for res in resolutions:
            add_result = run_script(
                SCRIPT_PATH, 'add', '--plan-id', 'test-plan', '--type', 'bug', '--title', f'Bug for {res}', '--detail', 'd'
            )
            hash_id = str(parse_toon(add_result.stdout)['hash_id'])

            result = run_script(SCRIPT_PATH, 'resolve', '--plan-id', 'test-plan', '--hash-id', hash_id, '--resolution', res)
            assert result.success, f'Failed for resolution {res}'


# =============================================================================
# Test: Finding Promote Command
# =============================================================================


def test_finding_promote():
    """Test promoting a finding."""
    with TestContext():
        add_result = run_script(
            SCRIPT_PATH,
            'add',
            '--plan-id', 'test-plan',
            '--type', 'tip',
            '--title', 'Use constructor injection',
            '--detail',
            'Prefer constructor injection over field injection for testability',
        )
        hash_id = str(parse_toon(add_result.stdout)['hash_id'])

        result = run_script(SCRIPT_PATH, 'promote', '--plan-id', 'test-plan', '--hash-id', hash_id, '--promoted-to', 'architecture')
        assert result.success
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert data['promoted_to'] == 'architecture'


def test_finding_promote_to_lessons():
    """Test promoting to lessons learned."""
    with TestContext():
        add_result = run_script(
            SCRIPT_PATH,
            'add',
            '--plan-id', 'test-plan',
            '--type', 'bug',
            '--title', 'Null pointer from missing null check',
            '--detail',
            'Always check for null before calling methods on optional fields',
        )
        hash_id = str(parse_toon(add_result.stdout)['hash_id'])

        result = run_script(SCRIPT_PATH, 'promote', '--plan-id', 'test-plan', '--hash-id', hash_id, '--promoted-to', 'lessons-2025-01-22-001')
        assert result.success
        data = parse_toon(result.stdout)
        assert 'lessons-' in data['promoted_to']


def test_finding_query_promoted():
    """Test filtering by promoted status."""
    with TestContext():
        # Add and promote one
        add_result = run_script(SCRIPT_PATH, 'add', '--plan-id', 'test-plan', '--type', 'tip', '--title', 'Promoted tip', '--detail', 'd')
        hash_id = str(parse_toon(add_result.stdout)['hash_id'])
        run_script(SCRIPT_PATH, 'promote', '--plan-id', 'test-plan', '--hash-id', hash_id, '--promoted-to', 'architecture')

        # Add one not promoted
        run_script(SCRIPT_PATH, 'add', '--plan-id', 'test-plan', '--type', 'tip', '--title', 'Not promoted', '--detail', 'd')

        # Query promoted
        result = run_script(SCRIPT_PATH, 'query', '--plan-id', 'test-plan', '--promoted', 'true')
        assert result.success
        data = parse_toon(result.stdout)
        assert data['filtered_count'] == 1

        # Query not promoted
        result = run_script(SCRIPT_PATH, 'query', '--plan-id', 'test-plan', '--promoted', 'false')
        assert result.success
        data = parse_toon(result.stdout)
        assert data['filtered_count'] == 1


# =============================================================================
# Test: Q-Gate Add Command
# =============================================================================


def test_qgate_add_basic():
    """Test adding a basic Q-Gate finding."""
    with TestContext(plan_id='qgate-add-basic'):
        result = run_script(
            SCRIPT_PATH,
            'qgate',
            'add',
            '--plan-id', 'qgate-add-basic',
            '--phase',
            '3-outline',
            '--source',
            'qgate',
            '--type',
            'triage',
            '--title',
            'False positive: helper.py',
            '--detail',
            'File is consumer-only, not a producer',
        )
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert 'hash_id' in data
        assert data['phase'] == '3-outline'


def test_qgate_add_with_options():
    """Test adding Q-Gate finding with all options."""
    with TestContext(plan_id='qgate-add-opts'):
        result = run_script(
            SCRIPT_PATH,
            'qgate',
            'add',
            '--plan-id', 'qgate-add-opts',
            '--phase',
            '3-outline',
            '--source',
            'user_review',
            '--type',
            'triage',
            '--title',
            'User: Add module X',
            '--detail',
            'User requested adding module X to scope',
            '--file-path',
            'src/module-x/main.py',
            '--component',
            'deliverable-3',
            '--severity',
            'warning',
            '--iteration',
            '2',
        )
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'


def test_qgate_add_invalid_phase():
    """Test that invalid phase is rejected."""
    with TestContext(plan_id='qgate-inv-phase'):
        result = run_script(
            SCRIPT_PATH,
            'qgate',
            'add',
            '--plan-id', 'qgate-inv-phase',
            '--phase',
            'invalid-phase',
            '--source',
            'qgate',
            '--type',
            'triage',
            '--title',
            'Test',
            '--detail',
            'Test detail',
        )
        assert not result.success


def test_qgate_add_invalid_source():
    """Test that invalid source is rejected."""
    with TestContext(plan_id='qgate-inv-source'):
        result = run_script(
            SCRIPT_PATH,
            'qgate',
            'add',
            '--plan-id', 'qgate-inv-source',
            '--phase',
            '3-outline',
            '--source',
            'invalid',
            '--type',
            'triage',
            '--title',
            'Test',
            '--detail',
            'Test detail',
        )
        assert not result.success


# =============================================================================
# Test: Q-Gate Query Command
# =============================================================================


def test_qgate_query_empty():
    """Test querying with no Q-Gate findings."""
    with TestContext(plan_id='qgate-query-empty'):
        result = run_script(SCRIPT_PATH, 'qgate', 'query', '--plan-id', 'qgate-query-empty', '--phase', '3-outline')
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert data['total_count'] == 0
        assert data['phase'] == '3-outline'


def test_qgate_query_by_resolution():
    """Test filtering Q-Gate findings by resolution."""
    with TestContext(plan_id='qgate-query-res'):
        # Add two findings
        run_script(
            SCRIPT_PATH,
            'qgate', 'add', '--plan-id', 'qgate-query-res',
            '--phase', '3-outline', '--source', 'qgate',
            '--type', 'triage', '--title', 'Finding 1', '--detail', 'd1',
        )
        add_result = run_script(
            SCRIPT_PATH,
            'qgate', 'add', '--plan-id', 'qgate-query-res',
            '--phase', '3-outline', '--source', 'qgate',
            '--type', 'triage', '--title', 'Finding 2', '--detail', 'd2',
        )
        hash_id = str(parse_toon(add_result.stdout)['hash_id'])

        # Resolve one
        run_script(
            SCRIPT_PATH, 'qgate', 'resolve', '--plan-id', 'qgate-query-res', '--hash-id', hash_id,
            '--resolution', 'taken_into_account', '--phase', '3-outline',
            '--detail', 'Addressed by revising deliverable 3',
        )

        # Query pending
        result = run_script(
            SCRIPT_PATH, 'qgate', 'query', '--plan-id', 'qgate-query-res',
            '--phase', '3-outline', '--resolution', 'pending',
        )
        assert result.success
        data = parse_toon(result.stdout)
        assert data['filtered_count'] == 1

        # Query taken_into_account
        result = run_script(
            SCRIPT_PATH, 'qgate', 'query', '--plan-id', 'qgate-query-res',
            '--phase', '3-outline', '--resolution', 'taken_into_account',
        )
        assert result.success
        data = parse_toon(result.stdout)
        assert data['filtered_count'] == 1


def test_qgate_query_by_source():
    """Test filtering Q-Gate findings by source."""
    with TestContext(plan_id='qgate-query-src'):
        run_script(
            SCRIPT_PATH,
            'qgate', 'add', '--plan-id', 'qgate-query-src',
            '--phase', '3-outline', '--source', 'qgate',
            '--type', 'triage', '--title', 'Auto finding', '--detail', 'd',
        )
        run_script(
            SCRIPT_PATH,
            'qgate', 'add', '--plan-id', 'qgate-query-src',
            '--phase', '3-outline', '--source', 'user_review',
            '--type', 'triage', '--title', 'User finding', '--detail', 'd',
        )

        result = run_script(
            SCRIPT_PATH, 'qgate', 'query', '--plan-id', 'qgate-query-src',
            '--phase', '3-outline', '--source', 'user_review',
        )
        assert result.success
        data = parse_toon(result.stdout)
        assert data['total_count'] == 2
        assert data['filtered_count'] == 1


def test_qgate_per_phase_isolation():
    """Test that Q-Gate findings are isolated per phase."""
    with TestContext(plan_id='qgate-phase-iso'):
        # Add to phase 3
        run_script(
            SCRIPT_PATH,
            'qgate', 'add', '--plan-id', 'qgate-phase-iso',
            '--phase', '3-outline', '--source', 'qgate',
            '--type', 'triage', '--title', 'Phase 3 finding', '--detail', 'd',
        )
        # Add to phase 4
        run_script(
            SCRIPT_PATH,
            'qgate', 'add', '--plan-id', 'qgate-phase-iso',
            '--phase', '4-plan', '--source', 'qgate',
            '--type', 'triage', '--title', 'Phase 4 finding', '--detail', 'd',
        )

        # Query phase 3 only
        result = run_script(SCRIPT_PATH, 'qgate', 'query', '--plan-id', 'qgate-phase-iso', '--phase', '3-outline')
        assert result.success
        data = parse_toon(result.stdout)
        assert data['total_count'] == 1
        assert data['phase'] == '3-outline'

        # Query phase 4 only
        result = run_script(SCRIPT_PATH, 'qgate', 'query', '--plan-id', 'qgate-phase-iso', '--phase', '4-plan')
        assert result.success
        data = parse_toon(result.stdout)
        assert data['total_count'] == 1
        assert data['phase'] == '4-plan'


# =============================================================================
# Test: Q-Gate Resolve Command
# =============================================================================


def test_qgate_resolve_taken_into_account():
    """Test resolving a Q-Gate finding with taken_into_account."""
    with TestContext(plan_id='qgate-resolve-tia'):
        add_result = run_script(
            SCRIPT_PATH,
            'qgate', 'add', '--plan-id', 'qgate-resolve-tia',
            '--phase', '3-outline', '--source', 'qgate',
            '--type', 'triage', '--title', 'Missing coverage', '--detail', 'File X not covered',
        )
        hash_id = str(parse_toon(add_result.stdout)['hash_id'])

        result = run_script(
            SCRIPT_PATH, 'qgate', 'resolve', '--plan-id', 'qgate-resolve-tia', '--hash-id', hash_id,
            '--resolution', 'taken_into_account', '--phase', '3-outline',
            '--detail', 'Added file X to deliverable 2',
        )
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert data['resolution'] == 'taken_into_account'


def test_qgate_resolve_all_statuses():
    """Test all resolution statuses for Q-Gate findings."""
    resolutions = ['pending', 'fixed', 'suppressed', 'accepted', 'taken_into_account']
    with TestContext(plan_id='qgate-resolve-all-st'):
        for res in resolutions:
            add_result = run_script(
                SCRIPT_PATH,
                'qgate', 'add', '--plan-id', 'qgate-resolve-all-st',
                '--phase', '6-verify', '--source', 'qgate',
                '--type', 'triage', '--title', f'Finding for {res}', '--detail', 'd',
            )
            assert add_result.success, f'Add failed for {res}: {add_result.stdout}'
            hash_id = str(parse_toon(add_result.stdout)['hash_id'])

            result = run_script(
                SCRIPT_PATH, 'qgate', 'resolve', '--plan-id', 'qgate-resolve-all-st', '--hash-id', hash_id,
                '--resolution', res, '--phase', '6-verify',
            )
            assert result.success, f'Failed for resolution {res}: stdout={result.stdout}'


# =============================================================================
# Test: Q-Gate Clear Command
# =============================================================================


def test_qgate_clear():
    """Test clearing Q-Gate findings for a phase."""
    with TestContext(plan_id='qgate-clear'):
        run_script(
            SCRIPT_PATH,
            'qgate', 'add', '--plan-id', 'qgate-clear',
            '--phase', '3-outline', '--source', 'qgate',
            '--type', 'triage', '--title', 'Finding 1', '--detail', 'd',
        )
        run_script(
            SCRIPT_PATH,
            'qgate', 'add', '--plan-id', 'qgate-clear',
            '--phase', '3-outline', '--source', 'qgate',
            '--type', 'triage', '--title', 'Finding 2', '--detail', 'd',
        )

        result = run_script(SCRIPT_PATH, 'qgate', 'clear', '--plan-id', 'qgate-clear', '--phase', '3-outline')
        assert result.success
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert data['cleared'] == 2

        # Verify empty
        query_result = run_script(SCRIPT_PATH, 'qgate', 'query', '--plan-id', 'qgate-clear', '--phase', '3-outline')
        query_data = parse_toon(query_result.stdout)
        assert query_data['total_count'] == 0


def test_qgate_clear_empty():
    """Test clearing when no Q-Gate findings exist."""
    with TestContext(plan_id='qgate-clear-empty'):
        result = run_script(SCRIPT_PATH, 'qgate', 'clear', '--plan-id', 'qgate-clear-empty', '--phase', '3-outline')
        assert result.success
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert data['cleared'] == 0


def test_qgate_user_review_source():
    """Test that user_review findings work end-to-end."""
    with TestContext(plan_id='qgate-user-review'):
        # Add user review finding
        add_result = run_script(
            SCRIPT_PATH,
            'qgate', 'add', '--plan-id', 'qgate-user-review',
            '--phase', '3-outline', '--source', 'user_review',
            '--type', 'triage', '--title', 'User: scope too narrow',
            '--detail', 'Please include module Y in the deliverables',
        )
        assert add_result.success
        hash_id = str(parse_toon(add_result.stdout)['hash_id'])

        # Query user_review findings
        query_result = run_script(
            SCRIPT_PATH, 'qgate', 'query', '--plan-id', 'qgate-user-review',
            '--phase', '3-outline', '--source', 'user_review',
        )
        assert query_result.success
        data = parse_toon(query_result.stdout)
        assert data['filtered_count'] == 1

        # Resolve as taken_into_account
        resolve_result = run_script(
            SCRIPT_PATH, 'qgate', 'resolve', '--plan-id', 'qgate-user-review', '--hash-id', hash_id,
            '--resolution', 'taken_into_account', '--phase', '3-outline',
            '--detail', 'Added module Y to deliverable scope',
        )
        assert resolve_result.success

        # Verify resolved
        verify_result = run_script(
            SCRIPT_PATH, 'qgate', 'query', '--plan-id', 'qgate-user-review',
            '--phase', '3-outline', '--resolution', 'pending',
        )
        assert verify_result.success
        verify_data = parse_toon(verify_result.stdout)
        assert verify_data['filtered_count'] == 0


# =============================================================================
# Test: Finding Resolve with taken_into_account (extended)
# =============================================================================


# =============================================================================
# Test: Q-Gate Deduplication
# =============================================================================


def test_qgate_add_dedup_pending():
    """Test that adding same title twice returns deduplicated, only 1 record."""
    with TestContext(plan_id='qgate-dedup-pend'):
        result1 = run_script(
            SCRIPT_PATH,
            'qgate', 'add', '--plan-id', 'qgate-dedup-pend',
            '--phase', '3-outline', '--source', 'qgate',
            '--type', 'triage', '--title', 'Missing assessment for helper.py', '--detail', 'd1',
        )
        assert result1.success
        data1 = parse_toon(result1.stdout)
        assert data1['status'] == 'success'
        original_hash = str(data1['hash_id'])

        # Add same title again
        result2 = run_script(
            SCRIPT_PATH,
            'qgate', 'add', '--plan-id', 'qgate-dedup-pend',
            '--phase', '3-outline', '--source', 'qgate',
            '--type', 'triage', '--title', 'Missing assessment for helper.py', '--detail', 'd2',
        )
        assert result2.success
        data2 = parse_toon(result2.stdout)
        assert data2['status'] == 'deduplicated'
        assert str(data2['hash_id']) == original_hash

        # Verify only 1 record exists
        query_result = run_script(
            SCRIPT_PATH, 'qgate', 'query', '--plan-id', 'qgate-dedup-pend', '--phase', '3-outline',
        )
        query_data = parse_toon(query_result.stdout)
        assert query_data['total_count'] == 1


def test_qgate_add_reopen_resolved():
    """Test that re-adding a resolved finding reopens it."""
    with TestContext(plan_id='qgate-dedup-reopen'):
        # Add finding
        add_result = run_script(
            SCRIPT_PATH,
            'qgate', 'add', '--plan-id', 'qgate-dedup-reopen',
            '--phase', '3-outline', '--source', 'qgate',
            '--type', 'triage', '--title', 'Missing coverage for utils.py', '--detail', 'd1',
        )
        assert add_result.success
        hash_id = str(parse_toon(add_result.stdout)['hash_id'])

        # Resolve it
        run_script(
            SCRIPT_PATH, 'qgate', 'resolve', '--plan-id', 'qgate-dedup-reopen', '--hash-id', hash_id,
            '--resolution', 'taken_into_account', '--phase', '3-outline',
            '--detail', 'Addressed',
        )

        # Re-add same title
        reopen_result = run_script(
            SCRIPT_PATH,
            'qgate', 'add', '--plan-id', 'qgate-dedup-reopen',
            '--phase', '3-outline', '--source', 'qgate',
            '--type', 'triage', '--title', 'Missing coverage for utils.py', '--detail', 'd2',
        )
        assert reopen_result.success
        reopen_data = parse_toon(reopen_result.stdout)
        assert reopen_data['status'] == 'reopened'
        assert str(reopen_data['hash_id']) == hash_id

        # Verify it's pending again
        query_result = run_script(
            SCRIPT_PATH, 'qgate', 'query', '--plan-id', 'qgate-dedup-reopen',
            '--phase', '3-outline', '--resolution', 'pending',
        )
        query_data = parse_toon(query_result.stdout)
        assert query_data['filtered_count'] == 1


def test_qgate_add_different_titles_not_deduped():
    """Test that different titles create separate findings."""
    with TestContext(plan_id='qgate-dedup-diff'):
        run_script(
            SCRIPT_PATH,
            'qgate', 'add', '--plan-id', 'qgate-dedup-diff',
            '--phase', '3-outline', '--source', 'qgate',
            '--type', 'triage', '--title', 'Finding A', '--detail', 'd1',
        )
        run_script(
            SCRIPT_PATH,
            'qgate', 'add', '--plan-id', 'qgate-dedup-diff',
            '--phase', '3-outline', '--source', 'qgate',
            '--type', 'triage', '--title', 'Finding B', '--detail', 'd2',
        )

        query_result = run_script(
            SCRIPT_PATH, 'qgate', 'query', '--plan-id', 'qgate-dedup-diff', '--phase', '3-outline',
        )
        query_data = parse_toon(query_result.stdout)
        assert query_data['total_count'] == 2


# =============================================================================
# Test: Finding Resolve with taken_into_account (extended)
# =============================================================================


def test_finding_resolve_taken_into_account():
    """Test that taken_into_account resolution works for regular findings too."""
    with TestContext():
        add_result = run_script(
            SCRIPT_PATH, 'add', '--plan-id', 'test-plan', '--type', 'triage', '--title', 'Reviewed finding', '--detail', 'd',
        )
        hash_id = str(parse_toon(add_result.stdout)['hash_id'])

        result = run_script(
            SCRIPT_PATH, 'resolve', '--plan-id', 'test-plan', '--hash-id', hash_id, '--resolution', 'taken_into_account', '--detail', 'Addressed in revision',
        )
        assert result.success
        data = parse_toon(result.stdout)
        assert data['resolution'] == 'taken_into_account'
