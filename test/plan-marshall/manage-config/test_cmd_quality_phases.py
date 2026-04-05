#!/usr/bin/env python3
"""Tests for phase-based plan commands in manage-config.

Tests plan phase-5-execute (including verification pipeline), phase-6-finalize pipeline commands,
as well as scalar phase commands (phase-1-init, phase-2-refine).

Tier 2 (direct import) tests with 2 subprocess tests for CLI plumbing.
"""

import importlib.util
import json
import sys
from argparse import Namespace
from pathlib import Path

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

cmd_plan = _cmd_system_plan.cmd_plan

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import PlanContext, run_script  # noqa: E402

# =============================================================================
# phase-5-execute Verification Pipeline Command Tests (Tier 2)
# =============================================================================


def test_execute_verify_get():
    """Test plan phase-5-execute get returns steps list config."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_plan(Namespace(sub_noun='phase-5-execute', verb='get', field=None))

        assert result['status'] == 'success'
        assert 'verification_max_iterations' in result
        assert 'steps' in result
        assert 'default:quality_check' in result['steps']


def test_execute_verify_set_max_iterations():
    """Test plan phase-5-execute set-max-iterations for verification."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_plan(Namespace(sub_noun='phase-5-execute', verb='set-max-iterations', value=10))

        assert result['status'] == 'success'

        # Verify changed
        config = json.loads((ctx.fixture_dir / 'marshal.json').read_text())
        assert config['plan']['phase-5-execute']['verification_max_iterations'] == 10


def test_execute_set_steps():
    """Test plan phase-5-execute set-steps replaces entire steps list."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_plan(Namespace(
            sub_noun='phase-5-execute',
            verb='set-steps',
            steps='default:quality_check,default:build_verify,pm-documents:doc-verify',
        ))

        assert result['status'] == 'success'

        config = json.loads((ctx.fixture_dir / 'marshal.json').read_text())
        assert config['plan']['phase-5-execute']['steps'] == [
            'default:quality_check',
            'default:build_verify',
            'pm-documents:doc-verify',
        ]


def test_execute_add_step():
    """Test plan phase-5-execute add-step appends to steps list."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_plan(Namespace(
            sub_noun='phase-5-execute',
            verb='add-step',
            step='pm-documents:doc-verify',
            position=None,
        ))

        assert result['status'] == 'success'

        config = json.loads((ctx.fixture_dir / 'marshal.json').read_text())
        steps = config['plan']['phase-5-execute']['steps']
        assert 'pm-documents:doc-verify' in steps
        assert steps[-1] == 'pm-documents:doc-verify'


def test_execute_remove_step():
    """Test plan phase-5-execute remove-step removes from steps list."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_plan(Namespace(
            sub_noun='phase-5-execute',
            verb='remove-step',
            step='default:quality_check',
        ))

        assert result['status'] == 'success'

        config = json.loads((ctx.fixture_dir / 'marshal.json').read_text())
        steps = config['plan']['phase-5-execute']['steps']
        assert 'default:quality_check' not in steps
        assert 'default:build_verify' in steps


def test_execute_verify_get_field():
    """Test plan phase-5-execute get --field returns specific verification field."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_plan(Namespace(
            sub_noun='phase-5-execute',
            verb='get',
            field='verification_max_iterations',
        ))

        assert result['status'] == 'success'
        assert result['value'] == 5


def test_execute_add_step_duplicate():
    """Test plan phase-5-execute add-step with existing step returns error."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_plan(Namespace(
            sub_noun='phase-5-execute',
            verb='add-step',
            step='default:quality_check',
            position=None,
        ))

        assert result['status'] == 'error'
        assert 'default:quality_check' in result['error']


def test_execute_remove_step_not_found():
    """Test plan phase-5-execute remove-step with missing step returns error."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_plan(Namespace(
            sub_noun='phase-5-execute',
            verb='remove-step',
            step='nonexistent',
        ))

        assert result['status'] == 'error'
        assert 'nonexistent' in result['error']


# =============================================================================
# phase-6-finalize Command Tests (Tier 2)
# =============================================================================


def test_finalize_get():
    """Test plan phase-6-finalize get returns steps list config."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_plan(Namespace(sub_noun='phase-6-finalize', verb='get', field=None))

        assert result['status'] == 'success'
        assert 'max_iterations' in result
        assert 'steps' in result
        assert 'default:commit-push' in result['steps']


def test_finalize_set_steps():
    """Test plan phase-6-finalize set-steps replaces entire steps list."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_plan(Namespace(
            sub_noun='phase-6-finalize',
            verb='set-steps',
            steps='default:commit-push,default:create-pr,default:archive-plan',
        ))

        assert result['status'] == 'success'

        config = json.loads((ctx.fixture_dir / 'marshal.json').read_text())
        steps = config['plan']['phase-6-finalize']['steps']
        assert steps == ['default:commit-push', 'default:create-pr', 'default:archive-plan']


def test_finalize_set_steps_empty_error():
    """Test plan phase-6-finalize set-steps with empty list returns error."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_plan(Namespace(sub_noun='phase-6-finalize', verb='set-steps', steps=''))

        assert result['status'] == 'error'


def test_finalize_add_step():
    """Test plan phase-6-finalize add-step appends a new step."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_plan(Namespace(
            sub_noun='phase-6-finalize',
            verb='add-step',
            step='pm-dev-java:java-post-pr',
            position=None,
        ))

        assert result['status'] == 'success'

        config = json.loads((ctx.fixture_dir / 'marshal.json').read_text())
        steps = config['plan']['phase-6-finalize']['steps']
        assert 'pm-dev-java:java-post-pr' in steps
        assert steps[-1] == 'pm-dev-java:java-post-pr'


