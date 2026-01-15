#!/usr/bin/env python3
"""Tests for system and plan commands in plan-marshall-config.

Tests system retention and plan defaults commands.
"""

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from test_helpers import SCRIPT_PATH, create_marshal_json

from conftest import PlanContext, run_script

# =============================================================================
# system Command Tests
# =============================================================================


def test_system_retention_get():
    """Test system retention get."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'system', 'retention', 'get')

        assert result.success, f'Should succeed: {result.stderr}'
        assert 'logs_days' in result.stdout
        assert '1' in result.stdout  # Default value


def test_system_retention_set():
    """Test system retention set."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'system', 'retention', 'set', '--field', 'logs_days', '--value', '7')

        assert result.success, f'Should succeed: {result.stderr}'

        # Verify changed
        verify = run_script(SCRIPT_PATH, 'system', 'retention', 'get')
        assert '7' in verify.stdout


def test_system_retention_set_boolean():
    """Test system retention set with boolean value."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(
            SCRIPT_PATH, 'system', 'retention', 'set', '--field', 'temp_on_maintenance', '--value', 'false'
        )

        assert result.success, f'Should succeed: {result.stderr}'

        # Verify changed
        verify = run_script(SCRIPT_PATH, 'system', 'retention', 'get')
        assert 'false' in verify.stdout.lower()


# =============================================================================
# plan Command Tests
# =============================================================================


def test_plan_defaults_list():
    """Test plan defaults list."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'plan', 'defaults', 'list')

        assert result.success, f'Should succeed: {result.stderr}'
        assert 'commit_strategy' in result.stdout
        assert 'phase-specific' in result.stdout


def test_plan_defaults_get():
    """Test plan defaults get."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'plan', 'defaults', 'get', '--field', 'commit_strategy')

        assert result.success, f'Should succeed: {result.stderr}'
        assert 'phase-specific' in result.stdout


def test_plan_defaults_get_all():
    """Test plan defaults get without field returns all defaults."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'plan', 'defaults', 'get')

        assert result.success, f'Should succeed: {result.stderr}'
        # Should return multiple fields
        assert 'commit_strategy' in result.stdout
        assert 'verification_required' in result.stdout


def test_plan_defaults_set():
    """Test plan defaults set."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'plan', 'defaults', 'set', '--field', 'create_pr', '--value', 'true')

        assert result.success, f'Should succeed: {result.stderr}'

        # Verify changed
        verify = run_script(SCRIPT_PATH, 'plan', 'defaults', 'get', '--field', 'create_pr')
        assert 'true' in verify.stdout.lower()


def test_plan_defaults_set_string():
    """Test plan defaults set with string value."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(
            SCRIPT_PATH, 'plan', 'defaults', 'set', '--field', 'branch_strategy', '--value', 'feature-branch'
        )

        assert result.success, f'Should succeed: {result.stderr}'

        # Verify changed
        verify = run_script(SCRIPT_PATH, 'plan', 'defaults', 'get', '--field', 'branch_strategy')
        assert 'feature-branch' in verify.stdout


def test_plan_defaults_get_unknown_field():
    """Test plan defaults get with unknown field returns error."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'plan', 'defaults', 'get', '--field', 'nonexistent')

        assert 'error' in result.stdout.lower(), 'Should report error'


# =============================================================================
# Main
# =============================================================================
