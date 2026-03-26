#!/usr/bin/env python3
"""Tests for ci_health.py script.

Tests provider detection, tool verification, and configuration persistence.
"""

import json

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import PlanContext, get_script_path, run_script

# Get script path
SCRIPT_PATH = get_script_path('plan-marshall', 'tools-integration-ci', 'ci_health.py')


def test_detect_success():
    """Test detect command returns valid output."""
    result = run_script(SCRIPT_PATH, 'detect')
    assert result.success, f'Script failed: {result.stderr}'
    data = result.json()
    assert 'status' in data
    assert data['status'] == 'success'
    assert 'provider' in data
    assert data['provider'] in ('github', 'gitlab', 'unknown')
    assert 'confidence' in data


def test_verify_all_tools():
    """Test verify command checks all tools."""
    result = run_script(SCRIPT_PATH, 'verify')
    assert result.success, f'Script failed: {result.stderr}'
    data = result.json()
    assert data['status'] == 'success'
    assert 'tools' in data
    # Should have git at minimum
    assert 'git' in data['tools']
    assert 'installed' in data['tools']['git']


def test_verify_specific_tool():
    """Test verify command for specific tool."""
    result = run_script(SCRIPT_PATH, 'verify', '--tool', 'git')
    assert result.success, f'Script failed: {result.stderr}'
    data = result.json()
    assert data['status'] == 'success'
    assert 'tools' in data
    assert 'git' in data['tools']


def test_verify_unknown_tool():
    """Test verify command with unknown tool returns error."""
    result = run_script(SCRIPT_PATH, 'verify', '--tool', 'unknown_tool_xyz')
    assert not result.success, 'Expected script to fail for unknown tool'
    data = result.json_or_error()
    assert 'error' in data


def test_status_success():
    """Test status command returns comprehensive output."""
    result = run_script(SCRIPT_PATH, 'status')
    assert result.success, f'Script failed: {result.stderr}'
    data = result.json()
    assert data['status'] == 'success'
    assert 'provider' in data
    assert 'tools' in data
    assert 'overall' in data
    assert data['overall'] in ('healthy', 'degraded', 'unknown')


def test_persist_no_marshal_json():
    """Test persist command fails without marshal.json."""
    with PlanContext(plan_id='test-persist') as ctx:
        result = run_script(SCRIPT_PATH, 'persist', '--plan-dir', str(ctx.fixture_dir))
        assert not result.success, 'Expected script to fail without marshal.json'
        data = result.json_or_error()
        assert 'error' in data


def test_persist_with_marshal_json():
    """Test persist command succeeds with marshal.json."""
    with PlanContext(plan_id='test-persist-success') as ctx:
        # Create minimal marshal.json
        marshal_path = ctx.fixture_dir / 'marshal.json'
        marshal_path.write_text('{"version": 1}')

        result = run_script(SCRIPT_PATH, 'persist', '--plan-dir', str(ctx.fixture_dir))
        assert result.success, f'Script failed: {result.stderr}'

        # Verify marshal.json was updated
        updated = json.loads(marshal_path.read_text())
        assert 'ci' in updated
        assert 'provider' in updated['ci']
        # ci.commands should NOT be stored — the ci.py router resolves at runtime
        assert 'commands' not in updated['ci']


def test_persist_stores_provider_only():
    """Test persist stores provider and repo_url, not commands."""
    with PlanContext(plan_id='test-commands') as ctx:
        # Create minimal marshal.json
        marshal_path = ctx.fixture_dir / 'marshal.json'
        marshal_path.write_text('{"version": 1}')

        result = run_script(SCRIPT_PATH, 'persist', '--plan-dir', str(ctx.fixture_dir))
        assert result.success, f'Script failed: {result.stderr}'

        updated = json.loads(marshal_path.read_text())
        assert 'ci' in updated
        assert 'provider' in updated['ci']
        assert 'detected_at' in updated['ci']
        # No commands stored — router handles resolution
        assert 'commands' not in updated['ci']


def test_help_flag():
    """Test --help flag works."""
    result = run_script(SCRIPT_PATH, '--help')
    assert result.success, f'--help failed: {result.stderr}'
    assert 'detect' in result.stdout
    assert 'verify' in result.stdout
    assert 'status' in result.stdout
    assert 'persist' in result.stdout


def test_persist_key_ordering():
    """Test persist maintains canonical key ordering in marshal.json.

    Canonical order: ci, plan, skill_domains, system
    """
    with PlanContext(plan_id='test-ordering') as ctx:
        # Create marshal.json with keys in WRONG order
        marshal_path = ctx.fixture_dir / 'marshal.json'
        marshal_path.write_text(
            json.dumps(
                {
                    'system': {'retention': {}},
                    'plan': {'defaults': {}},
                    'skill_domains': {'system': {}},
                },
                indent=2,
            )
        )

        result = run_script(SCRIPT_PATH, 'persist', '--plan-dir', str(ctx.fixture_dir))
        assert result.success, f'Script failed: {result.stderr}'

        # Verify key ordering
        updated = json.loads(marshal_path.read_text())
        actual_keys = list(updated.keys())

        # Expected order (ci should be first since persist adds it)
        expected_order = ['ci', 'plan', 'skill_domains', 'system']

        # Filter to only keys that exist
        actual_order = [k for k in actual_keys if k in expected_order]
        expected_filtered = [k for k in expected_order if k in actual_keys]

        assert actual_order == expected_filtered, f'Key order should be {expected_filtered}, got {actual_order}'
