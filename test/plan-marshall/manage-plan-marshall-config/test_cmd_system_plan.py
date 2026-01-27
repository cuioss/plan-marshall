#!/usr/bin/env python3
"""Tests for system commands in plan-marshall-config.

Tests system retention commands. Plan phase commands are tested in
test_cmd_quality_phases.py.
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
# Main
# =============================================================================
