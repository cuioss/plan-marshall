#!/usr/bin/env python3
"""Tests for manage-assessments commands in manage-findings.py script.

Tier 2 (direct import) tests with 2-3 subprocess tests for CLI plumbing.
"""

import importlib.util
from argparse import Namespace
from pathlib import Path

from conftest import PlanContext, get_script_path, run_script

# Script path for remaining subprocess (CLI plumbing) tests
SCRIPT_PATH = get_script_path('plan-marshall', 'manage-findings', 'manage-findings.py')

# Import toon_parser - conftest sets up PYTHONPATH
from toon_parser import parse_toon  # type: ignore[import-not-found]  # noqa: E402

# Tier 2 direct imports - load hyphenated module via importlib
_MANAGE_FINDINGS_SCRIPT = str(
    Path(__file__).parent.parent.parent.parent
    / 'marketplace' / 'bundles' / 'plan-marshall' / 'skills' / 'manage-findings' / 'scripts' / 'manage-findings.py'
)
_spec = importlib.util.spec_from_file_location('manage_findings', _MANAGE_FINDINGS_SCRIPT)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

cmd_assessment_add = _mod.cmd_assessment_add
cmd_assessment_query = _mod.cmd_assessment_query
cmd_assessment_get = _mod.cmd_assessment_get
cmd_assessment_clear = _mod.cmd_assessment_clear


# =============================================================================
# Namespace Builders
# =============================================================================


def _add_ns(
    plan_id='test-plan',
    file_path='path/to/file.md',
    certainty='CERTAIN_INCLUDE',
    confidence=90,
    agent=None,
    detail=None,
    evidence=None,
):
    return Namespace(
        plan_id=plan_id,
        file_path=file_path,
        certainty=certainty,
        confidence=confidence,
        agent=agent,
        detail=detail,
        evidence=evidence,
    )


def _query_ns(plan_id='test-plan', certainty=None, min_confidence=None, max_confidence=None, file_pattern=None):
    return Namespace(
        plan_id=plan_id,
        certainty=certainty,
        min_confidence=min_confidence,
        max_confidence=max_confidence,
        file_pattern=file_pattern,
    )


def _get_ns(plan_id='test-plan', hash_id=''):
    return Namespace(plan_id=plan_id, hash_id=hash_id)


def _clear_ns(plan_id='test-plan', agent=None):
    return Namespace(plan_id=plan_id, agent=agent)


# =============================================================================
# Test: Assessment Add Command
# =============================================================================


def test_assessment_add_basic():
    """Test adding a basic assessment."""
    with PlanContext():
        result = cmd_assessment_add(_add_ns(
            file_path='marketplace/bundles/pm-dev-java/skills/java-cdi/SKILL.md',
            certainty='CERTAIN_INCLUDE',
            confidence=95,
        ))
        assert result['status'] == 'success'
        assert 'hash_id' in result
        assert result['file_path'] == 'marketplace/bundles/pm-dev-java/skills/java-cdi/SKILL.md'


def test_assessment_add_with_options():
    """Test adding assessment with all options."""
    with PlanContext():
        result = cmd_assessment_add(_add_ns(
            file_path='path/to/file.md',
            certainty='CERTAIN_EXCLUDE',
            confidence=85,
            agent='skill-analysis-agent',
            detail='No relevant content found',
            evidence='Checked ## Output section',
        ))
        assert result['status'] == 'success'


def test_assessment_add_uncertain():
    """Test adding an uncertain assessment."""
    with PlanContext():
        result = cmd_assessment_add(_add_ns(
            file_path='path/to/ambiguous.md',
            certainty='UNCERTAIN',
            confidence=65,
            detail='JSON found in workflow context - unclear if output spec',
        ))
        assert result['status'] == 'success'


def test_assessment_add_invalid_certainty():
    """Test that invalid certainty is rejected (CLI plumbing - subprocess)."""
    with PlanContext():
        result = run_script(
            SCRIPT_PATH,
            'assessment',
            'add',
            '--plan-id',
            'test-plan',
            '--file-path',
            'path/to/file.md',
            '--certainty',
            'INVALID',
            '--confidence',
            '50',
        )
        # argparse should reject invalid choice
        assert not result.success


def test_assessment_add_invalid_confidence():
    """Test that out-of-range confidence is rejected."""
    with PlanContext():
        result = cmd_assessment_add(_add_ns(
            file_path='path/to/file.md',
            certainty='CERTAIN_INCLUDE',
            confidence=150,
        ))
        assert result['status'] == 'error'


# =============================================================================
# Test: Assessment Query Command
# =============================================================================


def test_assessment_query_empty():
    """Test querying with no assessments."""
    with PlanContext():
        result = cmd_assessment_query(_query_ns())
        assert result['status'] == 'success'
        assert result['total_count'] == 0


def test_assessment_query_all():
    """Test querying all assessments."""
    with PlanContext():
        cmd_assessment_add(_add_ns(file_path='file1.md', certainty='CERTAIN_INCLUDE', confidence=90))
        cmd_assessment_add(_add_ns(file_path='file2.md', certainty='CERTAIN_EXCLUDE', confidence=85))
        cmd_assessment_add(_add_ns(file_path='file3.md', certainty='UNCERTAIN', confidence=60))

        result = cmd_assessment_query(_query_ns())
        assert result['total_count'] == 3
        assert result['filtered_count'] == 3


def test_assessment_query_by_certainty():
    """Test filtering assessments by certainty."""
    with PlanContext():
        cmd_assessment_add(_add_ns(file_path='file1.md', certainty='CERTAIN_INCLUDE', confidence=90))
        cmd_assessment_add(_add_ns(file_path='file2.md', certainty='CERTAIN_EXCLUDE', confidence=85))
        cmd_assessment_add(_add_ns(file_path='file3.md', certainty='UNCERTAIN', confidence=60))

        result = cmd_assessment_query(_query_ns(certainty='CERTAIN_INCLUDE'))
        assert result['total_count'] == 3
        assert result['filtered_count'] == 1
        assert 'file1.md' in result.get('file_paths', [])


