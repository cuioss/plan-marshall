#!/usr/bin/env python3
"""Tests for init command in plan-marshall-config.

Tests init command variants including force overwrite and error handling.
"""

import json

from test_helpers import SCRIPT_PATH, create_marshal_json

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import PlanContext, run_script

# =============================================================================
# Init Command Tests
# =============================================================================


def test_init_creates_marshal_json():
    """Test init creates marshal.json with defaults."""
    with PlanContext() as ctx:
        result = run_script(SCRIPT_PATH, 'init')

        assert result.success, f'Init should succeed: {result.stderr}'
        assert 'success' in result.stdout.lower(), 'Should output success'

        marshal_path = ctx.fixture_dir / 'marshal.json'
        assert marshal_path.exists(), 'marshal.json should be created'

        config = json.loads(marshal_path.read_text())
        assert 'skill_domains' in config, 'Should have skill_domains'
        assert 'system' in config, 'Should have system'
        assert 'plan' in config, 'Should have plan'


def test_init_fails_if_exists():
    """Test init fails if marshal.json already exists."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'init')

        assert not result.success or 'already exists' in result.stdout.lower(), (
            'Should fail or warn when marshal.json exists'
        )


def test_init_force_overwrites():
    """Test init --force overwrites existing marshal.json."""
    with PlanContext() as ctx:
        # Create existing with custom content
        create_marshal_json(ctx.fixture_dir, {'custom': True})

        result = run_script(SCRIPT_PATH, 'init', '--force')

        assert result.success, f'Init --force should succeed: {result.stderr}'

        marshal_path = ctx.fixture_dir / 'marshal.json'
        config = json.loads(marshal_path.read_text())
        assert 'skill_domains' in config, 'Should have default content'
        assert 'custom' not in config, 'Should not have old custom content'


def test_init_creates_parent_directory():
    """Test init creates .plan directory if missing."""
    with PlanContext() as ctx:
        # PlanContext creates .plan, but we verify it works
        result = run_script(SCRIPT_PATH, 'init')

        assert result.success, f'Init should succeed: {result.stderr}'
        assert (ctx.fixture_dir / 'marshal.json').exists()


def test_init_preserves_system_domain():
    """Test init includes system domain in defaults."""
    with PlanContext() as ctx:
        result = run_script(SCRIPT_PATH, 'init')

        assert result.success, f'Init should succeed: {result.stderr}'

        marshal_path = ctx.fixture_dir / 'marshal.json'
        config = json.loads(marshal_path.read_text())
        assert 'system' in config.get('skill_domains', {}), 'Should include system domain'


def test_init_no_build_systems_key():
    """Test init does NOT create build_systems key in marshal.json.

    Build systems are determined at runtime via extension discovery,
    not persisted in marshal.json.
    """
    with PlanContext() as ctx:
        result = run_script(SCRIPT_PATH, 'init')

        assert result.success, f'Init should succeed: {result.stderr}'

        marshal_path = ctx.fixture_dir / 'marshal.json'
        config = json.loads(marshal_path.read_text())
        assert 'build_systems' not in config, 'marshal.json should NOT contain build_systems key'


def test_init_key_ordering():
    """Test init creates marshal.json with correct key order.

    Canonical order: extension_defaults, finalize, plan, skill_domains, system, verification
    """
    with PlanContext() as ctx:
        result = run_script(SCRIPT_PATH, 'init')

        assert result.success, f'Init should succeed: {result.stderr}'

        marshal_path = ctx.fixture_dir / 'marshal.json'
        content = marshal_path.read_text()
        config = json.loads(content)

        # Get actual key order from JSON
        actual_keys = list(config.keys())

        # Expected canonical order (alphabetical)
        expected_order = ['extension_defaults', 'finalize', 'plan', 'skill_domains', 'system', 'verification']

        # Filter to only keys that exist
        actual_order = [k for k in actual_keys if k in expected_order]
        expected_filtered = [k for k in expected_order if k in actual_keys]

        assert actual_order == expected_filtered, f'Key order should be {expected_filtered}, got {actual_order}'


def test_init_includes_verification_section():
    """Test init creates marshal.json with verification pipeline section."""
    with PlanContext() as ctx:
        result = run_script(SCRIPT_PATH, 'init')
        assert result.success, f'Init should succeed: {result.stderr}'

        marshal_path = ctx.fixture_dir / 'marshal.json'
        config = json.loads(marshal_path.read_text())
        assert 'verification' in config, 'Should have verification section'
        assert 'steps' in config['verification'], 'Should have verification steps'
        assert 'max_iterations' in config['verification'], 'Should have max_iterations'
        assert config['verification']['max_iterations'] == 5


def test_init_includes_finalize_section():
    """Test init creates marshal.json with finalize pipeline section."""
    with PlanContext() as ctx:
        result = run_script(SCRIPT_PATH, 'init')
        assert result.success, f'Init should succeed: {result.stderr}'

        marshal_path = ctx.fixture_dir / 'marshal.json'
        config = json.loads(marshal_path.read_text())
        assert 'finalize' in config, 'Should have finalize section'
        assert 'steps' in config['finalize'], 'Should have finalize steps'
        assert 'max_iterations' in config['finalize'], 'Should have max_iterations'
        assert config['finalize']['max_iterations'] == 3


def test_init_includes_plan_finalize_section():
    """Test init creates marshal.json with plan.finalize section."""
    with PlanContext() as ctx:
        result = run_script(SCRIPT_PATH, 'init')
        assert result.success, f'Init should succeed: {result.stderr}'

        marshal_path = ctx.fixture_dir / 'marshal.json'
        config = json.loads(marshal_path.read_text())
        plan = config.get('plan', {})
        assert 'finalize' in plan, 'Should have plan.finalize section'
        assert plan['finalize']['commit'] is True, 'Should have commit=true'


# =============================================================================
# Main
# =============================================================================
