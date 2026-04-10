#!/usr/bin/env python3
"""Tests for ci_health.py script.

Tests provider detection, tool verification, and configuration persistence.

Tier 2 (direct import) tests for cmd_* functions.
Tier 3 (subprocess) tests retained for CLI plumbing and persist (marshal.json I/O).
"""

import json
from argparse import Namespace

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import PlanContext, get_script_path, run_script

# Script path for remaining subprocess (CLI plumbing) tests
SCRIPT_PATH = get_script_path('plan-marshall', 'tools-integration-ci', 'ci_health.py')

# Tier 2 direct imports
from ci_health import cmd_detect, cmd_status, cmd_verify  # type: ignore[import-not-found]  # noqa: E402

# =============================================================================
# Tier 2: Direct import tests for cmd_detect
# =============================================================================


def test_detect_returns_success():
    """Test detect command returns valid output via direct import."""
    result = cmd_detect(Namespace())
    assert result['status'] == 'success'
    assert 'provider' in result
    assert result['provider'] in ('github', 'gitlab', 'unknown')
    assert 'confidence' in result


def test_detect_includes_repo_url():
    """Test detect output includes repo_url field."""
    result = cmd_detect(Namespace())
    assert 'repo_url' in result


# =============================================================================
# Tier 2: Direct import tests for cmd_verify
# =============================================================================


def test_verify_all_tools():
    """Test verify command checks all tools via direct import."""
    result = cmd_verify(Namespace(tool=None))
    assert result['status'] == 'success'
    assert 'tools' in result
    # Should have git at minimum
    assert 'git' in result['tools']
    assert 'installed' in result['tools']['git']


def test_verify_specific_tool_git():
    """Test verify command for specific tool via direct import."""
    result = cmd_verify(Namespace(tool='git'))
    assert result['status'] == 'success'
    assert 'tools' in result
    assert 'git' in result['tools']


def test_verify_unknown_tool():
    """Test verify command with unknown tool returns error via direct import."""
    result = cmd_verify(Namespace(tool='unknown_tool_xyz'))
    assert result['status'] == 'error'
    assert 'error' in result


# =============================================================================
# Tier 2: Direct import tests for cmd_status
# =============================================================================


def test_status_returns_comprehensive_output():
    """Test status command returns comprehensive output via direct import."""
    result = cmd_status(Namespace())
    assert result['status'] == 'success'
    assert 'provider' in result
    assert 'tools' in result
    assert 'overall' in result
    assert result['overall'] in ('healthy', 'degraded', 'unknown')


# =============================================================================
# Tier 3: Subprocess tests for CLI plumbing
# =============================================================================


def test_help_flag():
    """Test --help flag works."""
    result = run_script(SCRIPT_PATH, '--help')
    assert result.success, f'--help failed: {result.stderr}'
    assert 'detect' in result.stdout
    assert 'verify' in result.stdout
    assert 'status' in result.stdout
    assert 'persist' in result.stdout


def test_detect_cli_output():
    """Test detect subcommand produces valid TOON via subprocess."""
    result = run_script(SCRIPT_PATH, 'detect')
    assert result.success, f'Script failed: {result.stderr}'
    data = result.toon()
    assert data['status'] == 'success'


def test_verify_cli_output():
    """Test verify subcommand produces valid TOON via subprocess."""
    result = run_script(SCRIPT_PATH, 'verify')
    assert result.success, f'Script failed: {result.stderr}'
    data = result.toon()
    assert data['status'] == 'success'


# =============================================================================
# Tier 3: Subprocess tests for persist (requires marshal.json I/O)
# =============================================================================


def test_persist_no_marshal_json():
    """Test persist command fails without marshal.json."""
    with PlanContext(plan_id='test-persist') as ctx:
        result = run_script(SCRIPT_PATH, 'persist', '--plan-dir', str(ctx.fixture_dir))
        assert result.success, 'Expected exit 0 (error in TOON output)'
        data = result.toon_or_error()
        assert data.get('status') != 'success', 'Expected error status in TOON output'
        assert 'error' in data


def test_persist_with_marshal_json():
    """Test persist command succeeds with marshal.json containing providers."""
    with PlanContext(plan_id='test-persist-success') as ctx:
        # Create marshal.json with a CI provider entry in providers list
        marshal_path = ctx.fixture_dir / 'marshal.json'
        marshal_path.write_text(json.dumps({
            'version': 1,
            'providers': [{
                'skill_name': 'workflow-integration-github',
                'auth_type': 'system',
                'default_url': 'https://github.com',
            }],
        }))

        result = run_script(SCRIPT_PATH, 'persist', '--plan-dir', str(ctx.fixture_dir))
        assert result.success, f'Script failed: {result.stderr}'

        # Verify marshal.json providers entry was updated
        updated = json.loads(marshal_path.read_text())
        assert 'providers' in updated
        ci_entry = next(
            (p for p in updated['providers']
             if p.get('skill_name', '').startswith('workflow-integration-gi')),
            None,
        )
        assert ci_entry is not None
        assert 'provider' in ci_entry


def test_persist_stores_provider_only():
    """Test persist stores provider and repo_url on providers entry."""
    with PlanContext(plan_id='test-commands') as ctx:
        # Create marshal.json with a CI provider entry
        marshal_path = ctx.fixture_dir / 'marshal.json'
        marshal_path.write_text(json.dumps({
            'version': 1,
            'providers': [{
                'skill_name': 'workflow-integration-github',
                'auth_type': 'system',
                'default_url': 'https://github.com',
            }],
        }))

        result = run_script(SCRIPT_PATH, 'persist', '--plan-dir', str(ctx.fixture_dir))
        assert result.success, f'Script failed: {result.stderr}'

        updated = json.loads(marshal_path.read_text())
        ci_entry = next(
            (p for p in updated['providers']
             if p.get('skill_name', '').startswith('workflow-integration-gi')),
            None,
        )
        assert ci_entry is not None
        assert 'provider' in ci_entry
        assert 'detected_at' in ci_entry


def test_persist_key_ordering():
    """Test persist maintains canonical key ordering in marshal.json.

    Canonical order: plan, providers, skill_domains, system
    """
    with PlanContext(plan_id='test-ordering') as ctx:
        # Create marshal.json with keys in WRONG order and a CI provider
        marshal_path = ctx.fixture_dir / 'marshal.json'
        marshal_path.write_text(
            json.dumps(
                {
                    'system': {'retention': {}},
                    'plan': {'defaults': {}},
                    'skill_domains': {'system': {}},
                    'providers': [{
                        'skill_name': 'workflow-integration-github',
                        'auth_type': 'system',
                        'default_url': 'https://github.com',
                    }],
                },
                indent=2,
            )
        )

        result = run_script(SCRIPT_PATH, 'persist', '--plan-dir', str(ctx.fixture_dir))
        assert result.success, f'Script failed: {result.stderr}'

        # Verify key ordering
        updated = json.loads(marshal_path.read_text())
        actual_keys = list(updated.keys())

        # Expected canonical order (no ci key — data lives in providers)
        expected_order = ['plan', 'providers', 'skill_domains', 'system']

        # Filter to only keys that exist
        actual_order = [k for k in actual_keys if k in expected_order]
        expected_filtered = [k for k in expected_order if k in actual_keys]

        assert actual_order == expected_filtered, f'Key order should be {expected_filtered}, got {actual_order}'
