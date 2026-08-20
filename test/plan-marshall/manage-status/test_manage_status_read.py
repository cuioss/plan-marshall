#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-status.py read: status, phase set/update, and progress."""


from argparse import Namespace

from _manage_status_read_fixtures import cmd_create, cmd_progress, cmd_read, cmd_set_phase, cmd_update_phase

# =============================================================================
# Test: Read Command
# =============================================================================


def test_read_status(plan_context):
    """Test reading status.json."""
    cmd_create(Namespace(plan_id='read-plan', title='Read Test', phases='1-init,2-refine,3-outline', force=False))
    result = cmd_read(Namespace(plan_id='read-plan'))
    assert result['status'] == 'success'
    assert 'plan' in result
    assert result['plan']['title'] == 'Read Test'
    assert result['plan']['current_phase'] == '1-init'


def test_read_not_found(plan_context):
    """Test read returns None for non-existent plan (TOON error already output)."""
    result = cmd_read(Namespace(plan_id='nonexistent'))
    assert result is None


# =============================================================================
# Test: Set-Phase Command
# =============================================================================


def test_set_phase(plan_context):
    """Test setting phase."""
    cmd_create(
        Namespace(
            plan_id='phase-plan',
            title='Phase Test',
            phases='1-init,2-refine,3-outline,4-plan,5-execute',
            force=False,
        )
    )
    result = cmd_set_phase(Namespace(plan_id='phase-plan', phase='3-outline'))
    assert result['status'] == 'success'
    assert result['current_phase'] == '3-outline'
    assert result['previous_phase'] == '1-init'


def test_set_phase_invalid(plan_context):
    """Test set-phase fails for invalid phase."""
    cmd_create(Namespace(plan_id='invalid-phase-plan', title='Test', phases='1-init,2-refine', force=False))
    result = cmd_set_phase(Namespace(plan_id='invalid-phase-plan', phase='nonexistent'))
    assert result['status'] == 'error'
    assert result['error'] == 'invalid_phase'


# =============================================================================
# Test: Update-Phase Command
# =============================================================================


def test_update_phase(plan_context):
    """Test updating a specific phase status."""
    cmd_create(
        Namespace(plan_id='update-phase-plan', title='Update Test', phases='1-init,2-refine,3-outline', force=False)
    )
    result = cmd_update_phase(Namespace(plan_id='update-phase-plan', phase='1-init', status='done'))
    assert result['status'] == 'success'
    assert result['phase'] == '1-init'
    assert result['phase_status'] == 'done'


def test_update_phase_not_found(plan_context):
    """Test update-phase fails for non-existent phase."""
    cmd_create(Namespace(plan_id='update-notfound-plan', title='Test', phases='1-init,2-refine', force=False))
    result = cmd_update_phase(Namespace(plan_id='update-notfound-plan', phase='nonexistent', status='done'))
    assert result['status'] == 'error'
    assert result['error'] == 'phase_not_found'


# =============================================================================
# Test: Progress Command
# =============================================================================


def test_progress_initial(plan_context):
    """Test progress calculation for initial state."""
    cmd_create(
        Namespace(
            plan_id='progress-plan', title='Progress Test', phases='1-init,2-refine,3-outline,4-plan', force=False
        )
    )
    result = cmd_progress(Namespace(plan_id='progress-plan'))
    assert result['status'] == 'success'
    assert result['progress']['total_phases'] == 4
    assert result['progress']['completed_phases'] == 0
    assert result['progress']['percent'] == 0


def test_progress_after_completion(plan_context, monkeypatch):
    """Test progress calculation after completing phases."""
    # Pin HOME and credentials dir defensively so progress calculation
    # cannot leak into real host paths.
    monkeypatch.setenv('HOME', str(plan_context.fixture_dir))
    monkeypatch.setenv('PLAN_MARSHALL_CREDENTIALS_DIR', str(plan_context.fixture_dir / 'creds'))
    cmd_create(
        Namespace(
            plan_id='progress-done-plan',
            title='Progress Test',
            phases='1-init,2-refine,3-outline,4-plan',
            force=False,
        )
    )
    # Mark first two phases as done
    cmd_update_phase(Namespace(plan_id='progress-done-plan', phase='1-init', status='done'))
    cmd_update_phase(Namespace(plan_id='progress-done-plan', phase='2-refine', status='done'))
    result = cmd_progress(Namespace(plan_id='progress-done-plan'))
    assert result['progress']['completed_phases'] == 2
    assert result['progress']['percent'] == 50
