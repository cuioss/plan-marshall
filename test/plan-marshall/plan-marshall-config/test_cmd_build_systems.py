#!/usr/bin/env python3
"""Tests for build-systems command in plan-marshall-config.

Tests build-systems command variants and edge cases.

NOTE: Build systems are defined statically in BUILD_SYSTEM_DEFAULTS.
They are not persisted in marshal.json - that key was removed.
Commands are stored per-module, not globally.
"""

import sys
from pathlib import Path

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import run_script, TestRunner, PlanTestContext
from test_helpers import SCRIPT_PATH, create_marshal_json


# =============================================================================
# build-systems Command Tests
# =============================================================================

def test_build_systems_list():
    """Test build-systems list returns static defaults."""
    with PlanTestContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'build-systems', 'list')

        assert result.success, f"Should succeed: {result.stderr}"
        # Returns all BUILD_SYSTEM_DEFAULTS (maven, gradle, npm)
        assert 'maven' in result.stdout.lower()
        assert 'gradle' in result.stdout.lower()
        assert 'npm' in result.stdout.lower()


def test_build_systems_get():
    """Test build-systems get returns static defaults."""
    with PlanTestContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'build-systems', 'get', '--system', 'maven')

        assert result.success, f"Should succeed: {result.stderr}"
        # Build systems reference domain-specific extension plugins
        assert 'pm-dev-java:plan-marshall-plugin' in result.stdout


def test_build_systems_add_not_supported():
    """Test build-systems add returns error (static config)."""
    with PlanTestContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        # Try to add a new build system
        result = run_script(SCRIPT_PATH, 'build-systems', 'add', '--system', 'cargo')

        # Should fail - can't add to static defaults
        assert 'error' in result.stdout.lower()
        assert 'cannot add' in result.stdout.lower() or 'BUILD_SYSTEM_DEFAULTS' in result.stdout


def test_build_systems_remove_not_supported():
    """Test build-systems remove returns error (static config)."""
    with PlanTestContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'build-systems', 'remove', '--system', 'npm')

        # Should fail - can't remove from static defaults
        assert 'error' in result.stdout.lower()
        assert 'cannot remove' in result.stdout.lower() or 'BUILD_SYSTEM_DEFAULTS' in result.stdout


def test_build_systems_get_unknown():
    """Test build-systems get with unknown system returns error."""
    with PlanTestContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'build-systems', 'get', '--system', 'unknown')

        assert 'error' in result.stdout.lower(), "Should report error"


def test_build_systems_add_existing():
    """Test build-systems add for existing system returns error."""
    with PlanTestContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'build-systems', 'add', '--system', 'maven')

        # Should fail - maven already in defaults
        assert 'error' in result.stdout.lower() or 'exists' in result.stdout.lower()


def test_build_systems_detect():
    """Test build-systems detect returns detected systems."""
    with PlanTestContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'build-systems', 'detect')

        assert result.success, f"Should succeed: {result.stderr}"
        # Should include note about module-level configuration
        assert 'detected' in result.stdout.lower()


# =============================================================================
# Main
# =============================================================================

if __name__ == '__main__':
    runner = TestRunner()
    runner.add_tests([
        test_build_systems_list,
        test_build_systems_get,
        test_build_systems_add_not_supported,
        test_build_systems_remove_not_supported,
        test_build_systems_get_unknown,
        test_build_systems_add_existing,
        test_build_systems_detect,
    ])
    sys.exit(runner.run())
