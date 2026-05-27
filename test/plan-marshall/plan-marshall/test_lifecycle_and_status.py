#!/usr/bin/env python3
"""Tests for lifecycle commands in manage-status.py script.

Tests plan discovery, transitions, archiving, and routing (formerly manage-lifecycle).
"""

from conftest import get_script_path, run_script

# Get script paths
LIFECYCLE_SCRIPT = get_script_path('plan-marshall', 'manage-status', 'manage-status.py')
STATUS_SCRIPT = get_script_path('plan-marshall', 'manage-status', 'manage-status.py')

# Import toon_parser - conftest sets up PYTHONPATH
from toon_parser import parse_toon  # type: ignore[import-not-found]  # noqa: E402


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


def test_get_routing_context(plan_context):
    """Test getting routing context combines phase, skill, and progress."""
    _create_plan('routing-plan', 'Routing Test', '1-init,2-refine,3-outline,4-plan,5-execute,6-finalize')
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


def test_get_routing_context_after_transition(plan_context):
    """Test routing context updates after phase transition."""
    _create_plan('transition-routing', 'Transition Test', '1-init,2-refine,3-outline,4-plan,5-execute,6-finalize')
    run_script(LIFECYCLE_SCRIPT, 'transition', '--plan-id', 'transition-routing', '--completed', '1-init')
    result = run_script(LIFECYCLE_SCRIPT, 'get-routing-context', '--plan-id', 'transition-routing')
    assert result.success, f'Script failed: {result.stderr}'
    data = parse_toon(result.stdout)
    assert data['current_phase'] == '2-refine'
    assert data['skill'] == 'request-refine'
    assert data['completed_phases'] == 1


def test_get_routing_context_not_found(plan_context):
    """Test get-routing-context exits 0 with TOON error for missing plan."""
    result = run_script(LIFECYCLE_SCRIPT, 'get-routing-context', '--plan-id', 'nonexistent')
    assert result.success, 'Should exit 0 with TOON error output'
    assert 'status: error' in result.stdout


# =============================================================================
# Test: List Command
# =============================================================================


def test_list_empty(plan_context):
    """Test listing when no plans exist."""
    result = run_script(LIFECYCLE_SCRIPT, 'list')
    assert result.success, f'Script failed: {result.stderr}'


def test_list_with_plan(plan_context):
    """Test listing when a plan exists."""
    _create_plan('list-plan', 'List Test', 'init,execute,finalize')
    result = run_script(LIFECYCLE_SCRIPT, 'list')
    assert result.success, f'Script failed: {result.stderr}'
    data = parse_toon(result.stdout)
    assert data['total'] >= 1
    # Find our plan in the list
    plan_ids = [p['id'] for p in data['plans']]
    assert 'list-plan' in plan_ids


def test_list_with_filter(plan_context):
    """Test listing with phase filter."""
    _create_plan('filter-plan', 'Filter Test', '1-init,2-refine,3-outline')
    # Filter for 1-init phase
    result = run_script(LIFECYCLE_SCRIPT, 'list', '--filter', '1-init')
    assert result.success, f'Script failed: {result.stderr}'
    data = parse_toon(result.stdout)
    # Should find the plan (it starts at 1-init)
    plan_ids = [p['id'] for p in data['plans']]
    assert 'filter-plan' in plan_ids


def test_list_with_filter_no_match(plan_context):
    """Test listing with filter that doesn't match."""
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


def test_transition_to_next_phase(plan_context):
    """Test transitioning to the next phase."""
    _create_plan('transition-plan', 'Transition Test', '1-init,2-refine,3-outline')
    result = run_script(LIFECYCLE_SCRIPT, 'transition', '--plan-id', 'transition-plan', '--completed', '1-init')
    assert result.success, f'Script failed: {result.stderr}'
    data = parse_toon(result.stdout)
    assert data['status'] == 'success'
    assert data['completed_phase'] == '1-init'
    assert data['next_phase'] == '2-refine'


def test_transition_last_phase(plan_context):
    """Test transitioning when completing the last phase."""
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


def test_transition_invalid_phase(plan_context):
    """Test transition with invalid phase name."""
    _create_plan('invalid-transition', 'Invalid Test', '1-init,2-refine')
    result = run_script(
        LIFECYCLE_SCRIPT, 'transition', '--plan-id', 'invalid-transition', '--completed', 'nonexistent'
    )
    assert result.success, 'Expected exit 0 for expected error'
    data = parse_toon(result.stdout)
    assert data['status'] == 'error'
    assert data['error'] == 'invalid_phase'


def test_transition_not_found(plan_context):
    """Test transition exits 0 with TOON error for non-existent plan."""
    result = run_script(LIFECYCLE_SCRIPT, 'transition', '--plan-id', 'nonexistent', '--completed', '1-init')
    assert result.success, 'Should exit 0 with TOON error output'
    assert 'status: error' in result.stdout


# =============================================================================
# Test: Route Command
# =============================================================================


def test_route_known_phase(plan_context):
    """Test getting skill for a known phase."""
    result = run_script(LIFECYCLE_SCRIPT, 'route', '--phase', '1-init')
    assert result.success, f'Script failed: {result.stderr}'
    data = parse_toon(result.stdout)
    assert data['status'] == 'success'
    assert data['phase'] == '1-init'
    assert data['skill'] == 'plan-init'


def test_route_all_phases(plan_context):
    """Test routing for all standard phases."""
    phases = {
        '1-init': 'plan-init',
        '2-refine': 'request-refine',
        '3-outline': 'solution-outline',
        '4-plan': 'task-plan',
        '5-execute': 'plan-execute',
        '6-finalize': 'plan-finalize',
    }
    for phase, expected_skill in phases.items():
        result = run_script(LIFECYCLE_SCRIPT, 'route', '--phase', phase)
        assert result.success, f'Script failed for {phase}: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['skill'] == expected_skill, f'Wrong skill for {phase}'


def test_route_unknown_phase(plan_context):
    """Unknown ``--phase`` is rejected at the argparse boundary.

    The ``add_phase_arg`` builder wires ``choices=PHASES`` and the
    canonical ``parse_args_with_toon_errors`` handler maps the resulting
    argparse error (``argument --phase: invalid choice``) to
    ``status: error / error: invalid_phase`` TOON on stdout — see
    ``input_validation.py`` for the contract.
    """
    result = run_script(LIFECYCLE_SCRIPT, 'route', '--phase', 'unknown-phase')
    assert result.success, 'Expected exit 0 for expected error'
    data = parse_toon(result.stdout)
    assert data['status'] == 'error'
    assert data['error'] == 'invalid_phase'


# =============================================================================
# Test: Archive Command
# =============================================================================


def test_archive_dry_run(plan_context):
    """Test archive dry run mode."""
    _create_plan('archive-plan', 'Archive Test', '1-init,2-refine')
    result = run_script(LIFECYCLE_SCRIPT, 'archive', '--plan-id', 'archive-plan', '--dry-run')
    assert result.success, f'Script failed: {result.stderr}'
    data = parse_toon(result.stdout)
    assert data['status'] == 'success'
    assert data['dry_run'] is True
    assert 'would_archive_to' in data


def test_archive_not_found(plan_context):
    """Test archive with non-existent plan."""
    result = run_script(LIFECYCLE_SCRIPT, 'archive', '--plan-id', 'nonexistent')
    assert result.success, 'Expected exit 0 for expected error'
    data = parse_toon(result.stdout)
    assert data['status'] == 'error'
    assert data['error'] == 'not_found'
