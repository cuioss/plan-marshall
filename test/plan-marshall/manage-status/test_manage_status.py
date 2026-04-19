#!/usr/bin/env python3
"""Tests for manage-status.py script."""

import json
from argparse import Namespace
from pathlib import Path

import pytest

from conftest import PlanContext, get_script_path, run_script

# Script path for remaining subprocess (CLI plumbing) tests
SCRIPT_PATH = get_script_path('plan-marshall', 'manage-status', 'manage_status.py')

# Tier 2 direct imports via importlib (scripts loaded via PYTHONPATH at runtime)
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


_lifecycle = _load_module('_status_cmd_lifecycle', '_cmd_lifecycle.py')
_query = _load_module('_status_cmd_query', '_status_query.py')

cmd_create, cmd_delete_plan = _lifecycle.cmd_create, _lifecycle.cmd_delete_plan
cmd_transition = _lifecycle.cmd_transition
cmd_get_context = _query.cmd_get_context
cmd_metadata = _query.cmd_metadata
cmd_progress = _query.cmd_progress
cmd_read = _query.cmd_read
cmd_set_phase = _query.cmd_set_phase
cmd_update_phase = _query.cmd_update_phase

# =============================================================================
# Test: Create Command
# =============================================================================


def test_create_status(monkeypatch):
    """Test creating a status.json with standard 6-phase model."""
    with PlanContext(plan_id='test-plan') as ctx:
        # Pin HOME and credentials dir defensively so status creation
        # cannot leak into real host paths.
        monkeypatch.setenv('HOME', str(ctx.fixture_dir))
        monkeypatch.setenv('PLAN_MARSHALL_CREDENTIALS_DIR', str(ctx.fixture_dir / 'creds'))
        result = cmd_create(
            Namespace(
                plan_id='test-plan',
                title='Test Plan',
                phases='1-init,2-refine,3-outline,4-plan,5-execute,6-finalize',
                force=False,
            )
        )
        assert result['status'] == 'success'
        assert result['created'] is True
        assert result['plan']['title'] == 'Test Plan'
        assert result['plan']['current_phase'] == '1-init'


def test_create_status_custom_phases():
    """Test creating a status.json with custom phases."""
    with PlanContext(plan_id='custom-plan'):
        result = cmd_create(
            Namespace(plan_id='custom-plan', title='Custom Test', phases='init,execute,finalize', force=False)
        )
        assert result['status'] == 'success'


def test_create_status_force_overwrite():
    """Test force overwrite of existing status.json."""
    with PlanContext(plan_id='force-plan'):
        # Create first plan
        cmd_create(
            Namespace(plan_id='force-plan', title='Original Plan', phases='1-init,2-refine,3-outline', force=False)
        )
        # Create again with --force
        result = cmd_create(
            Namespace(plan_id='force-plan', title='Replaced Plan', phases='1-init,2-refine,3-outline', force=True)
        )
        assert result['status'] == 'success'
        assert result['plan']['title'] == 'Replaced Plan'


def test_create_status_already_exists():
    """Test create fails if status already exists without force."""
    with PlanContext(plan_id='exists-plan'):
        # Create first plan
        cmd_create(Namespace(plan_id='exists-plan', title='First Plan', phases='1-init,2-refine', force=False))
        # Try to create again without --force
        result = cmd_create(
            Namespace(plan_id='exists-plan', title='Second Plan', phases='1-init,2-refine', force=False)
        )
        assert result['status'] == 'error'
        assert result['error'] == 'file_exists'


def test_create_invalid_plan_id():
    """Test create fails with invalid plan_id (sys.exit(1) from require_valid_plan_id)."""
    with PlanContext():
        with pytest.raises(SystemExit) as exc_info:
            cmd_create(Namespace(plan_id='Invalid_Plan', title='Test', phases='1-init', force=False))
        assert exc_info.value.code == 0


# =============================================================================
# Test: Read Command
# =============================================================================


