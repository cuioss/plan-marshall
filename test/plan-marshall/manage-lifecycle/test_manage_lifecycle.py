#!/usr/bin/env python3
"""Tests for lifecycle commands in manage_status.py script.

Tier 2 (direct import) tests with 3 subprocess tests for CLI plumbing.
"""

import json
import sys
from argparse import Namespace
from pathlib import Path

import pytest

# Import shared infrastructure
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from conftest import PlanContext, get_script_path, run_script  # noqa: E402

# Script path for remaining subprocess (CLI plumbing) tests
SCRIPT_PATH = get_script_path('plan-marshall', 'manage-status', 'manage_status.py')

# Tier 2 direct imports via importlib to avoid name collisions
# (_cmd_query.py exists in both manage-status and manage-tasks)
import importlib.util  # noqa: E402

_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-status'
    / 'scripts'
)


def _load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_lifecycle = _load_module('_lc_cmd_lifecycle', '_cmd_lifecycle.py')
_query = _load_module('_lc_cmd_query', '_cmd_query.py')
_routing = _load_module('_lc_cmd_routing', '_cmd_routing.py')

cmd_archive, cmd_transition = _lifecycle.cmd_archive, _lifecycle.cmd_transition
cmd_list = _query.cmd_list
cmd_get_routing_context, cmd_route, cmd_self_test = _routing.cmd_get_routing_context, _routing.cmd_route, _routing.cmd_self_test

# Import toon_parser - conftest sets up PYTHONPATH
from toon_parser import parse_toon  # type: ignore[import-not-found]  # noqa: E402

# =============================================================================
# Helper: create a status.json with standard phase structure
# =============================================================================


def _create_status(ctx, plan_id='test-plan', current_phase='1-init', phases=None, title='Test Plan'):
    """Create a status.json in the plan directory."""
    if phases is None:
        phases = [
            {'name': '1-init', 'status': 'done' if current_phase != '1-init' else 'in_progress'},
            {'name': '2-refine', 'status': 'in_progress' if current_phase == '2-refine' else 'pending'},
            {'name': '3-outline', 'status': 'in_progress' if current_phase == '3-outline' else 'pending'},
            {'name': '4-plan', 'status': 'in_progress' if current_phase == '4-plan' else 'pending'},
            {'name': '5-execute', 'status': 'in_progress' if current_phase == '5-execute' else 'pending'},
            {'name': '6-finalize', 'status': 'in_progress' if current_phase == '6-finalize' else 'pending'},
        ]
    status = {
        'title': title,
        'current_phase': current_phase,
        'phases': phases,
        'created': '2026-01-01T00:00:00Z',
        'updated': '2026-01-01T00:00:00Z',
    }
    status_file = ctx.plan_dir / 'status.json'
    status_file.write_text(json.dumps(status, indent=2))
    return status


# =============================================================================
# Test: list command (Tier 2 - direct import)
# =============================================================================


def test_list_empty_plans_dir():
    """Test listing when no plans exist."""
    with PlanContext(plan_id='lifecycle-list-empty') as ctx:
        # Remove the auto-created plan dir so plans/ is empty
        import shutil

        shutil.rmtree(ctx.plan_dir)

        result = cmd_list(Namespace(filter=None))
        assert result['status'] == 'success'
        assert result['total'] == 0


def test_list_no_plans_directory():
    """Test listing when plans directory does not exist at all."""
    with PlanContext(plan_id='lifecycle-list-nodir') as ctx:
        # Remove entire plans directory
        import shutil

        plans_dir = ctx.plan_dir.parent
        shutil.rmtree(plans_dir)

        result = cmd_list(Namespace(filter=None))
        assert result['status'] == 'success'
        assert result['total'] == 0


def test_list_with_plans():
    """Test listing when plans exist with status.json."""
    with PlanContext(plan_id='lifecycle-list-plans') as ctx:
        _create_status(ctx, plan_id='lifecycle-list-plans', current_phase='2-refine')

        result = cmd_list(Namespace(filter=None))
        assert result['status'] == 'success'
        assert result['total'] >= 1


def test_list_with_filter():
    """Test listing with phase filter."""
    with PlanContext(plan_id='lifecycle-list-filter') as ctx:
        _create_status(ctx, plan_id='lifecycle-list-filter', current_phase='3-outline')

        # Filter for matching phase
        result = cmd_list(Namespace(filter='3-outline'))
        assert result['status'] == 'success'
        assert result['total'] >= 1

        # Filter for non-matching phase
        result = cmd_list(Namespace(filter='5-execute'))
        assert result['status'] == 'success'
        assert result['total'] == 0


# =============================================================================
# Test: route command (Tier 2 - direct import)
# =============================================================================


def test_route_valid_phases():
    """Test route returns correct skill for each known phase."""
    expected = {
        '1-init': 'plan-init',
        '2-refine': 'request-refine',
        '3-outline': 'solution-outline',
        '4-plan': 'task-plan',
        '5-execute': 'plan-execute',
        '6-finalize': 'plan-finalize',
    }
    for phase, expected_skill in expected.items():
        result = cmd_route(Namespace(phase=phase))
        assert result['status'] == 'success'
        assert result['skill'] == expected_skill, f'Phase {phase}: expected {expected_skill}, got {result["skill"]}'


def test_route_unknown_phase():
    """Test route fails for an unknown phase."""
    result = cmd_route(Namespace(phase='unknown-phase'))
    assert result['status'] == 'error'


# =============================================================================
# Test: transition command (Tier 2 - direct import)
# =============================================================================


