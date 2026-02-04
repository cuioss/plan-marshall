#!/usr/bin/env python3
"""Tests for manage-artifacts.py script."""

import sys
from pathlib import Path

# Import shared infrastructure
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from conftest import PlanContext, get_script_path, run_script

# Get script path
SCRIPT_PATH = get_script_path('pm-workflow', 'manage-plan-artifacts', 'manage-artifacts.py')

# Import toon_parser - conftest sets up PYTHONPATH
from toon_parser import parse_toon  # type: ignore[import-not-found]  # noqa: E402

# Alias for backward compatibility
TestContext = PlanContext


# =============================================================================
# Test: Assessment Add Command
# =============================================================================


def test_assessment_add_basic():
    """Test adding a basic assessment."""
    with TestContext():
        result = run_script(
            SCRIPT_PATH,
            'assessment', 'add', 'test-plan',
            'marketplace/bundles/pm-dev-java/skills/java-cdi/SKILL.md',
            'CERTAIN_INCLUDE', '95'
        )
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert 'hash_id' in data
        assert data['file_path'] == 'marketplace/bundles/pm-dev-java/skills/java-cdi/SKILL.md'


def test_assessment_add_with_options():
    """Test adding assessment with all options."""
    with TestContext():
        result = run_script(
            SCRIPT_PATH,
            'assessment', 'add', 'test-plan',
            'path/to/file.md',
            'CERTAIN_EXCLUDE', '85',
            '--agent', 'skill-analysis-agent',
            '--detail', 'No relevant content found',
            '--evidence', 'Checked ## Output section'
        )
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'


def test_assessment_add_uncertain():
    """Test adding an uncertain assessment."""
    with TestContext():
        result = run_script(
            SCRIPT_PATH,
            'assessment', 'add', 'test-plan',
            'path/to/ambiguous.md',
            'UNCERTAIN', '65',
            '--detail', 'JSON found in workflow context - unclear if output spec'
        )
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'


def test_assessment_add_invalid_certainty():
    """Test that invalid certainty is rejected."""
    with TestContext():
        result = run_script(
            SCRIPT_PATH,
            'assessment', 'add', 'test-plan',
            'path/to/file.md',
            'INVALID', '50'
        )
        # argparse should reject invalid choice
        assert not result.success


def test_assessment_add_invalid_confidence():
    """Test that out-of-range confidence is rejected."""
    with TestContext():
        result = run_script(
            SCRIPT_PATH,
            'assessment', 'add', 'test-plan',
            'path/to/file.md',
            'CERTAIN_INCLUDE', '150'
        )
        assert not result.success
        data = parse_toon(result.stdout)
        assert data['status'] == 'error'


# =============================================================================
# Test: Assessment Query Command
# =============================================================================


def test_assessment_query_empty():
    """Test querying with no assessments."""
    with TestContext():
        result = run_script(SCRIPT_PATH, 'assessment', 'query', 'test-plan')
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert data['total_count'] == 0


def test_assessment_query_all():
    """Test querying all assessments."""
    with TestContext():
        # Add some assessments
        run_script(SCRIPT_PATH, 'assessment', 'add', 'test-plan', 'file1.md', 'CERTAIN_INCLUDE', '90')
        run_script(SCRIPT_PATH, 'assessment', 'add', 'test-plan', 'file2.md', 'CERTAIN_EXCLUDE', '85')
        run_script(SCRIPT_PATH, 'assessment', 'add', 'test-plan', 'file3.md', 'UNCERTAIN', '60')

        result = run_script(SCRIPT_PATH, 'assessment', 'query', 'test-plan')
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['total_count'] == 3
        assert data['filtered_count'] == 3


def test_assessment_query_by_certainty():
    """Test filtering assessments by certainty."""
    with TestContext():
        run_script(SCRIPT_PATH, 'assessment', 'add', 'test-plan', 'file1.md', 'CERTAIN_INCLUDE', '90')
        run_script(SCRIPT_PATH, 'assessment', 'add', 'test-plan', 'file2.md', 'CERTAIN_EXCLUDE', '85')
        run_script(SCRIPT_PATH, 'assessment', 'add', 'test-plan', 'file3.md', 'UNCERTAIN', '60')

        result = run_script(
            SCRIPT_PATH, 'assessment', 'query', 'test-plan',
            '--certainty', 'CERTAIN_INCLUDE'
        )
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['total_count'] == 3
        assert data['filtered_count'] == 1
        assert 'file1.md' in data.get('file_paths', [])


def test_assessment_query_by_confidence():
    """Test filtering assessments by confidence range."""
    with TestContext():
        run_script(SCRIPT_PATH, 'assessment', 'add', 'test-plan', 'file1.md', 'CERTAIN_INCLUDE', '95')
        run_script(SCRIPT_PATH, 'assessment', 'add', 'test-plan', 'file2.md', 'CERTAIN_INCLUDE', '85')
        run_script(SCRIPT_PATH, 'assessment', 'add', 'test-plan', 'file3.md', 'CERTAIN_INCLUDE', '75')

        result = run_script(
            SCRIPT_PATH, 'assessment', 'query', 'test-plan',
            '--min-confidence', '80'
        )
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['filtered_count'] == 2


