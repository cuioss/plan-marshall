#!/usr/bin/env python3
"""Tests for quality phases commands in plan-marshall-config.

Tests verification and finalize pipeline commands including set-steps.
"""

import json

from test_helpers import SCRIPT_PATH, create_marshal_json

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import PlanContext, run_script

# =============================================================================
# verification Command Tests
# =============================================================================


def test_verification_get():
    """Test verification get returns pipeline config."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'verification', 'get')

        assert result.success, f'Should succeed: {result.stderr}'
        assert 'max_iterations' in result.stdout
        assert 'steps' in result.stdout


def test_verification_set_max_iterations():
    """Test verification set-max-iterations."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'verification', 'set-max-iterations', '--value', '10')

        assert result.success, f'Should succeed: {result.stderr}'

        # Verify changed
        verify = run_script(SCRIPT_PATH, 'verification', 'get')
        assert '10' in verify.stdout


def test_verification_set_steps_valid():
    """Test verification set-steps with valid step names."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(
            SCRIPT_PATH, 'verification', 'set-steps', '--steps', 'quality_check,build_verify'
        )

        assert result.success, f'Should succeed: {result.stderr}'
        assert 'quality_check' in result.stdout
        assert 'build_verify' in result.stdout

        # Verify saved by reading marshal.json directly
        config = json.loads((ctx.fixture_dir / 'marshal.json').read_text())
        steps = config['verification']['steps']
        assert len(steps) == 2
        assert steps[0]['name'] == 'quality_check'
        assert steps[1]['name'] == 'build_verify'


def test_verification_set_steps_unknown():
    """Test verification set-steps with unknown step name returns error."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(
            SCRIPT_PATH, 'verification', 'set-steps', '--steps', 'quality_check,nonexistent'
        )

        assert 'error' in result.stdout.lower(), 'Should report error for unknown step'
        assert 'nonexistent' in result.stdout


def test_verification_set_steps_preserves_order():
    """Test verification set-steps preserves default step order regardless of input order."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        # Provide in reverse order
        result = run_script(
            SCRIPT_PATH, 'verification', 'set-steps', '--steps', 'doc_sync,quality_check'
        )

        assert result.success, f'Should succeed: {result.stderr}'

        # Verify order matches defaults (quality_check before doc_sync)
        config = json.loads((ctx.fixture_dir / 'marshal.json').read_text())
        steps = config['verification']['steps']
        assert len(steps) == 2
        assert steps[0]['name'] == 'quality_check'
        assert steps[1]['name'] == 'doc_sync'


# =============================================================================
# finalize Command Tests
# =============================================================================


def test_finalize_get():
    """Test finalize get returns pipeline config."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'finalize', 'get')

        assert result.success, f'Should succeed: {result.stderr}'
        assert 'max_iterations' in result.stdout
        assert 'steps' in result.stdout


def test_finalize_set_steps_valid():
    """Test finalize set-steps with valid step names."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(
            SCRIPT_PATH, 'finalize', 'set-steps', '--steps', 'commit_push'
        )

        assert result.success, f'Should succeed: {result.stderr}'
        assert 'commit_push' in result.stdout

        # Verify saved by reading marshal.json directly
        config = json.loads((ctx.fixture_dir / 'marshal.json').read_text())
        steps = config['finalize']['steps']
        assert len(steps) == 1
        assert steps[0]['name'] == 'commit_push'


def test_finalize_set_steps_unknown():
    """Test finalize set-steps with unknown step name returns error."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(
            SCRIPT_PATH, 'finalize', 'set-steps', '--steps', 'commit_push,bogus'
        )

        assert 'error' in result.stdout.lower(), 'Should report error for unknown step'
        assert 'bogus' in result.stdout


# =============================================================================
# Main
# =============================================================================
