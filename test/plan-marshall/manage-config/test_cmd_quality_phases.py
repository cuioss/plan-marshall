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

from test_helpers import SCRIPT_PATH, create_marshal_json

_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-config'
    / 'scripts'
)


def _load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# Load _cmd_quality_phases first so it's registered in sys.modules BEFORE _cmd_system_plan
# does `from _cmd_quality_phases import cmd_phase` — both modules must share the same instance
# for monkeypatching `_discover_steps_for_phase` to take effect during cmd_plan dispatch.
_cmd_quality_phases = _load_module('_cmd_quality_phases', '_cmd_quality_phases.py')
_cmd_system_plan = _load_module('_cmd_system_plan', '_cmd_system_plan.py')

cmd_plan = _cmd_system_plan.cmd_plan

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import run_script  # noqa: E402

# =============================================================================
# phase-5-execute Verification Pipeline Command Tests (Tier 2)
# =============================================================================


def test_execute_verify_get(plan_context):
    """Test plan phase-5-execute get returns steps list config."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_plan(Namespace(sub_noun='phase-5-execute', verb='get', field=None))

    assert result['status'] == 'success'
    assert 'verification_max_iterations' in result
    assert 'steps' in result
    assert 'default:quality_check' in result['steps']


def test_execute_verify_set_max_iterations(plan_context):
    """Test plan phase-5-execute set-max-iterations for verification."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_plan(Namespace(sub_noun='phase-5-execute', verb='set-max-iterations', value=10))

    assert result['status'] == 'success'

    # Verify changed
    config = json.loads((plan_context.fixture_dir / 'marshal.json').read_text())
    assert config['plan']['phase-5-execute']['verification_max_iterations'] == 10


def test_execute_set_steps(plan_context):
    """Test plan phase-5-execute set-steps replaces entire steps list, sorted by discovered order."""
    create_marshal_json(plan_context.fixture_dir)

    # Pass built-ins in reverse to prove ordering comes from discovery, not call order.
    result = cmd_plan(
        Namespace(
            sub_noun='phase-5-execute',
            verb='set-steps',
            steps='default:coverage_check,default:build_verify,default:quality_check',
        )
    )

    assert result['status'] == 'success'

    config = json.loads((plan_context.fixture_dir / 'marshal.json').read_text())
    # Sorted by discovered order: 10, 20, 30
    assert config['plan']['phase-5-execute']['steps'] == [
        'default:quality_check',
        'default:build_verify',
        'default:coverage_check',
    ]


def test_execute_add_step(plan_context, monkeypatch):
    """Test plan phase-5-execute add-step inserts an extension step at its discovered-order position."""
    create_marshal_json(plan_context.fixture_dir)

    # Inject an extension step with a known discovery order — overrides no longer exist.
    monkeypatch.setattr(
        _cmd_quality_phases,
        '_discover_steps_for_phase',
        lambda phase: [
            {'name': 'default:quality_check', 'order': 10},
            {'name': 'default:build_verify', 'order': 20},
            {'name': 'default:coverage_check', 'order': 30},
            {'name': 'pm-documents:doc-verify', 'order': 500},
        ],
    )

    result = cmd_plan(
        Namespace(
            sub_noun='phase-5-execute',
            verb='add-step',
            step='pm-documents:doc-verify',
            position=None,
        )
    )

    assert result['status'] == 'success'

    config = json.loads((plan_context.fixture_dir / 'marshal.json').read_text())
    steps = config['plan']['phase-5-execute']['steps']
    assert 'pm-documents:doc-verify' in steps
    # Order 500 places it after the default built-ins (10, 20, 30)
    assert steps[-1] == 'pm-documents:doc-verify'


def test_execute_remove_step(plan_context):
    """Test plan phase-5-execute remove-step removes from steps list."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_plan(
        Namespace(
            sub_noun='phase-5-execute',
            verb='remove-step',
            step='default:quality_check',
        )
    )

    assert result['status'] == 'success'

    config = json.loads((plan_context.fixture_dir / 'marshal.json').read_text())
    steps = config['plan']['phase-5-execute']['steps']
    assert 'default:quality_check' not in steps
    assert 'default:build_verify' in steps


def test_execute_verify_get_field(plan_context):
    """Test plan phase-5-execute get --field returns specific verification field."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_plan(
        Namespace(
            sub_noun='phase-5-execute',
            verb='get',
            field='verification_max_iterations',
        )
    )

    assert result['status'] == 'success'
    assert result['value'] == 5


def test_execute_add_step_duplicate(plan_context):
    """Test plan phase-5-execute add-step with existing step returns error."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_plan(
        Namespace(
            sub_noun='phase-5-execute',
            verb='add-step',
            step='default:quality_check',
            position=None,
        )
    )

    assert result['status'] == 'error'
    assert 'default:quality_check' in result['error']


def test_execute_remove_step_not_found(plan_context):
    """Test plan phase-5-execute remove-step with missing step returns error."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_plan(
        Namespace(
            sub_noun='phase-5-execute',
            verb='remove-step',
            step='nonexistent',
        )
    )

    assert result['status'] == 'error'
    assert 'nonexistent' in result['error']


