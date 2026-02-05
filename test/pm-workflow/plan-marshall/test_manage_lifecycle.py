#!/usr/bin/env python3
"""Tests for manage-lifecycle.py script.

manage-lifecycle handles plan discovery, transitions, archiving, and routing.
Status operations (create, read, set-phase, etc.) are in manage-status.
"""

import sys
from pathlib import Path

# Import shared infrastructure
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from conftest import PlanContext, get_script_path, run_script  # noqa: E402

# Get script paths
LIFECYCLE_SCRIPT = get_script_path('pm-workflow', 'plan-marshall', 'manage-lifecycle.py')
STATUS_SCRIPT = get_script_path('pm-workflow', 'manage-status', 'manage_status.py')

# Import toon_parser - conftest sets up PYTHONPATH
from toon_parser import parse_toon  # type: ignore[import-not-found]  # noqa: E402

# Alias for backward compatibility
TestContext = PlanContext


def _create_plan(plan_id: str, title: str, phases: str) -> None:
    """Helper to create a plan using manage-status."""
    result = run_script(
        STATUS_SCRIPT,
        'create',
        '--plan-id',
        plan_id,
        '--title',
        title,
        '--phases',
        phases,
    )
    assert result.success, f'Failed to create plan: {result.stderr}'


# =============================================================================
# Test: Get Routing Context
# =============================================================================


def test_get_routing_context():
    """Test getting routing context combines phase, skill, and progress."""
    with TestContext(plan_id='routing-plan'):
        _create_plan('routing-plan', 'Routing Test', '1-init,2-refine,3-outline,4-plan,5-execute,6-verify,7-finalize')
        result = run_script(LIFECYCLE_SCRIPT, 'get-routing-context', '--plan-id', 'routing-plan')
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        # Should have current phase
        assert data['current_phase'] == '1-init'
        # Should have skill routing
        assert data['skill'] == 'plan-init'
        # Should have progress
        assert 'total_phases' in data
        assert 'completed_phases' in data


def test_get_routing_context_after_transition():
    """Test routing context updates after phase transition."""
    with TestContext(plan_id='transition-routing'):
        _create_plan(
            'transition-routing', 'Transition Test', '1-init,2-refine,3-outline,4-plan,5-execute,6-verify,7-finalize'
        )
        run_script(LIFECYCLE_SCRIPT, 'transition', '--plan-id', 'transition-routing', '--completed', '1-init')
        result = run_script(LIFECYCLE_SCRIPT, 'get-routing-context', '--plan-id', 'transition-routing')
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['current_phase'] == '2-refine'
        assert data['skill'] == 'request-refine'
        assert data['completed_phases'] == 1


def test_get_routing_context_not_found():
    """Test get-routing-context with missing plan."""
    with TestContext():
        result = run_script(LIFECYCLE_SCRIPT, 'get-routing-context', '--plan-id', 'nonexistent')
        assert not result.success, 'Expected failure for missing plan'


# =============================================================================
# Test: List Command
# =============================================================================


def test_list_empty():
    """Test listing when no plans exist."""
    with TestContext():
        result = run_script(LIFECYCLE_SCRIPT, 'list')
        assert result.success, f'Script failed: {result.stderr}'


def test_list_with_plan():
    """Test listing when a plan exists."""
    with TestContext(plan_id='list-plan'):
        _create_plan('list-plan', 'List Test', 'init,execute,finalize')
        result = run_script(LIFECYCLE_SCRIPT, 'list')
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['total'] >= 1
        # Find our plan in the list
        plan_ids = [p['id'] for p in data['plans']]
        assert 'list-plan' in plan_ids


def test_list_with_filter():
    """Test listing with phase filter."""
    with TestContext(plan_id='filter-plan'):
        _create_plan('filter-plan', 'Filter Test', '1-init,2-refine,3-outline')
        # Filter for 1-init phase
        result = run_script(LIFECYCLE_SCRIPT, 'list', '--filter', '1-init')
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        # Should find the plan (it starts at 1-init)
        plan_ids = [p['id'] for p in data['plans']]
        assert 'filter-plan' in plan_ids


def test_list_with_filter_no_match():
    """Test listing with filter that doesn't match."""
    with TestContext(plan_id='nomatch-plan'):
        _create_plan('nomatch-plan', 'No Match Test', '1-init,2-refine')
        # Filter for a phase the plan isn't at
        result = run_script(LIFECYCLE_SCRIPT, 'list', '--filter', '5-execute')
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        # Should not find the plan
        plan_ids = [p['id'] for p in data['plans']]
        assert 'nomatch-plan' not in plan_ids


