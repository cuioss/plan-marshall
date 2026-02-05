#!/usr/bin/env python3
"""Tests for manage-status.py script."""

import json
import sys
from pathlib import Path

# Import shared infrastructure
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from conftest import PlanContext, get_script_path, run_script  # noqa: E402

# Get script path
SCRIPT_PATH = get_script_path('pm-workflow', 'manage-status', 'manage_status.py')

# Import toon_parser - conftest sets up PYTHONPATH
from toon_parser import parse_toon  # type: ignore[import-not-found]  # noqa: E402

# Alias for backward compatibility
TestContext = PlanContext


# =============================================================================
# Test: Create Command
# =============================================================================


def test_create_status():
    """Test creating a status.json with standard 7-phase model."""
    with TestContext(plan_id='test-plan'):
        result = run_script(
            SCRIPT_PATH,
            'create',
            '--plan-id',
            'test-plan',
            '--title',
            'Test Plan',
            '--phases',
            '1-init,2-refine,3-outline,4-plan,5-execute,6-verify,7-finalize',
        )
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert data['created'] is True
        assert data['plan']['title'] == 'Test Plan'
        assert data['plan']['current_phase'] == '1-init'


def test_create_status_custom_phases():
    """Test creating a status.json with custom phases."""
    with TestContext(plan_id='custom-plan'):
        result = run_script(
            SCRIPT_PATH,
            'create',
            '--plan-id',
            'custom-plan',
            '--title',
            'Custom Test',
            '--phases',
            'init,execute,finalize',
        )
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'


def test_create_status_force_overwrite():
    """Test force overwrite of existing status.json."""
    with TestContext(plan_id='force-plan'):
        # Create first plan
        run_script(
            SCRIPT_PATH,
            'create',
            '--plan-id',
            'force-plan',
            '--title',
            'Original Plan',
            '--phases',
            '1-init,2-refine,3-outline',
        )
        # Create again with --force
        result = run_script(
            SCRIPT_PATH,
            'create',
            '--plan-id',
            'force-plan',
            '--title',
            'Replaced Plan',
            '--phases',
            '1-init,2-refine,3-outline',
            '--force',
        )
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['plan']['title'] == 'Replaced Plan'


def test_create_status_already_exists():
    """Test create fails if status already exists without force."""
    with TestContext(plan_id='exists-plan'):
        # Create first plan
        run_script(
            SCRIPT_PATH,
            'create',
            '--plan-id',
            'exists-plan',
            '--title',
            'First Plan',
            '--phases',
            '1-init,2-refine',
        )
        # Try to create again without --force
        result = run_script(
            SCRIPT_PATH,
            'create',
            '--plan-id',
            'exists-plan',
            '--title',
            'Second Plan',
            '--phases',
            '1-init,2-refine',
        )
        assert not result.success, 'Expected failure for existing status'
        data = parse_toon(result.stdout)
        assert data['status'] == 'error'
        assert data['error'] == 'file_exists'


def test_create_invalid_plan_id():
    """Test create fails with invalid plan_id."""
    with TestContext():
        result = run_script(
            SCRIPT_PATH,
            'create',
            '--plan-id',
            'Invalid_Plan',  # uppercase not allowed
            '--title',
            'Test',
            '--phases',
            '1-init',
        )
        assert not result.success, 'Expected failure for invalid plan_id'
        data = parse_toon(result.stdout)
        assert data['status'] == 'error'
        assert data['error'] == 'invalid_plan_id'


# =============================================================================
# Test: Read Command
# =============================================================================


def test_read_status():
    """Test reading status.json."""
    with TestContext(plan_id='read-plan'):
        run_script(
            SCRIPT_PATH,
            'create',
            '--plan-id',
            'read-plan',
            '--title',
            'Read Test',
            '--phases',
            '1-init,2-refine,3-outline',
        )
        result = run_script(SCRIPT_PATH, 'read', '--plan-id', 'read-plan')
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert 'plan' in data
        assert data['plan']['title'] == 'Read Test'
        assert data['plan']['current_phase'] == '1-init'


