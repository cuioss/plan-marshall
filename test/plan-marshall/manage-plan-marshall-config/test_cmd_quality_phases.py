#!/usr/bin/env python3
"""Tests for phase-based plan commands in plan-marshall-config.

Tests plan phase-6-verify and plan phase-7-finalize pipeline commands,
as well as scalar phase commands (phase-1-init, phase-2-refine, phase-5-execute).
"""

import json

from test_helpers import SCRIPT_PATH, create_marshal_json

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import PlanContext, run_script

# =============================================================================
# phase-6-verify Command Tests
# =============================================================================


def test_verify_get():
    """Test plan phase-6-verify get returns pipeline config."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'plan', 'phase-6-verify', 'get')

        assert result.success, f'Should succeed: {result.stderr}'
        assert 'max_iterations' in result.stdout
        assert '1_quality_check' in result.stdout


def test_verify_set_max_iterations():
    """Test plan phase-6-verify set-max-iterations."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'plan', 'phase-6-verify', 'set-max-iterations', '--value', '10')

        assert result.success, f'Should succeed: {result.stderr}'

        # Verify changed
        config = json.loads((ctx.fixture_dir / 'marshal.json').read_text())
        assert config['plan']['phase-6-verify']['max_iterations'] == 10


def test_verify_set_step_disable():
    """Test plan phase-6-verify set-step to disable a boolean step."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(
            SCRIPT_PATH, 'plan', 'phase-6-verify', 'set-step',
            '--step', '1_quality_check', '--enabled', 'false'
        )

        assert result.success, f'Should succeed: {result.stderr}'

        # Verify saved
        config = json.loads((ctx.fixture_dir / 'marshal.json').read_text())
        assert config['plan']['phase-6-verify']['1_quality_check'] is False


def test_verify_set_step_unknown():
    """Test plan phase-6-verify set-step with unknown step returns error."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(
            SCRIPT_PATH, 'plan', 'phase-6-verify', 'set-step',
            '--step', 'nonexistent', '--enabled', 'true'
        )

        assert 'error' in result.stdout.lower(), 'Should report error for unknown step'
        assert 'nonexistent' in result.stdout


def test_verify_get_field():
    """Test plan phase-6-verify get --field returns specific field."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'plan', 'phase-6-verify', 'get', '--field', 'max_iterations')

        assert result.success, f'Should succeed: {result.stderr}'
        assert '5' in result.stdout


def test_verify_set_domain_step_agent():
    """Test plan phase-6-verify set-domain-step-agent to set a domain step."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(
            SCRIPT_PATH, 'plan', 'phase-6-verify', 'set-domain-step-agent',
            '--domain', 'java', '--step', '1_technical_impl', '--agent', 'pm-dev-java:java-verify-agent'
        )

        assert result.success, f'Should succeed: {result.stderr}'

        # Verify saved
        config = json.loads((ctx.fixture_dir / 'marshal.json').read_text())
        domain_steps = config['plan']['phase-6-verify']['domain_steps']
        assert 'java' in domain_steps
        assert domain_steps['java']['1_technical_impl'] == 'pm-dev-java:java-verify-agent'


def test_verify_set_domain_step_disable():
    """Test plan phase-6-verify set-domain-step to disable a domain step."""
    with PlanContext() as ctx:
        # Create config with a domain step already set
        config = {
            'skill_domains': {'system': {}},
            'system': {'retention': {}},
            'plan': {
                'phase-6-verify': {
                    'max_iterations': 5,
                    '1_quality_check': True,
                    '2_build_verify': True,
                    'domain_steps': {
                        'java': {
                            '1_technical_impl': 'pm-dev-java:java-verify-agent',
                        }
                    },
                },
                'phase-7-finalize': {'max_iterations': 3, '1_commit_push': True},
            },
        }
        create_marshal_json(ctx.fixture_dir, config)

        result = run_script(
            SCRIPT_PATH, 'plan', 'phase-6-verify', 'set-domain-step',
            '--domain', 'java', '--step', '1_technical_impl', '--enabled', 'false'
        )

        assert result.success, f'Should succeed: {result.stderr}'

        # Verify saved as false
        saved = json.loads((ctx.fixture_dir / 'marshal.json').read_text())
        assert saved['plan']['phase-6-verify']['domain_steps']['java']['1_technical_impl'] is False


def test_verify_set_domain_step_unknown_domain():
    """Test plan phase-6-verify set-domain-step with unknown domain returns error."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(
            SCRIPT_PATH, 'plan', 'phase-6-verify', 'set-domain-step',
            '--domain', 'nonexistent', '--step', '1_foo', '--enabled', 'false'
        )

        assert 'error' in result.stdout.lower(), 'Should report error for unknown domain'


# =============================================================================
# phase-7-finalize Command Tests
# =============================================================================


def test_finalize_get():
    """Test plan phase-7-finalize get returns pipeline config."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'plan', 'phase-7-finalize', 'get')

        assert result.success, f'Should succeed: {result.stderr}'
        assert 'max_iterations' in result.stdout
        assert '1_commit_push' in result.stdout