def test_read_status():
    """Test reading status.json."""
    with PlanContext(plan_id='read-plan'):
        cmd_create(Namespace(plan_id='read-plan', title='Read Test', phases='1-init,2-refine,3-outline', force=False))
        result = cmd_read(Namespace(plan_id='read-plan'))
        assert result['status'] == 'success'
        assert 'plan' in result
        assert result['plan']['title'] == 'Read Test'
        assert result['plan']['current_phase'] == '1-init'


def test_read_not_found():
    """Test read returns None for non-existent plan (TOON error already output)."""
    with PlanContext():
        result = cmd_read(Namespace(plan_id='nonexistent'))
        assert result is None


# =============================================================================
# Test: Set-Phase Command
# =============================================================================


def test_set_phase():
    """Test setting phase."""
    with PlanContext(plan_id='phase-plan'):
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


def test_set_phase_invalid():
    """Test set-phase fails for invalid phase."""
    with PlanContext(plan_id='invalid-phase-plan'):
        cmd_create(Namespace(plan_id='invalid-phase-plan', title='Test', phases='1-init,2-refine', force=False))
        result = cmd_set_phase(Namespace(plan_id='invalid-phase-plan', phase='nonexistent'))
        assert result['status'] == 'error'
        assert result['error'] == 'invalid_phase'


# =============================================================================
# Test: Update-Phase Command
# =============================================================================


def test_update_phase():
    """Test updating a specific phase status."""
    with PlanContext(plan_id='update-phase-plan'):
        cmd_create(
            Namespace(plan_id='update-phase-plan', title='Update Test', phases='1-init,2-refine,3-outline', force=False)
        )
        result = cmd_update_phase(Namespace(plan_id='update-phase-plan', phase='1-init', status='done'))
        assert result['status'] == 'success'
        assert result['phase'] == '1-init'
        assert result['phase_status'] == 'done'


def test_update_phase_not_found():
    """Test update-phase fails for non-existent phase."""
    with PlanContext(plan_id='update-notfound-plan'):
        cmd_create(Namespace(plan_id='update-notfound-plan', title='Test', phases='1-init,2-refine', force=False))
        result = cmd_update_phase(Namespace(plan_id='update-notfound-plan', phase='nonexistent', status='done'))
        assert result['status'] == 'error'
        assert result['error'] == 'phase_not_found'


# =============================================================================
# Test: Progress Command
# =============================================================================


def test_progress_initial():
    """Test progress calculation for initial state."""
    with PlanContext(plan_id='progress-plan'):
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


def test_progress_after_completion(monkeypatch):
    """Test progress calculation after completing phases."""
    with PlanContext(plan_id='progress-done-plan') as ctx:
        # Pin HOME and credentials dir defensively so progress calculation
        # cannot leak into real host paths.
        monkeypatch.setenv('HOME', str(ctx.fixture_dir))
        monkeypatch.setenv('PLAN_MARSHALL_CREDENTIALS_DIR', str(ctx.fixture_dir / 'creds'))
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
# Test: Metadata Commands
# =============================================================================


def test_metadata_set():
    """Test setting a metadata field."""
    with PlanContext(plan_id='metadata-plan'):
        cmd_create(Namespace(plan_id='metadata-plan', title='Metadata Test', phases='1-init,2-refine', force=False))
        result = cmd_metadata(
            Namespace(plan_id='metadata-plan', set=True, get=False, field='change_type', value='feature')
        )
        assert result['status'] == 'success'
        assert result['field'] == 'change_type'
        assert result['value'] == 'feature'


def test_metadata_get():
    """Test getting a metadata field."""
    with PlanContext(plan_id='metadata-get-plan'):
        cmd_create(Namespace(plan_id='metadata-get-plan', title='Metadata Test', phases='1-init,2-refine', force=False))
        # Set metadata first
        cmd_metadata(Namespace(plan_id='metadata-get-plan', set=True, get=False, field='change_type', value='bug_fix'))
        # Get metadata
        result = cmd_metadata(
            Namespace(plan_id='metadata-get-plan', set=False, get=True, field='change_type', value=None)
        )
        assert result['status'] == 'success'
        assert result['field'] == 'change_type'
        assert result['value'] == 'bug_fix'