def test_read_not_found():
    """Test read fails for non-existent plan."""
    with TestContext():
        result = run_script(SCRIPT_PATH, 'read', '--plan-id', 'nonexistent')
        assert not result.success, 'Expected failure for missing plan'
        data = parse_toon(result.stdout)
        assert data['status'] == 'error'
        assert data['error'] == 'file_not_found'


# =============================================================================
# Test: Set-Phase Command
# =============================================================================


def test_set_phase():
    """Test setting phase."""
    with TestContext(plan_id='phase-plan'):
        run_script(
            SCRIPT_PATH,
            'create',
            '--plan-id',
            'phase-plan',
            '--title',
            'Phase Test',
            '--phases',
            '1-init,2-refine,3-outline,4-plan,5-execute',
        )
        result = run_script(SCRIPT_PATH, 'set-phase', '--plan-id', 'phase-plan', '--phase', '3-outline')
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert data['current_phase'] == '3-outline'
        assert data['previous_phase'] == '1-init'


def test_set_phase_invalid():
    """Test set-phase fails for invalid phase."""
    with TestContext(plan_id='invalid-phase-plan'):
        run_script(
            SCRIPT_PATH,
            'create',
            '--plan-id',
            'invalid-phase-plan',
            '--title',
            'Test',
            '--phases',
            '1-init,2-refine',
        )
        result = run_script(SCRIPT_PATH, 'set-phase', '--plan-id', 'invalid-phase-plan', '--phase', 'nonexistent')
        assert not result.success, 'Expected failure for invalid phase'
        data = parse_toon(result.stdout)
        assert data['status'] == 'error'
        assert data['error'] == 'invalid_phase'


# =============================================================================
# Test: Update-Phase Command
# =============================================================================


def test_update_phase():
    """Test updating a specific phase status."""
    with TestContext(plan_id='update-phase-plan'):
        run_script(
            SCRIPT_PATH,
            'create',
            '--plan-id',
            'update-phase-plan',
            '--title',
            'Update Test',
            '--phases',
            '1-init,2-refine,3-outline',
        )
        result = run_script(
            SCRIPT_PATH, 'update-phase', '--plan-id', 'update-phase-plan', '--phase', '1-init', '--status', 'done'
        )
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert data['phase'] == '1-init'
        assert data['phase_status'] == 'done'


def test_update_phase_not_found():
    """Test update-phase fails for non-existent phase."""
    with TestContext(plan_id='update-notfound-plan'):
        run_script(
            SCRIPT_PATH,
            'create',
            '--plan-id',
            'update-notfound-plan',
            '--title',
            'Test',
            '--phases',
            '1-init,2-refine',
        )
        result = run_script(
            SCRIPT_PATH,
            'update-phase',
            '--plan-id',
            'update-notfound-plan',
            '--phase',
            'nonexistent',
            '--status',
            'done',
        )
        assert not result.success, 'Expected failure for non-existent phase'
        data = parse_toon(result.stdout)
        assert data['status'] == 'error'
        assert data['error'] == 'phase_not_found'


# =============================================================================
# Test: Progress Command
# =============================================================================


def test_progress_initial():
    """Test progress calculation for initial state."""
    with TestContext(plan_id='progress-plan'):
        run_script(
            SCRIPT_PATH,
            'create',
            '--plan-id',
            'progress-plan',
            '--title',
            'Progress Test',
            '--phases',
            '1-init,2-refine,3-outline,4-plan',
        )
        result = run_script(SCRIPT_PATH, 'progress', '--plan-id', 'progress-plan')
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert data['progress']['total_phases'] == 4
        assert data['progress']['completed_phases'] == 0
        assert data['progress']['percent'] == 0