def test_finalize_add_step_with_position():
    """Test plan phase-6-finalize add-step with position inserts at index."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_plan(Namespace(
            sub_noun='phase-6-finalize',
            verb='add-step',
            step='project:finalize-step-custom',
            position=0,
        ))

        assert result['status'] == 'success'

        config = json.loads((ctx.fixture_dir / 'marshal.json').read_text())
        steps = config['plan']['phase-6-finalize']['steps']
        assert steps[0] == 'project:finalize-step-custom'


def test_finalize_add_step_duplicate_error():
    """Test plan phase-6-finalize add-step with duplicate returns error."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_plan(Namespace(
            sub_noun='phase-6-finalize',
            verb='add-step',
            step='default:commit-push',
            position=None,
        ))

        assert result['status'] == 'error'


def test_finalize_remove_step():
    """Test plan phase-6-finalize remove-step removes a step."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_plan(Namespace(
            sub_noun='phase-6-finalize',
            verb='remove-step',
            step='default:sonar-roundtrip',
        ))

        assert result['status'] == 'success'

        config = json.loads((ctx.fixture_dir / 'marshal.json').read_text())
        steps = config['plan']['phase-6-finalize']['steps']
        assert 'default:sonar-roundtrip' not in steps


def test_finalize_remove_step_not_found_error():
    """Test plan phase-6-finalize remove-step with missing step returns error."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_plan(Namespace(
            sub_noun='phase-6-finalize',
            verb='remove-step',
            step='bogus',
        ))

        assert result['status'] == 'error'


def test_finalize_set_max_iterations():
    """Test plan phase-6-finalize set-max-iterations."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_plan(Namespace(sub_noun='phase-6-finalize', verb='set-max-iterations', value=7))

        assert result['status'] == 'success'

        config = json.loads((ctx.fixture_dir / 'marshal.json').read_text())
        assert config['plan']['phase-6-finalize']['max_iterations'] == 7


# =============================================================================
# Scalar Phase Command Tests (Tier 2)
# =============================================================================


def test_phase_1_init_get():
    """Test plan phase-1-init get returns config."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_plan(Namespace(sub_noun='phase-1-init', verb='get', field=None))

        assert result['status'] == 'success'
        assert 'branch_strategy' in result


def test_phase_1_init_set():
    """Test plan phase-1-init set updates a field."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_plan(Namespace(
            sub_noun='phase-1-init',
            verb='set',
            field='branch_strategy',
            value='feature-branch',
        ))

        assert result['status'] == 'success'

        config = json.loads((ctx.fixture_dir / 'marshal.json').read_text())
        assert config['plan']['phase-1-init']['branch_strategy'] == 'feature-branch'


def test_phase_2_refine_get():
    """Test plan phase-2-refine get returns config."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_plan(Namespace(sub_noun='phase-2-refine', verb='get', field=None))

        assert result['status'] == 'success'
        assert 'confidence_threshold' in result


def test_phase_2_refine_set():
    """Test plan phase-2-refine set updates a field."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_plan(Namespace(
            sub_noun='phase-2-refine',
            verb='set',
            field='confidence_threshold',
            value='90',
        ))

        assert result['status'] == 'success'

        config = json.loads((ctx.fixture_dir / 'marshal.json').read_text())
        assert config['plan']['phase-2-refine']['confidence_threshold'] == 90


def test_phase_5_execute_get():
    """Test plan phase-5-execute get returns config."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_plan(Namespace(sub_noun='phase-5-execute', verb='get', field=None))

        assert result['status'] == 'success'
        assert 'commit_strategy' in result
        assert 'compatibility' not in result


def test_phase_5_execute_set():
    """Test plan phase-5-execute set updates a field."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_plan(Namespace(
            sub_noun='phase-5-execute',
            verb='set',
            field='commit_strategy',
            value='per_plan',
        ))

        assert result['status'] == 'success'

        config = json.loads((ctx.fixture_dir / 'marshal.json').read_text())
        assert config['plan']['phase-5-execute']['commit_strategy'] == 'per_plan'


def test_phase_2_refine_get_includes_compatibility():
    """Test plan phase-2-refine get returns compatibility."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_plan(Namespace(sub_noun='phase-2-refine', verb='get', field=None))

        assert result['status'] == 'success'
        assert 'compatibility' in result
        assert 'confidence_threshold' in result


def test_phase_2_refine_set_compatibility():
    """Test plan phase-2-refine set updates compatibility field."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_plan(Namespace(
            sub_noun='phase-2-refine',
            verb='set',
            field='compatibility',
            value='deprecation',
        ))

        assert result['status'] == 'success'

        config = json.loads((ctx.fixture_dir / 'marshal.json').read_text())
        assert config['plan']['phase-2-refine']['compatibility'] == 'deprecation'


# =============================================================================
# CLI Plumbing Tests (Tier 3 - subprocess)
# =============================================================================


def test_cli_plan_phase_5_execute_get():
    """Test CLI plumbing: plan phase-5-execute get outputs TOON."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'plan', 'phase-5-execute', 'get')

        assert result.success, f'Should succeed: {result.stderr}'
        assert 'verification_max_iterations' in result.stdout


def test_cli_plan_phase_6_finalize_get():
    """Test CLI plumbing: plan phase-6-finalize get outputs TOON."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'plan', 'phase-6-finalize', 'get')

        assert result.success, f'Should succeed: {result.stderr}'
        assert 'max_iterations' in result.stdout


# =============================================================================
# Main
# =============================================================================
