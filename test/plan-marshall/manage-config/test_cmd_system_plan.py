#!/usr/bin/env python3
"""Tests for system commands in manage-config.

Tests system retention commands. Plan phase commands are tested in
test_cmd_quality_phases.py.

Tier 2 (direct import) tests with 2 subprocess tests for CLI plumbing.
"""

from argparse import Namespace

# Tier 2 direct imports
from _cmd_system_plan import cmd_system

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from test_helpers import SCRIPT_PATH, create_marshal_json, patch_config_paths

from conftest import PlanContext, run_script

# =============================================================================
# system Command Tests (Tier 2 - direct import)
# =============================================================================


def test_system_retention_get():
    """Test system retention get."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_system(Namespace(sub_noun='retention', verb='get'))

        assert result['status'] == 'success'
        assert 'retention' in result
        assert result['retention']['logs_days'] == 1


def test_system_retention_set():
    """Test system retention set."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_system(Namespace(sub_noun='retention', verb='set', field='logs_days', value='7'))

        assert result['status'] == 'success'
        assert result['field'] == 'logs_days'
        assert result['value'] == 7

        # Verify changed via another get
        verify = cmd_system(Namespace(sub_noun='retention', verb='get'))
        assert verify['retention']['logs_days'] == 7


def test_system_retention_set_boolean():
    """Test system retention set with boolean value."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_system(
            Namespace(sub_noun='retention', verb='set', field='temp_on_maintenance', value='false')
        )

        assert result['status'] == 'success'
        assert result['value'] is False

        # Verify changed
        verify = cmd_system(Namespace(sub_noun='retention', verb='get'))
        assert verify['retention']['temp_on_maintenance'] is False


# =============================================================================
# CLI Plumbing Tests (Tier 3 - subprocess)
# =============================================================================


def test_cli_system_retention_get():
    """Test CLI plumbing: system retention get outputs TOON."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'system', 'retention', 'get')

        assert result.success, f'Should succeed: {result.stderr}'
        assert 'logs_days' in result.stdout


def test_cli_system_retention_set():
    """Test CLI plumbing: system retention set outputs TOON."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'system', 'retention', 'set', '--field', 'logs_days', '--value', '7')

        assert result.success, f'Should succeed: {result.stderr}'


# =============================================================================
# Main
# =============================================================================
