#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-status.py read + phase verbs + worktree-path resolution."""


import json
from argparse import Namespace

from _manage_status_read_fixtures import (
    cmd_create,
    cmd_get_worktree_path,
    cmd_progress,
    cmd_read,
    cmd_set_phase,
    cmd_update_phase,
)

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


# =============================================================================
# Test: cmd_get_worktree_path verb
# =============================================================================
#
# cmd_get_worktree_path resolves status.metadata into a tri-state response
# discriminated by `worktree_state`:
# - use_worktree==false (or metadata absent) →
#   worktree_state: disabled, worktree_path: ''
# - use_worktree==true and worktree_path set →
#   worktree_state: materialized, worktree_path: <abs>
# - use_worktree==true and worktree_path missing/empty →
#   worktree_state: pending, worktree_path: '', not_yet_materialized: true


def test_get_worktree_path_resolved_when_use_worktree_true(plan_context):
    """A materialized plan (worktree_path + branch persisted) → returns both.

    The path and branch are no longer seeded at create — phase-5-execute Step
    2.5 back-fills them at materialization. This test seeds the materialized
    metadata shape directly (also the shape a legacy plan carries) and asserts
    the verb reads it verbatim.
    """
    plan_id = 'wt-resolve-ok'
    abs_path = '/tmp/worktrees/wt-resolve-ok'
    branch = 'feature/wt-resolve-ok'
    cmd_create(
        Namespace(
            plan_id=plan_id,
            title='Resolve OK',
            phases='1-init,2-refine',
            force=False,
            use_worktree=True,
        )
    )
    # Simulate phase-5 materialization: back-fill worktree_path + branch.
    status_path = plan_context.plan_dir_for(plan_id) / 'status.json'
    status = json.loads(status_path.read_text(encoding='utf-8'))
    status['metadata'] = {
        'use_worktree': True,
        'worktree_path': abs_path,
        'worktree_branch': branch,
    }
    status_path.write_text(json.dumps(status), encoding='utf-8')

    result = cmd_get_worktree_path(Namespace(plan_id=plan_id))
    assert result['status'] == 'success'
    assert result['use_worktree'] is True
    assert result['worktree_state'] == 'materialized', (
        f'Expected worktree_state=materialized, got '
        f'{result.get("worktree_state")!r}.'
    )
    assert result['worktree_path'] == abs_path, (
        f'Expected resolved worktree_path={abs_path!r}, got '
        f'{result.get("worktree_path")!r}. The verb must read '
        f'metadata.worktree_path verbatim — no recomputation.'
    )
    assert result['worktree_branch'] == branch


def test_get_worktree_path_empty_when_use_worktree_false(plan_context):
    """use_worktree=false → returns empty string (NOT an error).

    Plans running against the main checkout legitimately have no worktree
    path; the verb's empty-string contract lets callers branch cleanly on a
    falsy value without parsing error envelopes.
    """
    plan_id = 'wt-resolve-false'
    cmd_create(
        Namespace(
            plan_id=plan_id,
            title='Resolve False',
            phases='1-init,2-refine',
            force=False,
            use_worktree=False,
        )
    )
    result = cmd_get_worktree_path(Namespace(plan_id=plan_id))
    assert result['status'] == 'success'
    assert result['use_worktree'] is False
    assert result['worktree_state'] == 'disabled', (
        f'Expected worktree_state=disabled, got '
        f'{result.get("worktree_state")!r}.'
    )
    assert result['worktree_path'] == '', (
        f"Expected empty worktree_path '', got "
        f'{result.get("worktree_path")!r}. use_worktree=false MUST yield '
        f'an empty string — never an error, never a missing key.'
    )