def test_assessment_query_file_paths_list():
    """Test that query returns file_paths list."""
    with TestContext():
        run_script(SCRIPT_PATH, 'assessment', 'add', 'test-plan', 'path/a.md', 'CERTAIN_INCLUDE', '90')
        run_script(SCRIPT_PATH, 'assessment', 'add', 'test-plan', 'path/b.md', 'CERTAIN_INCLUDE', '90')

        result = run_script(
            SCRIPT_PATH, 'assessment', 'query', 'test-plan',
            '--certainty', 'CERTAIN_INCLUDE'
        )
        assert result.success
        data = parse_toon(result.stdout)
        assert 'file_paths' in data
        assert len(data['file_paths']) == 2


# =============================================================================
# Test: Assessment Clear Command
# =============================================================================


def test_assessment_clear_all():
    """Test clearing all assessments."""
    with TestContext():
        run_script(SCRIPT_PATH, 'assessment', 'add', 'test-plan', 'file1.md', 'CERTAIN_INCLUDE', '90')
        run_script(SCRIPT_PATH, 'assessment', 'add', 'test-plan', 'file2.md', 'CERTAIN_EXCLUDE', '85')

        result = run_script(SCRIPT_PATH, 'assessment', 'clear', 'test-plan')
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert data['cleared'] == 2

        # Verify empty
        query_result = run_script(SCRIPT_PATH, 'assessment', 'query', 'test-plan')
        query_data = parse_toon(query_result.stdout)
        assert query_data['total_count'] == 0


def test_assessment_clear_by_agent():
    """Test clearing assessments filtered by agent name."""
    with TestContext():
        run_script(
            SCRIPT_PATH, 'assessment', 'add', 'test-plan', 'file1.md',
            'CERTAIN_INCLUDE', '90', '--agent', 'agent-a'
        )
        run_script(
            SCRIPT_PATH, 'assessment', 'add', 'test-plan', 'file2.md',
            'CERTAIN_EXCLUDE', '85', '--agent', 'agent-b'
        )
        run_script(
            SCRIPT_PATH, 'assessment', 'add', 'test-plan', 'file3.md',
            'CERTAIN_INCLUDE', '80', '--agent', 'agent-a'
        )

        result = run_script(
            SCRIPT_PATH, 'assessment', 'clear', 'test-plan',
            '--agent', 'agent-a'
        )
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert data['cleared'] == 2

        # Verify only agent-b remains
        query_result = run_script(SCRIPT_PATH, 'assessment', 'query', 'test-plan')
        query_data = parse_toon(query_result.stdout)
        assert query_data['total_count'] == 1
        assert 'file2.md' in query_data.get('file_paths', [])


def test_assessment_clear_empty():
    """Test clearing when no assessments exist."""
    with TestContext():
        result = run_script(SCRIPT_PATH, 'assessment', 'clear', 'test-plan')
        assert result.success
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert data['cleared'] == 0


# =============================================================================
# Test: Assessment Get Command
# =============================================================================


def test_assessment_get():
    """Test getting a specific assessment."""
    with TestContext():
        add_result = run_script(
            SCRIPT_PATH, 'assessment', 'add', 'test-plan',
            'file.md', 'CERTAIN_INCLUDE', '90'
        )
        add_data = parse_toon(add_result.stdout)
        hash_id = str(add_data['hash_id'])  # Ensure string for subprocess args

        result = run_script(SCRIPT_PATH, 'assessment', 'get', 'test-plan', hash_id)
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert data['file_path'] == 'file.md'
        assert data['certainty'] == 'CERTAIN_INCLUDE'


def test_assessment_get_not_found():
    """Test getting non-existent assessment."""
    with TestContext():
        result = run_script(SCRIPT_PATH, 'assessment', 'get', 'test-plan', 'nonexistent')
        assert not result.success


# =============================================================================
# Test: Finding Add Command
# =============================================================================


def test_finding_add_basic():
    """Test adding a basic finding."""
    with TestContext():
        result = run_script(
            SCRIPT_PATH,
            'finding', 'add', 'test-plan',
            'bug', 'Test failure in CacheTest',
            '--detail', 'AssertionError: expected 5 but got 3'
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
            'finding', 'add', 'test-plan',
            'sonar-issue', 'S1192: String literals duplicated',
            '--detail', 'String "application/json" appears 5 times',
            '--file-path', 'src/main/java/Api.java',
            '--line', '42',
            '--rule', 'java:S1192',
            '--severity', 'warning'
        )
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'


def test_finding_add_all_types():
    """Test that all finding types are accepted."""
    finding_types = [
        'bug', 'improvement', 'anti-pattern', 'triage',
        'tip', 'insight', 'best-practice',
        'build-error', 'test-failure', 'lint-issue', 'sonar-issue', 'pr-comment'
    ]
    with TestContext():
        for ftype in finding_types:
            result = run_script(
                SCRIPT_PATH,
                'finding', 'add', 'test-plan',
                ftype, f'Test {ftype}',
                '--detail', f'Testing {ftype} type'
            )
            assert result.success, f'Failed for type {ftype}: {result.stderr}'