def test_metadata_get_not_found():
    """Test getting a non-existent metadata field."""
    with PlanContext(plan_id='metadata-notfound-plan'):
        cmd_create(Namespace(plan_id='metadata-notfound-plan', title='Test', phases='1-init', force=False))
        result = cmd_metadata(
            Namespace(plan_id='metadata-notfound-plan', set=False, get=True, field='nonexistent', value=None)
        )
        assert result['status'] == 'not_found'
        assert result['field'] == 'nonexistent'


def test_metadata_update_existing():
    """Test updating an existing metadata field."""
    with PlanContext(plan_id='metadata-update-plan'):
        cmd_create(Namespace(plan_id='metadata-update-plan', title='Test', phases='1-init', force=False))
        # Set initial value
        cmd_metadata(
            Namespace(plan_id='metadata-update-plan', set=True, get=False, field='change_type', value='feature')
        )
        # Update value
        result = cmd_metadata(
            Namespace(plan_id='metadata-update-plan', set=True, get=False, field='change_type', value='bug_fix')
        )
        assert result['value'] == 'bug_fix'
        assert result['previous_value'] == 'feature'


# =============================================================================
# Test: Get-Context Command
# =============================================================================


def test_get_context():
    """Test get-context returns combined status context."""
    with PlanContext(plan_id='context-plan'):
        cmd_create(
            Namespace(
                plan_id='context-plan',
                title='Context Test',
                phases='1-init,2-refine,3-outline,4-plan',
                force=False,
            )
        )
        # Set some metadata
        cmd_metadata(Namespace(plan_id='context-plan', set=True, get=False, field='change_type', value='feature'))
        # Mark first phase as done
        cmd_update_phase(Namespace(plan_id='context-plan', phase='1-init', status='done'))
        cmd_set_phase(Namespace(plan_id='context-plan', phase='2-refine'))

        result = cmd_get_context(Namespace(plan_id='context-plan'))
        assert result['status'] == 'success'
        # Should have phase info
        assert result['current_phase'] == '2-refine'
        # Should have progress
        assert result['total_phases'] == 4
        assert result['completed_phases'] == 1
        # Should have metadata
        assert result['change_type'] == 'feature'


def test_get_context_not_found():
    """Test get-context returns None for missing plan (TOON error already output)."""
    with PlanContext():
        result = cmd_get_context(Namespace(plan_id='nonexistent'))
        assert result is None


# =============================================================================
# Test: JSON Storage Format
# =============================================================================


def test_json_storage_format():
    """Test that status is stored in JSON format."""
    with PlanContext(plan_id='json-plan') as ctx:
        cmd_create(Namespace(plan_id='json-plan', title='JSON Test', phases='1-init,2-refine,3-outline', force=False))
        # Directly read the status.json file
        status_file = ctx.plan_dir / 'status.json'
        assert status_file.exists(), 'status.json should exist'

        content = json.loads(status_file.read_text(encoding='utf-8'))
        assert content['title'] == 'JSON Test'
        assert content['current_phase'] == '1-init'
        assert len(content['phases']) == 3
        assert 'created' in content
        assert 'updated' in content


def test_json_phases_structure():
    """Test that phases are stored with correct structure."""
    with PlanContext(plan_id='phases-plan') as ctx:
        cmd_create(
            Namespace(plan_id='phases-plan', title='Phases Test', phases='1-init,2-refine,3-outline', force=False)
        )
        status_file = ctx.plan_dir / 'status.json'
        content = json.loads(status_file.read_text(encoding='utf-8'))

        # Check phases structure
        phases = content['phases']
        assert phases[0] == {'name': '1-init', 'status': 'in_progress'}
        assert phases[1] == {'name': '2-refine', 'status': 'pending'}
        assert phases[2] == {'name': '3-outline', 'status': 'pending'}


def test_json_metadata_structure():
    """Test that metadata is stored correctly."""
    with PlanContext(plan_id='metadata-json-plan') as ctx:
        cmd_create(Namespace(plan_id='metadata-json-plan', title='Metadata Test', phases='1-init', force=False))
        cmd_metadata(Namespace(plan_id='metadata-json-plan', set=True, get=False, field='change_type', value='feature'))

        status_file = ctx.plan_dir / 'status.json'
        content = json.loads(status_file.read_text(encoding='utf-8'))

        assert 'metadata' in content
        assert content['metadata']['change_type'] == 'feature'