def test_progress_after_completion():
    """Test progress calculation after completing phases."""
    with TestContext(plan_id='progress-done-plan'):
        run_script(
            SCRIPT_PATH,
            'create',
            '--plan-id',
            'progress-done-plan',
            '--title',
            'Progress Test',
            '--phases',
            '1-init,2-refine,3-outline,4-plan',
        )
        # Mark first two phases as done
        run_script(
            SCRIPT_PATH, 'update-phase', '--plan-id', 'progress-done-plan', '--phase', '1-init', '--status', 'done'
        )
        run_script(
            SCRIPT_PATH, 'update-phase', '--plan-id', 'progress-done-plan', '--phase', '2-refine', '--status', 'done'
        )
        result = run_script(SCRIPT_PATH, 'progress', '--plan-id', 'progress-done-plan')
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['progress']['completed_phases'] == 2
        assert data['progress']['percent'] == 50


# =============================================================================
# Test: Metadata Commands
# =============================================================================


def test_metadata_set():
    """Test setting a metadata field."""
    with TestContext(plan_id='metadata-plan'):
        run_script(
            SCRIPT_PATH,
            'create',
            '--plan-id',
            'metadata-plan',
            '--title',
            'Metadata Test',
            '--phases',
            '1-init,2-refine',
        )
        result = run_script(
            SCRIPT_PATH,
            'metadata',
            '--plan-id',
            'metadata-plan',
            '--set',
            '--field',
            'change_type',
            '--value',
            'feature',
        )
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert data['field'] == 'change_type'
        assert data['value'] == 'feature'


def test_metadata_get():
    """Test getting a metadata field."""
    with TestContext(plan_id='metadata-get-plan'):
        run_script(
            SCRIPT_PATH,
            'create',
            '--plan-id',
            'metadata-get-plan',
            '--title',
            'Metadata Test',
            '--phases',
            '1-init,2-refine',
        )
        # Set metadata first
        run_script(
            SCRIPT_PATH,
            'metadata',
            '--plan-id',
            'metadata-get-plan',
            '--set',
            '--field',
            'change_type',
            '--value',
            'bug_fix',
        )
        # Get metadata
        result = run_script(
            SCRIPT_PATH, 'metadata', '--plan-id', 'metadata-get-plan', '--get', '--field', 'change_type'
        )
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert data['field'] == 'change_type'
        assert data['value'] == 'bug_fix'


def test_metadata_get_not_found():
    """Test getting a non-existent metadata field."""
    with TestContext(plan_id='metadata-notfound-plan'):
        run_script(
            SCRIPT_PATH,
            'create',
            '--plan-id',
            'metadata-notfound-plan',
            '--title',
            'Test',
            '--phases',
            '1-init',
        )
        result = run_script(
            SCRIPT_PATH, 'metadata', '--plan-id', 'metadata-notfound-plan', '--get', '--field', 'nonexistent'
        )
        assert not result.success, 'Expected failure for missing metadata field'
        data = parse_toon(result.stdout)
        assert data['status'] == 'error'
        assert data['error'] == 'field_not_found'


def test_metadata_update_existing():
    """Test updating an existing metadata field."""
    with TestContext(plan_id='metadata-update-plan'):
        run_script(
            SCRIPT_PATH,
            'create',
            '--plan-id',
            'metadata-update-plan',
            '--title',
            'Test',
            '--phases',
            '1-init',
        )
        # Set initial value
        run_script(
            SCRIPT_PATH,
            'metadata',
            '--plan-id',
            'metadata-update-plan',
            '--set',
            '--field',
            'change_type',
            '--value',
            'feature',
        )
        # Update value
        result = run_script(
            SCRIPT_PATH,
            'metadata',
            '--plan-id',
            'metadata-update-plan',
            '--set',
            '--field',
            'change_type',
            '--value',
            'bug_fix',
        )
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['value'] == 'bug_fix'
        assert data['previous_value'] == 'feature'


