#!/usr/bin/env python3
"""Tests for system commands in manage-config.

Tests system retention commands. Plan phase commands are tested in
test_cmd_quality_phases.py.

Tier 2 (direct import) tests with 2 subprocess tests for CLI plumbing.
"""

import importlib.util
import sys
from argparse import Namespace
from pathlib import Path

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from test_helpers import SCRIPT_PATH, create_marshal_json, patch_config_paths

_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace' / 'bundles' / 'plan-marshall' / 'skills' / 'manage-config' / 'scripts'
)


def _load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_cmd_system_plan = _load_module('_cmd_system_plan', '_cmd_system_plan.py')

cmd_system = _cmd_system_plan.cmd_system

from conftest import PlanContext, run_script  # noqa: E402

# =============================================================================
# system Command Tests (Tier 2 - direct import)
# =============================================================================


def test_system_retention_get(monkeypatch):
    """Test system retention get."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)
        patch_config_paths(monkeypatch, ctx.fixture_dir)

        result = cmd_system(Namespace(sub_noun='retention', verb='get'))

        assert result['status'] == 'success'
        assert 'retention' in result
        assert result['retention']['logs_days'] == 1


def test_system_retention_set(monkeypatch):
    """Test system retention set."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)
        patch_config_paths(monkeypatch, ctx.fixture_dir)

        result = cmd_system(Namespace(sub_noun='retention', verb='set', field='logs_days', value='7'))

        assert result['status'] == 'success'
        assert result['field'] == 'logs_days'
        assert result['value'] == 7

        # Verify changed via another get
        verify = cmd_system(Namespace(sub_noun='retention', verb='get'))
        assert verify['retention']['logs_days'] == 7


def test_system_retention_set_boolean(monkeypatch):
    """Test system retention set with boolean value."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)
        patch_config_paths(monkeypatch, ctx.fixture_dir)

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