# =============================================================================
# Test: Delete Plan
# =============================================================================


def test_delete_plan_success():
    """Test deleting an existing plan directory."""
    with PlanContext(plan_id='delete-test') as ctx:
        # Create some files in the plan
        (ctx.plan_dir / 'request.md').write_text('# Request')
        (ctx.plan_dir / 'references.json').write_text('{"branch": "main"}')
        (ctx.plan_dir / 'tasks').mkdir()
        (ctx.plan_dir / 'tasks' / 'TASK-001.toon').write_text('title: Test')

        result = cmd_delete_plan(Namespace(plan_id='delete-test'))
        assert result['status'] == 'success'
        assert result['action'] == 'deleted'
        assert result['plan_id'] == 'delete-test'
        assert result['files_removed'] == 3  # request.md, references.json, TASK-001.toon
        # Verify directory was deleted
        assert not ctx.plan_dir.exists()


def test_delete_plan_not_found():
    """Test deleting a plan that doesn't exist."""
    with PlanContext():
        result = cmd_delete_plan(Namespace(plan_id='nonexistent-plan'))
        assert result['status'] == 'error'
        assert result['error'] == 'plan_not_found'


def test_delete_plan_invalid_id():
    """Test delete-plan rejects invalid plan IDs (sys.exit(1) from require_valid_plan_id)."""
    with PlanContext():
        with pytest.raises(SystemExit) as exc_info:
            cmd_delete_plan(Namespace(plan_id='Invalid_Plan'))
        assert exc_info.value.code == 0


# =============================================================================
# CLI Plumbing Tests (Tier 3 - subprocess)
# =============================================================================


def test_cli_missing_required_args():
    """Test that missing required args produces exit code 2 (argparse error)."""
    with PlanContext():
        result = run_script(SCRIPT_PATH, 'create', '--plan-id', 'test-plan')
        # argparse exits with code 2 for missing required args (--title, --phases)
        assert not result.success


def test_cli_help_flag():
    """Test that --help produces exit code 0."""
    with PlanContext():
        result = run_script(SCRIPT_PATH, '--help')
        assert result.success


def test_cli_subcommand_help():
    """Test that subcommand --help produces exit code 0."""
    with PlanContext():
        result = run_script(SCRIPT_PATH, 'create', '--help')
        assert result.success


# =============================================================================
# Regression Tests: Not-found conditions exit 0 with TOON error
# =============================================================================


def test_cli_read_not_found_exits_zero():
    """Regression: read with missing status.json exits 0 with TOON error output."""
    with PlanContext():
        result = run_script(SCRIPT_PATH, 'read', '--plan-id', 'nonexistent')
        assert result.success, f'Should exit 0, got: {result.stderr}'
        assert 'status: error' in result.stdout
        assert 'file_not_found' in result.stdout


def test_cli_transition_not_found_exits_zero():
    """Regression: transition with missing status.json exits 0 with TOON error output."""
    with PlanContext():
        result = run_script(SCRIPT_PATH, 'transition', '--plan-id', 'nonexistent', '--completed', '1-init')
        assert result.success, f'Should exit 0, got: {result.stderr}'
        assert 'status: error' in result.stdout
        assert 'file_not_found' in result.stdout


# =============================================================================
# Regression Tests: cmd_transition(completed='5-execute') empty-diff guard
# =============================================================================
#
# A bug in the earlier lesson allowed cmd_transition to wipe a previously
# populated ``references.modified_files`` whenever ``git diff`` returned
# nothing (e.g., after a squash-merge reset the branch diff to empty). The
# fix added a guard: if the new diff is empty AND the existing list is
# non-empty, preserve the existing list; only replace when the new diff
# has entries (or the prior value is absent/empty). These tests pin both
# halves of that guard so neither branch regresses silently.