# =============================================================================
# Test: Finding Query Command
# =============================================================================


def test_finding_query_empty():
    """Test querying with no findings."""
    with TestContext():
        result = run_script(SCRIPT_PATH, 'finding', 'query', 'test-plan')
        assert result.success
        data = parse_toon(result.stdout)
        assert data['total_count'] == 0


def test_finding_query_by_type():
    """Test filtering findings by type."""
    with TestContext():
        run_script(SCRIPT_PATH, 'finding', 'add', 'test-plan', 'bug', 'Bug 1', '--detail', 'd')
        run_script(SCRIPT_PATH, 'finding', 'add', 'test-plan', 'tip', 'Tip 1', '--detail', 'd')
        run_script(SCRIPT_PATH, 'finding', 'add', 'test-plan', 'bug', 'Bug 2', '--detail', 'd')

        result = run_script(SCRIPT_PATH, 'finding', 'query', 'test-plan', '--type', 'bug')
        assert result.success
        data = parse_toon(result.stdout)
        assert data['filtered_count'] == 2


def test_finding_query_by_resolution():
    """Test filtering findings by resolution."""
    with TestContext():
        # Add a finding
        add_result = run_script(
            SCRIPT_PATH, 'finding', 'add', 'test-plan',
            'bug', 'Bug to fix', '--detail', 'd'
        )
        hash_id = str(parse_toon(add_result.stdout)['hash_id'])

        # Resolve it
        run_script(
            SCRIPT_PATH, 'finding', 'resolve', 'test-plan',
            hash_id, 'fixed', '--detail', 'Fixed in commit abc'
        )

        # Query by resolution
        result = run_script(
            SCRIPT_PATH, 'finding', 'query', 'test-plan',
            '--resolution', 'fixed'
        )
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
            SCRIPT_PATH, 'finding', 'add', 'test-plan',
            'build-error', 'Compilation error',
            '--detail', 'Missing import'
        )
        hash_id = str(parse_toon(add_result.stdout)['hash_id'])

        result = run_script(
            SCRIPT_PATH, 'finding', 'resolve', 'test-plan',
            hash_id, 'fixed',
            '--detail', 'Added missing import statement'
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
                SCRIPT_PATH, 'finding', 'add', 'test-plan',
                'bug', f'Bug for {res}', '--detail', 'd'
            )
            hash_id = str(parse_toon(add_result.stdout)['hash_id'])

            result = run_script(
                SCRIPT_PATH, 'finding', 'resolve', 'test-plan',
                hash_id, res
            )
            assert result.success, f'Failed for resolution {res}'


# =============================================================================
# Test: Finding Promote Command
# =============================================================================


def test_finding_promote():
    """Test promoting a finding."""
    with TestContext():
        add_result = run_script(
            SCRIPT_PATH, 'finding', 'add', 'test-plan',
            'tip', 'Use constructor injection',
            '--detail', 'Prefer constructor injection over field injection for testability'
        )
        hash_id = str(parse_toon(add_result.stdout)['hash_id'])

        result = run_script(
            SCRIPT_PATH, 'finding', 'promote', 'test-plan',
            hash_id, 'architecture'
        )
        assert result.success
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert data['promoted_to'] == 'architecture'


def test_finding_promote_to_lessons():
    """Test promoting to lessons learned."""
    with TestContext():
        add_result = run_script(
            SCRIPT_PATH, 'finding', 'add', 'test-plan',
            'bug', 'Null pointer from missing null check',
            '--detail', 'Always check for null before calling methods on optional fields'
        )
        hash_id = str(parse_toon(add_result.stdout)['hash_id'])

        result = run_script(
            SCRIPT_PATH, 'finding', 'promote', 'test-plan',
            hash_id, 'lessons-2025-01-22-001'
        )
        assert result.success
        data = parse_toon(result.stdout)
        assert 'lessons-' in data['promoted_to']


def test_finding_query_promoted():
    """Test filtering by promoted status."""
    with TestContext():
        # Add and promote one
        add_result = run_script(
            SCRIPT_PATH, 'finding', 'add', 'test-plan',
            'tip', 'Promoted tip', '--detail', 'd'
        )
        hash_id = str(parse_toon(add_result.stdout)['hash_id'])
        run_script(SCRIPT_PATH, 'finding', 'promote', 'test-plan', hash_id, 'architecture')

        # Add one not promoted
        run_script(SCRIPT_PATH, 'finding', 'add', 'test-plan', 'tip', 'Not promoted', '--detail', 'd')

        # Query promoted
        result = run_script(
            SCRIPT_PATH, 'finding', 'query', 'test-plan',
            '--promoted', 'true'
        )
        assert result.success
        data = parse_toon(result.stdout)
        assert data['filtered_count'] == 1

        # Query not promoted
        result = run_script(
            SCRIPT_PATH, 'finding', 'query', 'test-plan',
            '--promoted', 'false'
        )
        assert result.success
        data = parse_toon(result.stdout)
        assert data['filtered_count'] == 1