# =============================================================================
# phase-6-finalize Command Tests (Tier 2)
# =============================================================================


def test_finalize_get(plan_context):
    """Test plan phase-6-finalize get returns steps list config."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_plan(Namespace(sub_noun='phase-6-finalize', verb='get', field=None))

    assert result['status'] == 'success'
    assert 'max_iterations' in result
    assert 'steps' in result
    assert 'default:commit-push' in result['steps']


def test_finalize_set_steps(plan_context):
    """Test plan phase-6-finalize set-steps replaces entire steps list."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_plan(
        Namespace(
            sub_noun='phase-6-finalize',
            verb='set-steps',
            steps='default:commit-push,default:create-pr,default:archive-plan',
        )
    )

    assert result['status'] == 'success'

    config = json.loads((plan_context.fixture_dir / 'marshal.json').read_text())
    steps = config['plan']['phase-6-finalize']['steps']
    assert steps == ['default:commit-push', 'default:create-pr', 'default:archive-plan']


def test_finalize_set_steps_empty_error(plan_context):
    """Test plan phase-6-finalize set-steps with empty list returns error."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_plan(Namespace(sub_noun='phase-6-finalize', verb='set-steps', steps=''))

    assert result['status'] == 'error'


def test_finalize_add_step(plan_context, monkeypatch):
    """Test plan phase-6-finalize add-step places an extension step at its discovered-order position."""
    create_marshal_json(plan_context.fixture_dir)

    # Inject discovery orders for the existing built-ins plus an extension step at order 75.
    monkeypatch.setattr(
        _cmd_quality_phases,
        '_discover_steps_for_phase',
        lambda phase: [
            {'name': 'default:commit-push', 'order': 10},
            {'name': 'default:create-pr', 'order': 20},
            {'name': 'default:automated-review', 'order': 30},
            {'name': 'default:sonar-roundtrip', 'order': 40},
            {'name': 'default:lessons-capture', 'order': 50},
            {'name': 'default:branch-cleanup', 'order': 70},
            {'name': 'pm-dev-java:java-post-pr', 'order': 75},
            {'name': 'default:record-metrics', 'order': 990},
            {'name': 'default:archive-plan', 'order': 1000},
        ],
    )

    result = cmd_plan(
        Namespace(
            sub_noun='phase-6-finalize',
            verb='add-step',
            step='pm-dev-java:java-post-pr',
            position=None,
        )
    )

    assert result['status'] == 'success'

    config = json.loads((plan_context.fixture_dir / 'marshal.json').read_text())
    steps = config['plan']['phase-6-finalize']['steps']
    assert 'pm-dev-java:java-post-pr' in steps
    # Order 75 sits between branch-cleanup (70) and record-metrics (990)
    idx = steps.index('pm-dev-java:java-post-pr')
    assert steps[idx - 1] == 'default:branch-cleanup'
    assert steps[idx + 1] == 'default:record-metrics'


def test_finalize_add_step_sorts_by_order(plan_context, monkeypatch):
    """Test plan phase-6-finalize add-step places the step by discovered order (positional arg ignored)."""
    create_marshal_json(plan_context.fixture_dir)

    # Inject a project step at order=1 so it sorts ahead of every built-in.
    monkeypatch.setattr(
        _cmd_quality_phases,
        '_discover_steps_for_phase',
        lambda phase: [
            {'name': 'project:finalize-step-custom', 'order': 1},
            {'name': 'default:commit-push', 'order': 10},
            {'name': 'default:create-pr', 'order': 20},
            {'name': 'default:automated-review', 'order': 30},
            {'name': 'default:sonar-roundtrip', 'order': 40},
            {'name': 'default:lessons-capture', 'order': 50},
            {'name': 'default:branch-cleanup', 'order': 70},
            {'name': 'default:record-metrics', 'order': 990},
            {'name': 'default:archive-plan', 'order': 1000},
        ],
    )

    result = cmd_plan(
        Namespace(
            sub_noun='phase-6-finalize',
            verb='add-step',
            step='project:finalize-step-custom',
            position=5,  # Ignored — sort by discovered order.
        )
    )

    assert result['status'] == 'success'

    config = json.loads((plan_context.fixture_dir / 'marshal.json').read_text())
    steps = config['plan']['phase-6-finalize']['steps']
    # Order 1 is lowest — custom step lands at index 0.
    assert steps[0] == 'project:finalize-step-custom'


def test_finalize_add_step_duplicate_error(plan_context):
    """Test plan phase-6-finalize add-step with duplicate returns error."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_plan(
        Namespace(
            sub_noun='phase-6-finalize',
            verb='add-step',
            step='default:commit-push',
            position=None,
        )
    )

    assert result['status'] == 'error'