def test_finalize_set_step_disable():
    """Test plan phase-7-finalize set-step to disable a boolean step."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(
            SCRIPT_PATH, 'plan', 'phase-7-finalize', 'set-step',
            '--step', '2_create_pr', '--enabled', 'false'
        )

        assert result.success, f'Should succeed: {result.stderr}'

        # Verify saved
        config = json.loads((ctx.fixture_dir / 'marshal.json').read_text())
        assert config['plan']['phase-7-finalize']['2_create_pr'] is False


def test_finalize_set_step_unknown():
    """Test plan phase-7-finalize set-step with unknown step returns error."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(
            SCRIPT_PATH, 'plan', 'phase-7-finalize', 'set-step',
            '--step', 'bogus', '--enabled', 'true'
        )

        assert 'error' in result.stdout.lower(), 'Should report error for unknown step'
        assert 'bogus' in result.stdout


def test_finalize_set_max_iterations():
    """Test plan phase-7-finalize set-max-iterations."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'plan', 'phase-7-finalize', 'set-max-iterations', '--value', '7')

        assert result.success, f'Should succeed: {result.stderr}'

        config = json.loads((ctx.fixture_dir / 'marshal.json').read_text())
        assert config['plan']['phase-7-finalize']['max_iterations'] == 7


# =============================================================================
# Scalar Phase Command Tests
# =============================================================================


def test_phase_1_init_get():
    """Test plan phase-1-init get returns config."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'plan', 'phase-1-init', 'get')

        assert result.success, f'Should succeed: {result.stderr}'
        assert 'branch_strategy' in result.stdout


def test_phase_1_init_set():
    """Test plan phase-1-init set updates a field."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(
            SCRIPT_PATH, 'plan', 'phase-1-init', 'set',
            '--field', 'branch_strategy', '--value', 'feature-branch'
        )

        assert result.success, f'Should succeed: {result.stderr}'

        config = json.loads((ctx.fixture_dir / 'marshal.json').read_text())
        assert config['plan']['phase-1-init']['branch_strategy'] == 'feature-branch'


def test_phase_2_refine_get():
    """Test plan phase-2-refine get returns config."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'plan', 'phase-2-refine', 'get')

        assert result.success, f'Should succeed: {result.stderr}'
        assert 'confidence_threshold' in result.stdout


def test_phase_2_refine_set():
    """Test plan phase-2-refine set updates a field."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(
            SCRIPT_PATH, 'plan', 'phase-2-refine', 'set',
            '--field', 'confidence_threshold', '--value', '90'
        )

        assert result.success, f'Should succeed: {result.stderr}'

        config = json.loads((ctx.fixture_dir / 'marshal.json').read_text())
        assert config['plan']['phase-2-refine']['confidence_threshold'] == 90


def test_phase_5_execute_get():
    """Test plan phase-5-execute get returns config."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'plan', 'phase-5-execute', 'get')

        assert result.success, f'Should succeed: {result.stderr}'
        assert 'commit_strategy' in result.stdout
        assert 'compatibility' not in result.stdout


def test_phase_5_execute_set():
    """Test plan phase-5-execute set updates a field."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(
            SCRIPT_PATH, 'plan', 'phase-5-execute', 'set',
            '--field', 'commit_strategy', '--value', 'per_plan'
        )

        assert result.success, f'Should succeed: {result.stderr}'

        config = json.loads((ctx.fixture_dir / 'marshal.json').read_text())
        assert config['plan']['phase-5-execute']['commit_strategy'] == 'per_plan'


def test_phase_2_refine_get_includes_compatibility():
    """Test plan phase-2-refine get returns compatibility."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'plan', 'phase-2-refine', 'get')

        assert result.success, f'Should succeed: {result.stderr}'
        assert 'compatibility' in result.stdout
        assert 'confidence_threshold' in result.stdout


def test_phase_2_refine_set_compatibility():
    """Test plan phase-2-refine set updates compatibility field."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(
            SCRIPT_PATH, 'plan', 'phase-2-refine', 'set',
            '--field', 'compatibility', '--value', 'deprecation'
        )

        assert result.success, f'Should succeed: {result.stderr}'

        config = json.loads((ctx.fixture_dir / 'marshal.json').read_text())
        assert config['plan']['phase-2-refine']['compatibility'] == 'deprecation'


# =============================================================================
# Main
# =============================================================================
