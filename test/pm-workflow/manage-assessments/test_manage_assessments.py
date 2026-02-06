#!/usr/bin/env python3
"""Tests for manage-assessments.py script."""

import sys
from pathlib import Path

# Import shared infrastructure
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from conftest import PlanContext, get_script_path, run_script

# Get script path
SCRIPT_PATH = get_script_path('pm-workflow', 'manage-assessments', 'manage-assessments.py')

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
            'add',
            '--plan-id', 'test-plan',
            '--file-path', 'marketplace/bundles/pm-dev-java/skills/java-cdi/SKILL.md',
            '--certainty', 'CERTAIN_INCLUDE',
            '--confidence', '95',
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
            'add',
            '--plan-id', 'test-plan',
            '--file-path', 'path/to/file.md',
            '--certainty', 'CERTAIN_EXCLUDE',
            '--confidence', '85',
            '--agent',
            'skill-analysis-agent',
            '--detail',
            'No relevant content found',
            '--evidence',
            'Checked ## Output section',
        )
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'


def test_assessment_add_uncertain():
    """Test adding an uncertain assessment."""
    with TestContext():
        result = run_script(
            SCRIPT_PATH,
            'add',
            '--plan-id', 'test-plan',
            '--file-path', 'path/to/ambiguous.md',
            '--certainty', 'UNCERTAIN',
            '--confidence', '65',
            '--detail',
            'JSON found in workflow context - unclear if output spec',
        )
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'


def test_assessment_add_invalid_certainty():
    """Test that invalid certainty is rejected."""
    with TestContext():
        result = run_script(
            SCRIPT_PATH, 'add', '--plan-id', 'test-plan',
            '--file-path', 'path/to/file.md',
            '--certainty', 'INVALID',
            '--confidence', '50'
        )
        # argparse should reject invalid choice
        assert not result.success