def test_finalize_remove_step(plan_context):
    """Test plan phase-6-finalize remove-step removes a step."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_plan(
        Namespace(
            sub_noun='phase-6-finalize',
            verb='remove-step',
            step='default:sonar-roundtrip',
        )
    )

    assert result['status'] == 'success'

    config = json.loads((plan_context.fixture_dir / 'marshal.json').read_text())
    steps = config['plan']['phase-6-finalize']['steps']
    assert 'default:sonar-roundtrip' not in steps


def test_finalize_remove_step_not_found_error(plan_context):
    """Test plan phase-6-finalize remove-step with missing step returns error."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_plan(
        Namespace(
            sub_noun='phase-6-finalize',
            verb='remove-step',
            step='bogus',
        )
    )

    assert result['status'] == 'error'


def test_finalize_set_max_iterations(plan_context):
    """Test plan phase-6-finalize set-max-iterations."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_plan(Namespace(sub_noun='phase-6-finalize', verb='set-max-iterations', value=7))

    assert result['status'] == 'success'

    config = json.loads((plan_context.fixture_dir / 'marshal.json').read_text())
    assert config['plan']['phase-6-finalize']['max_iterations'] == 7


# =============================================================================
# Order-driven set-steps / add-step / overrides Tests (deliverable 6)
# =============================================================================


def test_finalize_set_steps_sorts_by_order(plan_context):
    """set-steps persists the steps list sorted by ascending resolved order."""
    create_marshal_json(plan_context.fixture_dir)

    # Pass built-in steps in reverse order to prove sorting.
    result = cmd_plan(
        Namespace(
            sub_noun='phase-6-finalize',
            verb='set-steps',
            steps='default:archive-plan,default:record-metrics,default:commit-push,default:create-pr',
        )
    )

    assert result['status'] == 'success'
    assert result['steps'] == [
        'default:commit-push',
        'default:create-pr',
        'default:record-metrics',
        'default:archive-plan',
    ]


def test_finalize_set_steps_missing_order_returns_error(plan_context):
    """set-steps fails with `error: missing_order` when a step has no resolvable order."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_plan(
        Namespace(
            sub_noun='phase-6-finalize',
            verb='set-steps',
            steps='default:commit-push,pm-dev-java:java-post-pr',
        )
    )

    assert result['status'] == 'error'
    assert result['error'] == 'missing_order'
    assert result['step'] == 'pm-dev-java:java-post-pr'
    assert result['phase'] == 'phase-6-finalize'


def test_finalize_set_steps_order_collision_returns_error(plan_context, monkeypatch):
    """set-steps fails with `error: order_collision` when two steps share the same discovered order."""
    create_marshal_json(plan_context.fixture_dir)

    # Inject a discovery layout where commit-push and create-pr collide at order 20.
    monkeypatch.setattr(
        _cmd_quality_phases,
        '_discover_steps_for_phase',
        lambda phase: [
            {'name': 'default:commit-push', 'order': 20},
            {'name': 'default:create-pr', 'order': 20},
        ],
    )

    result = cmd_plan(
        Namespace(
            sub_noun='phase-6-finalize',
            verb='set-steps',
            steps='default:commit-push,default:create-pr',
        )
    )

    assert result['status'] == 'error'
    assert result['error'] == 'order_collision'
    assert result['order'] == 20
    assert sorted(result['steps']) == ['default:commit-push', 'default:create-pr']
    assert result['phase'] == 'phase-6-finalize'


def test_execute_add_step_order_collision_returns_error(plan_context, monkeypatch):
    """add-step fails with `error: order_collision` mirroring set-steps semantics."""
    create_marshal_json(plan_context.fixture_dir)

    # Inject discovery where the new extension step shares order 10 with quality_check.
    monkeypatch.setattr(
        _cmd_quality_phases,
        '_discover_steps_for_phase',
        lambda phase: [
            {'name': 'default:quality_check', 'order': 10},
            {'name': 'default:build_verify', 'order': 20},
            {'name': 'default:coverage_check', 'order': 30},
            {'name': 'pm-documents:doc-verify', 'order': 10},
        ],
    )

    result = cmd_plan(
        Namespace(
            sub_noun='phase-5-execute',
            verb='add-step',
            step='pm-documents:doc-verify',
            position=None,
        )
    )

    assert result['status'] == 'error'
    assert result['error'] == 'order_collision'
    assert result['order'] == 10


# =============================================================================
# Scalar Phase Command Tests (Tier 2)
# =============================================================================


