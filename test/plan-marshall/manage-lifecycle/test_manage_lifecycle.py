#!/usr/bin/env python3
"""Tests for lifecycle commands in manage_status.py script."""

import json
import sys
from pathlib import Path

# Import shared infrastructure
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from conftest import PlanContext, get_script_path, run_script

# Get script path - lifecycle commands are now in manage_status.py
SCRIPT_PATH = get_script_path('plan-marshall', 'manage-status', 'manage_status.py')

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
# Test: list command
# =============================================================================


def test_list_empty_plans_dir():
    """Test listing when no plans exist."""
    with PlanContext(plan_id='lifecycle-list-empty') as ctx:
        # Remove the auto-created plan dir so plans/ is empty
        import shutil

        shutil.rmtree(ctx.plan_dir)

        result = run_script(SCRIPT_PATH, 'list')
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert data['total'] == 0


def test_list_no_plans_directory():
    """Test listing when plans directory does not exist at all."""
    with PlanContext(plan_id='lifecycle-list-nodir') as ctx:
        # Remove entire plans directory
        import shutil

        plans_dir = ctx.plan_dir.parent
        shutil.rmtree(plans_dir)

        result = run_script(SCRIPT_PATH, 'list')
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert data['total'] == 0


def test_list_with_plans():
    """Test listing when plans exist with status.json."""
    with PlanContext(plan_id='lifecycle-list-plans') as ctx:
        _create_status(ctx, plan_id='lifecycle-list-plans', current_phase='2-refine')

        result = run_script(SCRIPT_PATH, 'list')
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert data['total'] >= 1


def test_list_with_filter():
    """Test listing with phase filter."""
    with PlanContext(plan_id='lifecycle-list-filter') as ctx:
        _create_status(ctx, plan_id='lifecycle-list-filter', current_phase='3-outline')

        # Filter for matching phase
        result = run_script(SCRIPT_PATH, 'list', '--filter', '3-outline')
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert data['total'] >= 1

        # Filter for non-matching phase
        result = run_script(SCRIPT_PATH, 'list', '--filter', '5-execute')
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert data['total'] == 0


# =============================================================================
# Test: route command
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
        result = run_script(SCRIPT_PATH, 'route', '--phase', phase)
        assert result.success, f'Route failed for {phase}: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert data['skill'] == expected_skill, f'Phase {phase}: expected {expected_skill}, got {data["skill"]}'


def test_route_unknown_phase():
    """Test route fails for an unknown phase."""
    result = run_script(SCRIPT_PATH, 'route', '--phase', 'unknown-phase')
    assert not result.success, 'Expected failure for unknown phase'


# =============================================================================
# Test: transition command
# =============================================================================


def test_transition_valid():
    """Test transitioning from one phase to the next."""
    with PlanContext(plan_id='lifecycle-trans') as ctx:
        _create_status(ctx, plan_id='lifecycle-trans', current_phase='1-init')

        result = run_script(
            SCRIPT_PATH,
            'transition',
            '--plan-id',
            'lifecycle-trans',
            '--completed',
            '1-init',
        )
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert data['completed_phase'] == '1-init'
        assert data['next_phase'] == '2-refine'


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

        result = run_script(
            SCRIPT_PATH,
            'transition',
            '--plan-id',
            'lifecycle-trans-last',
            '--completed',
            '6-finalize',
        )
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert data['message'] == 'All phases completed'


def test_transition_invalid_plan_id():
    """Test transition fails with invalid plan ID."""
    result = run_script(
        SCRIPT_PATH,
        'transition',
        '--plan-id',
        'INVALID ID!',
        '--completed',
        '1-init',
    )
    assert not result.success, 'Expected failure for invalid plan ID'


def test_transition_nonexistent_plan():
    """Test transition fails for a plan without status.json."""
    with PlanContext(plan_id='lifecycle-trans-noplan'):
        # No status.json created
        result = run_script(
            SCRIPT_PATH,
            'transition',
            '--plan-id',
            'lifecycle-trans-noplan',
            '--completed',
            '1-init',
        )
        assert not result.success, 'Expected failure for missing status.json'