def test_assessment_add_invalid_confidence():
    """Test that out-of-range confidence is rejected."""
    with TestContext():
        result = run_script(
            SCRIPT_PATH, 'add', '--plan-id', 'test-plan',
            '--file-path', 'path/to/file.md',
            '--certainty', 'CERTAIN_INCLUDE',
            '--confidence', '150'
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
        result = run_script(SCRIPT_PATH, 'query', '--plan-id', 'test-plan')
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert data['total_count'] == 0


def test_assessment_query_all():
    """Test querying all assessments."""
    with TestContext():
        # Add some assessments
        run_script(SCRIPT_PATH, 'add', '--plan-id', 'test-plan', '--file-path', 'file1.md', '--certainty', 'CERTAIN_INCLUDE', '--confidence', '90')
        run_script(SCRIPT_PATH, 'add', '--plan-id', 'test-plan', '--file-path', 'file2.md', '--certainty', 'CERTAIN_EXCLUDE', '--confidence', '85')
        run_script(SCRIPT_PATH, 'add', '--plan-id', 'test-plan', '--file-path', 'file3.md', '--certainty', 'UNCERTAIN', '--confidence', '60')

        result = run_script(SCRIPT_PATH, 'query', '--plan-id', 'test-plan')
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['total_count'] == 3
        assert data['filtered_count'] == 3


def test_assessment_query_by_certainty():
    """Test filtering assessments by certainty."""
    with TestContext():
        run_script(SCRIPT_PATH, 'add', '--plan-id', 'test-plan', '--file-path', 'file1.md', '--certainty', 'CERTAIN_INCLUDE', '--confidence', '90')
        run_script(SCRIPT_PATH, 'add', '--plan-id', 'test-plan', '--file-path', 'file2.md', '--certainty', 'CERTAIN_EXCLUDE', '--confidence', '85')
        run_script(SCRIPT_PATH, 'add', '--plan-id', 'test-plan', '--file-path', 'file3.md', '--certainty', 'UNCERTAIN', '--confidence', '60')

        result = run_script(SCRIPT_PATH, 'query', '--plan-id', 'test-plan', '--certainty', 'CERTAIN_INCLUDE')
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['total_count'] == 3
        assert data['filtered_count'] == 1
        assert 'file1.md' in data.get('file_paths', [])


def test_assessment_query_by_confidence():
    """Test filtering assessments by confidence range."""
    with TestContext():
        run_script(SCRIPT_PATH, 'add', '--plan-id', 'test-plan', '--file-path', 'file1.md', '--certainty', 'CERTAIN_INCLUDE', '--confidence', '95')
        run_script(SCRIPT_PATH, 'add', '--plan-id', 'test-plan', '--file-path', 'file2.md', '--certainty', 'CERTAIN_INCLUDE', '--confidence', '85')
        run_script(SCRIPT_PATH, 'add', '--plan-id', 'test-plan', '--file-path', 'file3.md', '--certainty', 'CERTAIN_INCLUDE', '--confidence', '75')

        result = run_script(SCRIPT_PATH, 'query', '--plan-id', 'test-plan', '--min-confidence', '80')
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['filtered_count'] == 2


def test_assessment_query_file_paths_list():
    """Test that query returns file_paths list."""
    with TestContext():
        run_script(SCRIPT_PATH, 'add', '--plan-id', 'test-plan', '--file-path', 'path/a.md', '--certainty', 'CERTAIN_INCLUDE', '--confidence', '90')
        run_script(SCRIPT_PATH, 'add', '--plan-id', 'test-plan', '--file-path', 'path/b.md', '--certainty', 'CERTAIN_INCLUDE', '--confidence', '90')

        result = run_script(SCRIPT_PATH, 'query', '--plan-id', 'test-plan', '--certainty', 'CERTAIN_INCLUDE')
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
        run_script(SCRIPT_PATH, 'add', '--plan-id', 'test-plan', '--file-path', 'file1.md', '--certainty', 'CERTAIN_INCLUDE', '--confidence', '90')
        run_script(SCRIPT_PATH, 'add', '--plan-id', 'test-plan', '--file-path', 'file2.md', '--certainty', 'CERTAIN_EXCLUDE', '--confidence', '85')

        result = run_script(SCRIPT_PATH, 'clear', '--plan-id', 'test-plan')
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert data['cleared'] == 2

        # Verify empty
        query_result = run_script(SCRIPT_PATH, 'query', '--plan-id', 'test-plan')
        query_data = parse_toon(query_result.stdout)
        assert query_data['total_count'] == 0


def test_assessment_clear_by_agent():
    """Test clearing assessments filtered by agent name."""
    with TestContext():
        run_script(
            SCRIPT_PATH, 'add', '--plan-id', 'test-plan', '--file-path', 'file1.md', '--certainty', 'CERTAIN_INCLUDE', '--confidence', '90', '--agent', 'agent-a'
        )
        run_script(
            SCRIPT_PATH, 'add', '--plan-id', 'test-plan', '--file-path', 'file2.md', '--certainty', 'CERTAIN_EXCLUDE', '--confidence', '85', '--agent', 'agent-b'
        )
        run_script(
            SCRIPT_PATH, 'add', '--plan-id', 'test-plan', '--file-path', 'file3.md', '--certainty', 'CERTAIN_INCLUDE', '--confidence', '80', '--agent', 'agent-a'
        )

        result = run_script(SCRIPT_PATH, 'clear', '--plan-id', 'test-plan', '--agent', 'agent-a')
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert data['cleared'] == 2

        # Verify only agent-b remains
        query_result = run_script(SCRIPT_PATH, 'query', '--plan-id', 'test-plan')
        query_data = parse_toon(query_result.stdout)
        assert query_data['total_count'] == 1
        assert 'file2.md' in query_data.get('file_paths', [])


def test_assessment_clear_empty():
    """Test clearing when no assessments exist."""
    with TestContext():
        result = run_script(SCRIPT_PATH, 'clear', '--plan-id', 'test-plan')
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
        add_result = run_script(SCRIPT_PATH, 'add', '--plan-id', 'test-plan', '--file-path', 'file.md', '--certainty', 'CERTAIN_INCLUDE', '--confidence', '90')
        add_data = parse_toon(add_result.stdout)
        hash_id = str(add_data['hash_id'])  # Ensure string for subprocess args

        result = run_script(SCRIPT_PATH, 'get', '--plan-id', 'test-plan', '--hash-id', hash_id)
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert data['file_path'] == 'file.md'
        assert data['certainty'] == 'CERTAIN_INCLUDE'


def test_assessment_get_not_found():
    """Test getting non-existent assessment."""
    with TestContext():
        result = run_script(SCRIPT_PATH, 'get', '--plan-id', 'test-plan', '--hash-id', 'nonexistent')
        assert not result.success
