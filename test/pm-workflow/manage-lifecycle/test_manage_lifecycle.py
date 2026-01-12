#!/usr/bin/env python3
"""Tests for manage-lifecycle.py script."""

import sys
from pathlib import Path

# Import shared infrastructure
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from conftest import run_script, TestRunner, get_script_path, PlanTestContext

# Get script path
SCRIPT_PATH = get_script_path('pm-workflow', 'manage-lifecycle', 'manage-lifecycle.py')

# Import toon_parser - conftest sets up PYTHONPATH
from toon_parser import parse_toon  # type: ignore[import-not-found]


# Alias for backward compatibility
TestContext = PlanTestContext


# =============================================================================
# Test: Create Command
# =============================================================================

def test_create_plan():
    """Test creating a plan with standard 5-phase model."""
    with TestContext(plan_id='test-plan'):
        result = run_script(SCRIPT_PATH, 'create',
            '--plan-id', 'test-plan',
            '--title', 'Test Plan',
            '--phases', 'init,outline,plan,execute,finalize'
        )
        assert result.success, f"Script failed: {result.stderr}"
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert data['plan']['title'] == 'Test Plan'
        assert data['plan']['current_phase'] == 'init'
        # Domain should NOT be in output (removed from status.toon)
        assert 'domain' not in data['plan']


def test_create_plan_custom_phases():
    """Test creating a plan with custom phases."""
    with TestContext(plan_id='custom-plan'):
        result = run_script(SCRIPT_PATH, 'create',
            '--plan-id', 'custom-plan',
            '--title', 'Custom Test',
            '--phases', 'init,execute,finalize'
        )
        assert result.success, f"Script failed: {result.stderr}"
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'


def test_create_plan_force_overwrite():
    """Test force overwrite of existing plan."""
    with TestContext(plan_id='force-plan'):
        # Create first plan
        run_script(SCRIPT_PATH, 'create',
            '--plan-id', 'force-plan',
            '--title', 'Original Plan',
            '--phases', 'init,outline,plan,execute,finalize'
        )
        # Create again with --force
        result = run_script(SCRIPT_PATH, 'create',
            '--plan-id', 'force-plan',
            '--title', 'Replaced Plan',
            '--phases', 'init,outline,plan,execute,finalize',
            '--force'
        )
        assert result.success, f"Script failed: {result.stderr}"
        data = parse_toon(result.stdout)
        assert data['plan']['title'] == 'Replaced Plan'


# =============================================================================
# Test: Phase Operations
# =============================================================================

def test_set_phase():
    """Test setting phase."""
    with TestContext(plan_id='phase-plan'):
        # First create the plan
        run_script(SCRIPT_PATH, 'create',
            '--plan-id', 'phase-plan',
            '--title', 'Phase Test',
            '--phases', 'init,outline,plan,execute,finalize'
        )
        # Then set phase
        result = run_script(SCRIPT_PATH, 'set-phase',
            '--plan-id', 'phase-plan',
            '--phase', 'execute'
        )
        assert result.success, f"Script failed: {result.stderr}"
        data = parse_toon(result.stdout)
        assert data['current_phase'] == 'execute'


def test_read_plan():
    """Test reading plan status."""
    with TestContext(plan_id='read-plan'):
        run_script(SCRIPT_PATH, 'create',
            '--plan-id', 'read-plan',
            '--title', 'Read Test',
            '--phases', 'init,outline,plan,execute,finalize'
        )
        result = run_script(SCRIPT_PATH, 'read',
            '--plan-id', 'read-plan'
        )
        assert result.success, f"Script failed: {result.stderr}"
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert 'plan' in data
        # Domain should NOT be in plan (removed from status.toon)
        assert 'domain' not in data['plan']


# =============================================================================
# Test: Get Routing Context
# =============================================================================

def test_get_routing_context():
    """Test getting routing context combines phase, skill, and progress."""
    with TestContext(plan_id='routing-plan'):
        run_script(SCRIPT_PATH, 'create',
            '--plan-id', 'routing-plan',
            '--title', 'Routing Test',
            '--phases', 'init,outline,plan,execute,finalize'
        )
        result = run_script(SCRIPT_PATH, 'get-routing-context',
            '--plan-id', 'routing-plan'
        )
        assert result.success, f"Script failed: {result.stderr}"
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        # Should have current phase
        assert data['current_phase'] == 'init'
        # Should have skill routing
        assert data['skill'] == 'plan-init'
        # Should have progress
        assert 'total_phases' in data
        assert 'completed_phases' in data
        # Domain should NOT be in routing context (removed from status.toon)
        assert 'domain' not in data


def test_get_routing_context_after_transition():
    """Test routing context updates after phase transition."""
    with TestContext(plan_id='transition-routing'):
        run_script(SCRIPT_PATH, 'create',
            '--plan-id', 'transition-routing',
            '--title', 'Transition Test',
            '--phases', 'init,outline,plan,execute,finalize'
        )
        run_script(SCRIPT_PATH, 'transition',
            '--plan-id', 'transition-routing',
            '--completed', 'init'
        )
        result = run_script(SCRIPT_PATH, 'get-routing-context',
            '--plan-id', 'transition-routing'
        )
        assert result.success, f"Script failed: {result.stderr}"
        data = parse_toon(result.stdout)
        assert data['current_phase'] == 'outline'
        assert data['skill'] == 'solution-outline'
        assert data['completed_phases'] == 1


def test_get_routing_context_not_found():
    """Test get-routing-context with missing plan."""
    with TestContext():
        result = run_script(SCRIPT_PATH, 'get-routing-context',
            '--plan-id', 'nonexistent'
        )
        assert not result.success, "Expected failure for missing plan"


# =============================================================================
# Test: List Command
# =============================================================================

def test_list_empty():
    """Test listing when no plans exist."""
    with TestContext():
        result = run_script(SCRIPT_PATH, 'list')
        assert result.success, f"Script failed: {result.stderr}"


def test_list_with_plan():
    """Test listing when a plan exists."""
    with TestContext(plan_id='list-plan'):
        run_script(SCRIPT_PATH, 'create',
            '--plan-id', 'list-plan',
            '--title', 'List Test',
            '--phases', 'init,execute,finalize'
        )
        result = run_script(SCRIPT_PATH, 'list')
        assert result.success, f"Script failed: {result.stderr}"
        data = parse_toon(result.stdout)
        assert data['total'] >= 1
        # Find our plan in the list
        plan_ids = [p['id'] for p in data['plans']]
        assert 'list-plan' in plan_ids
        # Domain should NOT be in list output (removed from status.toon)
        for plan in data['plans']:
            assert 'domain' not in plan


# =============================================================================
# Test Runner
# =============================================================================

if __name__ == '__main__':
    runner = TestRunner()
    runner.add_tests([
        # Create command
        test_create_plan,
        test_create_plan_custom_phases,
        test_create_plan_force_overwrite,
        # Phase operations
        test_set_phase,
        test_read_plan,
        # Get routing context
        test_get_routing_context,
        test_get_routing_context_after_transition,
        test_get_routing_context_not_found,
        # List command
        test_list_empty,
        test_list_with_plan,
    ])
    sys.exit(runner.run())