def test_assessment_query_by_confidence():
    """Test filtering assessments by confidence range."""
    with PlanContext():
        cmd_assessment_add(_add_ns(file_path='file1.md', certainty='CERTAIN_INCLUDE', confidence=95))
        cmd_assessment_add(_add_ns(file_path='file2.md', certainty='CERTAIN_INCLUDE', confidence=85))
        cmd_assessment_add(_add_ns(file_path='file3.md', certainty='CERTAIN_INCLUDE', confidence=75))

        result = cmd_assessment_query(_query_ns(min_confidence=80))
        assert result['filtered_count'] == 2


def test_assessment_query_file_paths_list():
    """Test that query returns file_paths list."""
    with PlanContext():
        cmd_assessment_add(_add_ns(file_path='path/a.md', certainty='CERTAIN_INCLUDE', confidence=90))
        cmd_assessment_add(_add_ns(file_path='path/b.md', certainty='CERTAIN_INCLUDE', confidence=90))

        result = cmd_assessment_query(_query_ns(certainty='CERTAIN_INCLUDE'))
        assert 'file_paths' in result
        assert len(result['file_paths']) == 2


# =============================================================================
# Test: Assessment Clear Command
# =============================================================================


def test_assessment_clear_all():
    """Test clearing all assessments."""
    with PlanContext():
        cmd_assessment_add(_add_ns(file_path='file1.md', certainty='CERTAIN_INCLUDE', confidence=90))
        cmd_assessment_add(_add_ns(file_path='file2.md', certainty='CERTAIN_EXCLUDE', confidence=85))

        result = cmd_assessment_clear(_clear_ns())
        assert result['status'] == 'success'
        assert result['cleared'] == 2

        # Verify empty
        query_result = cmd_assessment_query(_query_ns())
        assert query_result['total_count'] == 0


def test_assessment_clear_by_agent():
    """Test clearing assessments filtered by agent name."""
    with PlanContext():
        cmd_assessment_add(_add_ns(file_path='file1.md', certainty='CERTAIN_INCLUDE', confidence=90, agent='agent-a'))
        cmd_assessment_add(_add_ns(file_path='file2.md', certainty='CERTAIN_EXCLUDE', confidence=85, agent='agent-b'))
        cmd_assessment_add(_add_ns(file_path='file3.md', certainty='CERTAIN_INCLUDE', confidence=80, agent='agent-a'))

        result = cmd_assessment_clear(_clear_ns(agent='agent-a'))
        assert result['status'] == 'success'
        assert result['cleared'] == 2

        # Verify only agent-b remains
        query_result = cmd_assessment_query(_query_ns())
        assert query_result['total_count'] == 1
        assert 'file2.md' in query_result.get('file_paths', [])


def test_assessment_clear_empty():
    """Test clearing when no assessments exist."""
    with PlanContext():
        result = cmd_assessment_clear(_clear_ns())
        assert result['status'] == 'success'
        assert result['cleared'] == 0


# =============================================================================
# Test: Assessment Get Command
# =============================================================================


def test_assessment_get():
    """Test getting a specific assessment."""
    with PlanContext():
        add_result = cmd_assessment_add(_add_ns(
            file_path='file.md',
            certainty='CERTAIN_INCLUDE',
            confidence=90,
        ))
        hash_id = str(add_result['hash_id'])

        result = cmd_assessment_get(_get_ns(hash_id=hash_id))
        assert result['status'] == 'success'
        assert result['file_path'] == 'file.md'
        assert result['certainty'] == 'CERTAIN_INCLUDE'


def test_assessment_get_not_found():
    """Test getting non-existent assessment."""
    with PlanContext():
        result = cmd_assessment_get(_get_ns(hash_id='nonexistent'))
        assert result['status'] == 'error'


# =============================================================================
# CLI Plumbing Tests (subprocess)
# =============================================================================


def test_cli_assessment_add_and_query_roundtrip():
    """CLI plumbing: add an assessment and query it back via subprocess."""
    with PlanContext():
        result = run_script(
            SCRIPT_PATH,
            'assessment',
            'add',
            '--plan-id',
            'test-plan',
            '--file-path',
            'cli-test.md',
            '--certainty',
            'CERTAIN_INCLUDE',
            '--confidence',
            '90',
        )
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'

        query_result = run_script(SCRIPT_PATH, 'assessment', 'query', '--plan-id', 'test-plan')
        assert query_result.success
        query_data = parse_toon(query_result.stdout)
        assert query_data['total_count'] == 1


def test_cli_assessment_clear_roundtrip():
    """CLI plumbing: add assessments and clear via subprocess."""
    with PlanContext():
        run_script(
            SCRIPT_PATH,
            'assessment',
            'add',
            '--plan-id',
            'test-plan',
            '--file-path',
            'cli-file1.md',
            '--certainty',
            'CERTAIN_INCLUDE',
            '--confidence',
            '90',
        )
        run_script(
            SCRIPT_PATH,
            'assessment',
            'add',
            '--plan-id',
            'test-plan',
            '--file-path',
            'cli-file2.md',
            '--certainty',
            'UNCERTAIN',
            '--confidence',
            '60',
        )

        clear_result = run_script(SCRIPT_PATH, 'assessment', 'clear', '--plan-id', 'test-plan')
        assert clear_result.success
        clear_data = parse_toon(clear_result.stdout)
        assert clear_data['cleared'] == 2