def _seed_execute_phase_plan(ctx, plan_id: str, modified_files: list) -> None:
    """Create a plan with 1-init done, 5-execute in_progress, base_branch set,
    and refs.modified_files pre-populated. Returns nothing; mutates the
    fixture directory directly.
    """
    cmd_create(
        Namespace(
            plan_id=plan_id,
            title='Transition Test',
            phases='1-init,2-refine,3-outline,4-plan,5-execute,6-finalize',
            force=False,
        )
    )
    # Advance phases until 5-execute is the current (in_progress) phase.
    for phase in ('1-init', '2-refine', '3-outline', '4-plan'):
        cmd_update_phase(Namespace(plan_id=plan_id, phase=phase, status='done'))
    cmd_set_phase(Namespace(plan_id=plan_id, phase='5-execute'))

    # Write references.json with a base_branch (required by the guard code
    # path) and the pre-populated modified_files we want to protect.
    refs = {
        'base_branch': 'main',
        'modified_files': list(modified_files),
    }
    refs_path = ctx.plan_dir / 'references.json'
    refs_path.write_text(json.dumps(refs), encoding='utf-8')


def _read_modified_files(ctx, plan_id: str) -> list:
    """Read ``references.modified_files`` back from disk for assertion."""
    refs_path = ctx.plan_dir / 'references.json'
    return json.loads(refs_path.read_text(encoding='utf-8'))['modified_files']


def test_transition_5_execute_preserves_modified_files_when_diff_empty(monkeypatch):
    """Regression: empty diff MUST NOT wipe a pre-populated modified_files.

    Stub ``_collect_modified_files`` on the lifecycle module so we can
    simulate a squash-merge scenario where ``git diff`` returns no
    entries. The guard in cmd_transition must preserve the existing list.
    """
    with PlanContext(plan_id='transition-guard-preserve') as ctx:
        _seed_execute_phase_plan(ctx, 'transition-guard-preserve', ['a', 'b', 'c'])

        # Act: stub the git collection to return empty, then transition.
        monkeypatch.setattr(_lifecycle, '_collect_modified_files', lambda *args, **kwargs: [])
        result = cmd_transition(
            Namespace(plan_id='transition-guard-preserve', completed='5-execute')
        )

        # Assert: transition succeeded AND the modified_files guard preserved
        # the pre-populated list despite the empty diff.
        assert result['status'] == 'success'
        preserved = _read_modified_files(ctx, 'transition-guard-preserve')
        assert preserved == ['a', 'b', 'c'], (
            f'Empty-diff guard failed: expected preserved [a,b,c], got {preserved}. '
            f'This regression means cmd_transition is wiping modified_files again.'
        )


def test_transition_5_execute_replaces_modified_files_when_diff_nonempty(monkeypatch):
    """Regression sibling: non-empty diff MUST replace the existing list.

    The guard only protects against empty-diff wipes — when git returns
    real entries, cmd_transition must update refs.modified_files to
    reflect the current branch state.
    """
    with PlanContext(plan_id='transition-guard-replace') as ctx:
        _seed_execute_phase_plan(ctx, 'transition-guard-replace', ['a', 'b', 'c'])

        # Act: stub the git collection to return ['x','y'], then transition.
        monkeypatch.setattr(
            _lifecycle, '_collect_modified_files', lambda *args, **kwargs: ['x', 'y']
        )
        result = cmd_transition(
            Namespace(plan_id='transition-guard-replace', completed='5-execute')
        )

        # Assert: transition succeeded AND the modified_files was replaced
        # with the new diff contents (not appended, not preserved).
        assert result['status'] == 'success'
        replaced = _read_modified_files(ctx, 'transition-guard-replace')
        assert replaced == ['x', 'y'], (
            f'Non-empty diff replacement failed: expected [x,y], got {replaced}. '
            f'The guard must only preserve on EMPTY diff — real diffs must win.'
        )


def test_cli_get_routing_context_not_found_exits_zero():
    """Regression: get-routing-context with missing status.json exits 0 with TOON error output."""
    with PlanContext():
        result = run_script(SCRIPT_PATH, 'get-routing-context', '--plan-id', 'nonexistent')
        assert result.success, f'Should exit 0, got: {result.stderr}'
        assert 'status: error' in result.stdout
        assert 'file_not_found' in result.stdout