def test_phase_1_init_get(plan_context):
    """Test plan phase-1-init get returns config."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_plan(Namespace(sub_noun='phase-1-init', verb='get', field=None))

    assert result['status'] == 'success'
    assert 'branch_strategy' in result


def test_phase_1_init_set(plan_context):
    """Test plan phase-1-init set updates a field."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_plan(
        Namespace(
            sub_noun='phase-1-init',
            verb='set',
            field='branch_strategy',
            value='feature-branch',
        )
    )

    assert result['status'] == 'success'

    config = json.loads((plan_context.fixture_dir / 'marshal.json').read_text())
    assert config['plan']['phase-1-init']['branch_strategy'] == 'feature-branch'


def test_phase_2_refine_get(plan_context):
    """Test plan phase-2-refine get returns config."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_plan(Namespace(sub_noun='phase-2-refine', verb='get', field=None))

    assert result['status'] == 'success'
    assert 'confidence_threshold' in result


def test_phase_2_refine_set(plan_context):
    """Test plan phase-2-refine set updates a field."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_plan(
        Namespace(
            sub_noun='phase-2-refine',
            verb='set',
            field='confidence_threshold',
            value='90',
        )
    )

    assert result['status'] == 'success'

    config = json.loads((plan_context.fixture_dir / 'marshal.json').read_text())
    assert config['plan']['phase-2-refine']['confidence_threshold'] == 90


def test_phase_5_execute_get(plan_context):
    """Test plan phase-5-execute get returns config."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_plan(Namespace(sub_noun='phase-5-execute', verb='get', field=None))

    assert result['status'] == 'success'
    assert 'commit_strategy' in result
    assert 'compatibility' not in result


def test_phase_5_execute_set(plan_context):
    """Test plan phase-5-execute set updates a field."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_plan(
        Namespace(
            sub_noun='phase-5-execute',
            verb='set',
            field='commit_strategy',
            value='per_plan',
        )
    )

    assert result['status'] == 'success'

    config = json.loads((plan_context.fixture_dir / 'marshal.json').read_text())
    assert config['plan']['phase-5-execute']['commit_strategy'] == 'per_plan'


def test_phase_2_refine_get_includes_compatibility(plan_context):
    """Test plan phase-2-refine get returns compatibility."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_plan(Namespace(sub_noun='phase-2-refine', verb='get', field=None))

    assert result['status'] == 'success'
    assert 'compatibility' in result
    assert 'confidence_threshold' in result


def test_phase_2_refine_set_compatibility(plan_context):
    """Test plan phase-2-refine set updates compatibility field."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_plan(
        Namespace(
            sub_noun='phase-2-refine',
            verb='set',
            field='compatibility',
            value='deprecation',
        )
    )

    assert result['status'] == 'success'

    config = json.loads((plan_context.fixture_dir / 'marshal.json').read_text())
    assert config['plan']['phase-2-refine']['compatibility'] == 'deprecation'


# =============================================================================
# CLI Plumbing Tests (Tier 3 - subprocess)
# =============================================================================


def test_cli_plan_phase_5_execute_get(plan_context):
    """Test CLI plumbing: plan phase-5-execute get outputs TOON."""
    create_marshal_json(plan_context.fixture_dir)

    result = run_script(SCRIPT_PATH, 'plan', 'phase-5-execute', 'get')

    assert result.success, f'Should succeed: {result.stderr}'
    assert 'verification_max_iterations' in result.stdout


def test_cli_plan_phase_6_finalize_get(plan_context):
    """Test CLI plumbing: plan phase-6-finalize get outputs TOON."""
    create_marshal_json(plan_context.fixture_dir)

    result = run_script(SCRIPT_PATH, 'plan', 'phase-6-finalize', 'get')

    assert result.success, f'Should succeed: {result.stderr}'
    assert 'max_iterations' in result.stdout


def test_cli_set_step_order_override_no_longer_registered(plan_context):
    """Regression: the set-step-order-override verb is no longer a registered argparse choice."""
    create_marshal_json(plan_context.fixture_dir)

    result = run_script(
        SCRIPT_PATH,
        'plan',
        'phase-6-finalize',
        'set-step-order-override',
        '--step',
        'foo',
        '--order',
        '1',
    )

    assert not result.success
    combined = (result.stderr + result.stdout).lower()
    assert 'invalid choice' in combined or 'unrecognized' in combined


def test_cli_remove_step_order_override_no_longer_registered(plan_context):
    """Regression: the remove-step-order-override verb is no longer a registered argparse choice."""
    create_marshal_json(plan_context.fixture_dir)

    result = run_script(
        SCRIPT_PATH,
        'plan',
        'phase-6-finalize',
        'remove-step-order-override',
        '--step',
        'foo',
    )

    assert not result.success
    combined = (result.stderr + result.stdout).lower()
    assert 'invalid choice' in combined or 'unrecognized' in combined


# =============================================================================
# Main
# =============================================================================