def test_transition_invalid_phase():
    """Test transition fails for a phase not in the plan."""
    with PlanContext(plan_id='lifecycle-trans-badphase') as ctx:
        _create_status(ctx, plan_id='lifecycle-trans-badphase')

        result = run_script(
            SCRIPT_PATH,
            'transition',
            '--plan-id',
            'lifecycle-trans-badphase',
            '--completed',
            'nonexistent-phase',
        )
        assert not result.success, 'Expected failure for invalid phase'


# =============================================================================
# Test: get-routing-context command
# =============================================================================


def test_get_routing_context_valid():
    """Test getting routing context for a valid plan."""
    with PlanContext(plan_id='lifecycle-ctx') as ctx:
        _create_status(ctx, plan_id='lifecycle-ctx', current_phase='3-outline', title='My Feature')

        result = run_script(
            SCRIPT_PATH,
            'get-routing-context',
            '--plan-id',
            'lifecycle-ctx',
        )
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert data['current_phase'] == '3-outline'
        assert data['skill'] == 'solution-outline'
        assert data['title'] == 'My Feature'


def test_get_routing_context_invalid_plan_id():
    """Test get-routing-context fails with invalid plan ID."""
    result = run_script(
        SCRIPT_PATH,
        'get-routing-context',
        '--plan-id',
        '!!!bad!!!',
    )
    assert not result.success, 'Expected failure for invalid plan ID'


def test_get_routing_context_missing_plan():
    """Test get-routing-context fails for nonexistent plan."""
    with PlanContext(plan_id='lifecycle-ctx-missing'):
        result = run_script(
            SCRIPT_PATH,
            'get-routing-context',
            '--plan-id',
            'lifecycle-ctx-missing',
        )
        assert not result.success, 'Expected failure for missing plan'


# =============================================================================
# Test: archive command
# =============================================================================


def test_archive_dry_run():
    """Test archive with --dry-run shows what would happen."""
    with PlanContext(plan_id='lifecycle-archive-dry') as ctx:
        _create_status(ctx, plan_id='lifecycle-archive-dry')

        result = run_script(
            SCRIPT_PATH,
            'archive',
            '--plan-id',
            'lifecycle-archive-dry',
            '--dry-run',
        )
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        # Plan directory should still exist after dry run
        assert ctx.plan_dir.exists(), 'Plan dir should still exist after dry run'


def test_archive_actual():
    """Test actual archive moves plan directory."""
    with PlanContext(plan_id='lifecycle-archive-real') as ctx:
        _create_status(ctx, plan_id='lifecycle-archive-real')

        result = run_script(
            SCRIPT_PATH,
            'archive',
            '--plan-id',
            'lifecycle-archive-real',
        )
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert 'archived_to' in data
        # Plan directory should no longer exist
        assert not ctx.plan_dir.exists(), 'Plan dir should be moved after archive'


def test_archive_invalid_plan_id():
    """Test archive fails with invalid plan ID."""
    result = run_script(
        SCRIPT_PATH,
        'archive',
        '--plan-id',
        'BAD ID!',
    )
    assert not result.success, 'Expected failure for invalid plan ID'


# =============================================================================
# Test: self-test command
# =============================================================================


def test_self_test_passes():
    """Test self-test reports all checks passing."""
    with PlanContext(plan_id='lifecycle-selftest'):
        result = run_script(SCRIPT_PATH, 'self-test')
        assert result.success, f'Self-test failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert data['passed'] == 4
        assert data['failed'] == 0
        assert 'failures' not in data


# =============================================================================
# Test: archive - nonexistent plan
# =============================================================================


def test_archive_nonexistent_plan():
    """Test archive fails for nonexistent plan directory."""
    with PlanContext(plan_id='lifecycle-archive-gone'):
        # Remove the plan dir

        _ = Path(PlanContext(plan_id='lifecycle-archive-gone').plan_dir or '')
        # Use PlanContext but the dir was already created - remove it
        result = run_script(
            SCRIPT_PATH,
            'archive',
            '--plan-id',
            'lifecycle-archive-nope',
        )
        assert not result.success, 'Expected failure for nonexistent plan'