def test_transition_valid():
    """Test transitioning from one phase to the next."""
    with PlanContext(plan_id='lifecycle-trans') as ctx:
        _create_status(ctx, plan_id='lifecycle-trans', current_phase='1-init')

        result = cmd_transition(Namespace(plan_id='lifecycle-trans', completed='1-init'))
        assert result['status'] == 'success'
        assert result['completed_phase'] == '1-init'
        assert result['next_phase'] == '2-refine'


def test_transition_last_phase():
    """Test transitioning the final phase marks all completed."""
    with PlanContext(plan_id='lifecycle-trans-last') as ctx:
        phases = [
            {'name': '1-init', 'status': 'done'},
            {'name': '2-refine', 'status': 'done'},
            {'name': '3-outline', 'status': 'done'},
            {'name': '4-plan', 'status': 'done'},
            {'name': '5-execute', 'status': 'done'},
            {'name': '6-finalize', 'status': 'in_progress'},
        ]
        _create_status(ctx, plan_id='lifecycle-trans-last', current_phase='6-finalize', phases=phases)

        result = cmd_transition(Namespace(plan_id='lifecycle-trans-last', completed='6-finalize'))
        assert result['status'] == 'success'
        assert result['message'] == 'All phases completed'


def test_transition_invalid_phase():
    """Test transition fails for a phase not in the plan."""
    with PlanContext(plan_id='lifecycle-trans-badphase') as ctx:
        _create_status(ctx, plan_id='lifecycle-trans-badphase')

        result = cmd_transition(Namespace(plan_id='lifecycle-trans-badphase', completed='nonexistent-phase'))
        assert result['status'] == 'error'


def test_transition_nonexistent_plan():
    """Test transition raises RuntimeError for a plan without status.json."""
    with PlanContext(plan_id='lifecycle-trans-noplan'):
        # No status.json created — require_status raises RuntimeError
        with pytest.raises(RuntimeError):
            cmd_transition(Namespace(plan_id='lifecycle-trans-noplan', completed='1-init'))


# =============================================================================
# Test: get-routing-context command (Tier 2 - direct import)
# =============================================================================


def test_get_routing_context_valid():
    """Test getting routing context for a valid plan."""
    with PlanContext(plan_id='lifecycle-ctx') as ctx:
        _create_status(ctx, plan_id='lifecycle-ctx', current_phase='3-outline', title='My Feature')

        result = cmd_get_routing_context(Namespace(plan_id='lifecycle-ctx'))
        assert result['status'] == 'success'
        assert result['current_phase'] == '3-outline'
        assert result['skill'] == 'solution-outline'
        assert result['title'] == 'My Feature'


def test_get_routing_context_missing_plan():
    """Test get-routing-context raises RuntimeError for nonexistent plan."""
    with PlanContext(plan_id='lifecycle-ctx-missing'):
        # No status.json created — require_status raises RuntimeError
        with pytest.raises(RuntimeError):
            cmd_get_routing_context(Namespace(plan_id='lifecycle-ctx-missing'))


# =============================================================================
# Test: archive command (Tier 2 - direct import)
# =============================================================================


def test_archive_dry_run():
    """Test archive with --dry-run shows what would happen."""
    with PlanContext(plan_id='lifecycle-archive-dry') as ctx:
        _create_status(ctx, plan_id='lifecycle-archive-dry')

        result = cmd_archive(Namespace(plan_id='lifecycle-archive-dry', dry_run=True))
        assert result['status'] == 'success'
        # Plan directory should still exist after dry run
        assert ctx.plan_dir.exists(), 'Plan dir should still exist after dry run'


def test_archive_actual():
    """Test actual archive moves plan directory."""
    with PlanContext(plan_id='lifecycle-archive-real') as ctx:
        _create_status(ctx, plan_id='lifecycle-archive-real')

        result = cmd_archive(Namespace(plan_id='lifecycle-archive-real', dry_run=False))
        assert result['status'] == 'success'
        assert 'archived_to' in result
        # Plan directory should no longer exist
        assert not ctx.plan_dir.exists(), 'Plan dir should be moved after archive'


def test_archive_nonexistent_plan():
    """Test archive fails for nonexistent plan directory."""
    with PlanContext(plan_id='lifecycle-archive-gone'):
        result = cmd_archive(Namespace(plan_id='lifecycle-archive-nope', dry_run=False))
        assert result['status'] == 'error'


# =============================================================================
# Subprocess (CLI plumbing) tests
# =============================================================================


def test_cli_transition_invalid_plan_id():
    """Test transition CLI rejects invalid plan ID with exit code 1."""
    result = run_script(
        SCRIPT_PATH,
        'transition',
        '--plan-id',
        'INVALID ID!',
        '--completed',
        '1-init',
    )
    assert not result.success, 'Expected failure for invalid plan ID'


def test_cli_archive_invalid_plan_id():
    """Test archive CLI rejects invalid plan ID with exit code 1."""
    result = run_script(
        SCRIPT_PATH,
        'archive',
        '--plan-id',
        'BAD ID!',
    )
    assert not result.success, 'Expected failure for invalid plan ID'


def test_cli_self_test_passes():
    """Test self-test CLI reports all checks passing."""
    with PlanContext(plan_id='lifecycle-selftest'):
        result = run_script(SCRIPT_PATH, 'self-test')
        assert result.success, f'Self-test failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert data['passed'] == 4
        assert data['failed'] == 0
        assert 'failures' not in data