# =============================================================================
# Test: Transition Command
# =============================================================================


def test_transition_to_next_phase():
    """Test transitioning to the next phase."""
    with TestContext(plan_id='transition-plan'):
        _create_plan('transition-plan', 'Transition Test', '1-init,2-refine,3-outline')
        result = run_script(LIFECYCLE_SCRIPT, 'transition', '--plan-id', 'transition-plan', '--completed', '1-init')
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert data['completed_phase'] == '1-init'
        assert data['next_phase'] == '2-refine'


def test_transition_last_phase():
    """Test transitioning when completing the last phase."""
    with TestContext(plan_id='last-phase-plan'):
        _create_plan('last-phase-plan', 'Last Phase Test', '1-init,2-finalize')
        # Transition through all phases
        run_script(LIFECYCLE_SCRIPT, 'transition', '--plan-id', 'last-phase-plan', '--completed', '1-init')
        result = run_script(LIFECYCLE_SCRIPT, 'transition', '--plan-id', 'last-phase-plan', '--completed', '2-finalize')
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert data['completed_phase'] == '2-finalize'
        assert data['message'] == 'All phases completed'
        assert 'next_phase' not in data


def test_transition_invalid_phase():
    """Test transition with invalid phase name."""
    with TestContext(plan_id='invalid-transition'):
        _create_plan('invalid-transition', 'Invalid Test', '1-init,2-refine')
        result = run_script(
            LIFECYCLE_SCRIPT, 'transition', '--plan-id', 'invalid-transition', '--completed', 'nonexistent'
        )
        assert not result.success, 'Expected failure for invalid phase'
        data = parse_toon(result.stdout)
        assert data['status'] == 'error'
        assert data['error'] == 'invalid_phase'


def test_transition_not_found():
    """Test transition with non-existent plan."""
    with TestContext():
        result = run_script(LIFECYCLE_SCRIPT, 'transition', '--plan-id', 'nonexistent', '--completed', '1-init')
        assert not result.success, 'Expected failure for missing plan'


# =============================================================================
# Test: Route Command
# =============================================================================


def test_route_known_phase():
    """Test getting skill for a known phase."""
    with TestContext():
        result = run_script(LIFECYCLE_SCRIPT, 'route', '--phase', '1-init')
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert data['phase'] == '1-init'
        assert data['skill'] == 'plan-init'


def test_route_all_phases():
    """Test routing for all standard phases."""
    phases = {
        '1-init': 'plan-init',
        '2-refine': 'request-refine',
        '3-outline': 'solution-outline',
        '4-plan': 'task-plan',
        '5-execute': 'plan-execute',
        '6-verify': 'plan-verify',
        '7-finalize': 'plan-finalize',
    }
    with TestContext():
        for phase, expected_skill in phases.items():
            result = run_script(LIFECYCLE_SCRIPT, 'route', '--phase', phase)
            assert result.success, f'Script failed for {phase}: {result.stderr}'
            data = parse_toon(result.stdout)
            assert data['skill'] == expected_skill, f'Wrong skill for {phase}'


def test_route_unknown_phase():
    """Test routing for unknown phase."""
    with TestContext():
        result = run_script(LIFECYCLE_SCRIPT, 'route', '--phase', 'unknown-phase')
        assert not result.success, 'Expected failure for unknown phase'
        data = parse_toon(result.stdout)
        assert data['status'] == 'error'
        assert data['error'] == 'unknown_phase'


# =============================================================================
# Test: Archive Command
# =============================================================================


def test_archive_dry_run():
    """Test archive dry run mode."""
    with TestContext(plan_id='archive-plan'):
        _create_plan('archive-plan', 'Archive Test', '1-init,2-refine')
        result = run_script(LIFECYCLE_SCRIPT, 'archive', '--plan-id', 'archive-plan', '--dry-run')
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert data['dry_run'] is True
        assert 'would_archive_to' in data


def test_archive_not_found():
    """Test archive with non-existent plan."""
    with TestContext():
        result = run_script(LIFECYCLE_SCRIPT, 'archive', '--plan-id', 'nonexistent')
        assert not result.success, 'Expected failure for missing plan'
        data = parse_toon(result.stdout)
        assert data['status'] == 'error'
        assert data['error'] == 'not_found'