# =============================================================================
# Test: Get-Context Command
# =============================================================================


def test_get_context():
    """Test get-context returns combined status context."""
    with TestContext(plan_id='context-plan'):
        run_script(
            SCRIPT_PATH,
            'create',
            '--plan-id',
            'context-plan',
            '--title',
            'Context Test',
            '--phases',
            '1-init,2-refine,3-outline,4-plan',
        )
        # Set some metadata
        run_script(
            SCRIPT_PATH,
            'metadata',
            '--plan-id',
            'context-plan',
            '--set',
            '--field',
            'change_type',
            '--value',
            'feature',
        )
        # Mark first phase as done
        run_script(SCRIPT_PATH, 'update-phase', '--plan-id', 'context-plan', '--phase', '1-init', '--status', 'done')
        run_script(SCRIPT_PATH, 'set-phase', '--plan-id', 'context-plan', '--phase', '2-refine')

        result = run_script(SCRIPT_PATH, 'get-context', '--plan-id', 'context-plan')
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        # Should have phase info
        assert data['current_phase'] == '2-refine'
        # Should have progress
        assert data['total_phases'] == 4
        assert data['completed_phases'] == 1
        # Should have metadata
        assert data['change_type'] == 'feature'


def test_get_context_not_found():
    """Test get-context with missing plan."""
    with TestContext():
        result = run_script(SCRIPT_PATH, 'get-context', '--plan-id', 'nonexistent')
        assert not result.success, 'Expected failure for missing plan'


# =============================================================================
# Test: JSON Storage Format
# =============================================================================


def test_json_storage_format(tmp_path):
    """Test that status is stored in JSON format."""
    with TestContext(plan_id='json-plan') as ctx:
        run_script(
            SCRIPT_PATH,
            'create',
            '--plan-id',
            'json-plan',
            '--title',
            'JSON Test',
            '--phases',
            '1-init,2-refine,3-outline',
        )
        # Directly read the status.json file
        status_file = ctx.plan_dir / 'status.json'
        assert status_file.exists(), 'status.json should exist'

        content = json.loads(status_file.read_text(encoding='utf-8'))
        assert content['title'] == 'JSON Test'
        assert content['current_phase'] == '1-init'
        assert len(content['phases']) == 3
        assert 'created' in content
        assert 'updated' in content


def test_json_phases_structure(tmp_path):
    """Test that phases are stored with correct structure."""
    with TestContext(plan_id='phases-plan') as ctx:
        run_script(
            SCRIPT_PATH,
            'create',
            '--plan-id',
            'phases-plan',
            '--title',
            'Phases Test',
            '--phases',
            '1-init,2-refine,3-outline',
        )
        status_file = ctx.plan_dir / 'status.json'
        content = json.loads(status_file.read_text(encoding='utf-8'))

        # Check phases structure
        phases = content['phases']
        assert phases[0] == {'name': '1-init', 'status': 'in_progress'}
        assert phases[1] == {'name': '2-refine', 'status': 'pending'}
        assert phases[2] == {'name': '3-outline', 'status': 'pending'}


def test_json_metadata_structure(tmp_path):
    """Test that metadata is stored correctly."""
    with TestContext(plan_id='metadata-json-plan') as ctx:
        run_script(
            SCRIPT_PATH,
            'create',
            '--plan-id',
            'metadata-json-plan',
            '--title',
            'Metadata Test',
            '--phases',
            '1-init',
        )
        run_script(
            SCRIPT_PATH,
            'metadata',
            '--plan-id',
            'metadata-json-plan',
            '--set',
            '--field',
            'change_type',
            '--value',
            'feature',
        )

        status_file = ctx.plan_dir / 'status.json'
        content = json.loads(status_file.read_text(encoding='utf-8'))

        assert 'metadata' in content
        assert content['metadata']['change_type'] == 'feature'
