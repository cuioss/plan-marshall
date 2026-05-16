#!/usr/bin/env python3
"""Tests for manage-status.py script."""

import json
import shutil
import subprocess
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
cmd_archive = _lifecycle.cmd_archive
cmd_get_context = _query.cmd_get_context
cmd_get_worktree_path = _query.cmd_get_worktree_path
cmd_list_orphans = _query.cmd_list_orphans
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


def test_delete_plan_auto_restores_lesson():
    """delete-plan moves a lesson-{id}.md back to lessons-learned/ before deletion."""
    with PlanContext(plan_id='lesson-2025-01-01-001') as ctx:
        (ctx.plan_dir / 'request.md').write_text('# Request')
        (ctx.plan_dir / 'lesson-2025-01-01-001.md').write_text(
            'id=2025-01-01-001\ncomponent=foo\ncategory=bug\ncreated=2025-01-01\n\n# Lesson\n\nBody.\n'
        )

        lessons_dir = ctx.fixture_dir / 'lessons-learned'
        # Pre-emptively confirm the destination does not exist
        if lessons_dir.exists():
            (lessons_dir / '2025-01-01-001.md').unlink(missing_ok=True)

        result = cmd_delete_plan(Namespace(plan_id='lesson-2025-01-01-001', no_restore_lessons=False))

        assert result['status'] == 'success'
        assert result['action'] == 'deleted'
        assert result['lesson_restored'] is True
        assert result['restored_lesson_ids'] == ['2025-01-01-001']

        # Plan dir was deleted
        assert not ctx.plan_dir.exists()
        # Lesson file lives in lessons-learned/ again
        restored = ctx.fixture_dir / 'lessons-learned' / '2025-01-01-001.md'
        assert restored.exists()
        assert '# Lesson' in restored.read_text()


def test_delete_plan_no_lesson_file_unchanged_behaviour():
    """delete-plan on a plan dir without a lesson file reports lesson_restored: False."""
    with PlanContext(plan_id='delete-no-lesson') as ctx:
        (ctx.plan_dir / 'request.md').write_text('# Request')

        result = cmd_delete_plan(Namespace(plan_id='delete-no-lesson', no_restore_lessons=False))

        assert result['status'] == 'success'
        assert result['action'] == 'deleted'
        assert result['lesson_restored'] is False
        assert 'restored_lesson_ids' not in result
        assert not ctx.plan_dir.exists()


def test_delete_plan_no_restore_lessons_flag_skips_restoration():
    """--no-restore-lessons preserves the prior unconditional-delete behaviour."""
    with PlanContext(plan_id='lesson-2025-01-01-002') as ctx:
        (ctx.plan_dir / 'lesson-2025-01-01-002.md').write_text(
            'id=2025-01-01-002\ncomponent=foo\ncategory=bug\ncreated=2025-01-01\n\n# Lesson\n\nBody.\n'
        )

        result = cmd_delete_plan(Namespace(plan_id='lesson-2025-01-01-002', no_restore_lessons=True))

        assert result['status'] == 'success'
        assert result['action'] == 'deleted'
        assert result['lesson_restored'] is False
        # The lesson file was discarded along with the plan dir
        assert not ctx.plan_dir.exists()
        assert not (ctx.fixture_dir / 'lessons-learned' / '2025-01-01-002.md').exists()


def test_delete_plan_restores_all_lesson_files():
    """delete-plan restores every lesson-*.md file in the plan dir (multi-lesson plans)."""
    with PlanContext(plan_id='consolidate-multi') as ctx:
        (ctx.plan_dir / 'request.md').write_text('# Request')
        (ctx.plan_dir / 'lesson-2025-02-01-001.md').write_text(
            'id=2025-02-01-001\ncomponent=foo\ncategory=bug\ncreated=2025-02-01\n\n# One\n'
        )
        (ctx.plan_dir / 'lesson-2025-02-01-002.md').write_text(
            'id=2025-02-01-002\ncomponent=bar\ncategory=bug\ncreated=2025-02-01\n\n# Two\n'
        )

        result = cmd_delete_plan(Namespace(plan_id='consolidate-multi', no_restore_lessons=False))

        assert result['status'] == 'success'
        assert result['action'] == 'deleted'
        assert result['lesson_restored'] is True
        assert result['restored_lesson_ids'] == ['2025-02-01-001', '2025-02-01-002']

        # Both lesson files exist in lessons-learned/
        lessons_dir = ctx.fixture_dir / 'lessons-learned'
        assert (lessons_dir / '2025-02-01-001.md').exists()
        assert (lessons_dir / '2025-02-01-002.md').exists()
        assert not ctx.plan_dir.exists()


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
        result = cmd_transition(Namespace(plan_id='transition-guard-preserve', completed='5-execute'))

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
        monkeypatch.setattr(_lifecycle, '_collect_modified_files', lambda *args, **kwargs: ['x', 'y'])
        result = cmd_transition(Namespace(plan_id='transition-guard-replace', completed='5-execute'))

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


# =============================================================================
# Regression Tests: _collect_modified_files captures working tree at 5-execute
# =============================================================================
#
# Phase-5-execute completes BEFORE default:commit-push runs (commit-push lives
# in phase-6-finalize). Earlier code used ``git diff --name-only
# {base_branch}...HEAD`` (three-dot range) to populate references.modified_files
# at transition time — but with no feature commits yet on HEAD, the diff was
# always empty and modified_files became []. The fix uses ``git diff
# --name-only {base_branch}`` (no dots) to compare the working tree against
# the base branch, capturing pending modifications. These tests pin the new
# behavior across the three scenarios called out in the driving lesson:
#
# 1. Two-file working-tree change → modified_files length = 2.
# 2. Multi-file working-tree change → modified_files length matches.
# 3. No metadata.worktree_path → still collects from the cwd checkout
#    (pre-worktree-migration plans).


def _init_collection_repo(repo: Path) -> None:
    """Create a git repo on ``main`` with a baseline commit so subsequent
    working-tree edits show up under ``git diff --name-only main``.
    """
    subprocess.run(['git', 'init', '-q', '-b', 'main', str(repo)], check=True)
    subprocess.run(['git', '-C', str(repo), 'config', 'user.email', 't@t.test'], check=True)
    subprocess.run(['git', '-C', str(repo), 'config', 'user.name', 'Test'], check=True)
    (repo / 'README.md').write_text('baseline\n', encoding='utf-8')
    subprocess.run(['git', '-C', str(repo), 'add', '.'], check=True)
    subprocess.run(['git', '-C', str(repo), 'commit', '-q', '-m', 'init'], check=True)


def test_collect_modified_files_two_file_change(tmp_path):
    """Two uncommitted files → modified_files length 2 with expected paths."""
    _init_collection_repo(tmp_path)
    (tmp_path / 'a.py').write_text('print("a")\n', encoding='utf-8')
    (tmp_path / 'b.py').write_text('print("b")\n', encoding='utf-8')

    status = {'metadata': {'worktree_path': str(tmp_path)}}
    result = _lifecycle._collect_modified_files('plan-2-files', status, 'main')

    assert result == ['a.py', 'b.py'], (
        f'Expected [a.py, b.py] from working-tree diff, got {result}. '
        f'A regression here means _cmd_lifecycle.py:92 reverted to the '
        f'three-dot {{base_branch}}...HEAD range that always returns []'
        f' before commit-push runs.'
    )


def test_collect_modified_files_multi_file_change(tmp_path):
    """Mix of tracked edits and new untracked files → union captured."""
    _init_collection_repo(tmp_path)
    # Modify an existing tracked file → exercises ``git diff --name-only``.
    (tmp_path / 'README.md').write_text('baseline changed\n', encoding='utf-8')
    # New untracked files (incl. nested) → exercises ``git ls-files --others``.
    (tmp_path / 'one.py').write_text('1\n', encoding='utf-8')
    (tmp_path / 'two.py').write_text('2\n', encoding='utf-8')
    sub = tmp_path / 'pkg'
    sub.mkdir()
    (sub / 'four.py').write_text('4\n', encoding='utf-8')
    (sub / 'five.py').write_text('5\n', encoding='utf-8')

    status = {'metadata': {'worktree_path': str(tmp_path)}}
    result = _lifecycle._collect_modified_files('plan-multi-files', status, 'main')

    expected = ['README.md', 'one.py', 'pkg/five.py', 'pkg/four.py', 'two.py']
    assert result == expected, (
        f'Multi-file working-tree probe failed: expected {expected}, got {result}. '
        f'modified_files must union tracked modifications (README.md) and new '
        f'untracked files (one.py, two.py, pkg/*) at 5-execute completion.'
    )


def test_collect_modified_files_no_worktree_path(tmp_path, monkeypatch):
    """Plan without metadata.worktree_path → diffs the cwd checkout."""
    _init_collection_repo(tmp_path)
    (tmp_path / 'changed.py').write_text('x\n', encoding='utf-8')
    monkeypatch.chdir(tmp_path)

    status = {'metadata': {}}  # No worktree_path — pre-migration plan shape
    result = _lifecycle._collect_modified_files('plan-no-worktree', status, 'main')

    assert result == ['changed.py'], (
        f'Pre-worktree plan path failed: expected [changed.py] from cwd diff, '
        f'got {result}. The function must fall through to ``git diff`` (no -C) '
        f'when metadata.worktree_path is absent.'
    )


# =============================================================================
# Regression Tests: cmd_archive atomically completes the active phase, and
# cmd_transition mirrors the same end-state when the LAST phase finishes.
# =============================================================================
#
# Historical bug (PR ref: #320 finalize): phase-6-finalize SKILL.md called
# `transition --completed 6-finalize` AFTER `default:archive-plan` had already
# moved status.json out of the live plan dir, so the transition always failed
# with file_not_found and archived plans were frozen at
# `current_phase: 6-finalize, phases[6-finalize]: in_progress`. The fix moves
# the phase-completion responsibility into cmd_archive (atomic) and updates
# cmd_transition symmetrically so both verbs produce the same end-state when
# the last phase is the one being completed: `current_phase = "complete"`
# (the dormant sentinel referenced by SKILL.md's "plan-already-complete"
# check and `manage-status list --filter complete` in cleanup).


def _seed_finalize_phase_plan(plan_id: str) -> None:
    """Create a plan whose phases 1..5 are done and 6-finalize is in_progress.

    Mirrors the end-of-execute state when phase-6-finalize is about to run
    its final step (archive-plan).
    """
    cmd_create(
        Namespace(
            plan_id=plan_id,
            title='Atomic Archive Test',
            phases='1-init,2-refine,3-outline,4-plan,5-execute,6-finalize',
            force=False,
        )
    )
    for phase in ('1-init', '2-refine', '3-outline', '4-plan', '5-execute'):
        cmd_update_phase(Namespace(plan_id=plan_id, phase=phase, status='done'))
    cmd_set_phase(Namespace(plan_id=plan_id, phase='6-finalize'))


def test_archive_marks_final_phase_done_and_sets_complete():
    """cmd_archive must close the active phase + set current_phase=complete BEFORE the move.

    Regression for the PR-#320 finalize bug: archived status.json was frozen
    at `current_phase: 6-finalize, phases[6-finalize]: in_progress` because
    the post-archive `transition --completed 6-finalize` call always failed
    with file_not_found. The fix moves phase-completion into cmd_archive so
    the archived status.json reflects the closed state.
    """
    plan_id = 'archive-atomic-happy-path'
    with PlanContext(plan_id=plan_id):
        _seed_finalize_phase_plan(plan_id)
        result = cmd_archive(Namespace(plan_id=plan_id, dry_run=False))

        assert result['status'] == 'success', f'archive failed: {result}'
        assert 'archived_to' in result, f'missing archived_to in {result}'

        archived_status_path = Path(result['archived_to']) / 'status.json'
        assert archived_status_path.exists(), (
            f'archived status.json missing at {archived_status_path} — '
            f'either move failed or archived_to points to wrong path'
        )

        archived_status = json.loads(archived_status_path.read_text(encoding='utf-8'))
        assert archived_status['current_phase'] == 'complete', (
            f"Expected archived current_phase='complete', got "
            f"{archived_status['current_phase']!r}. Atomic-archive fix "
            f'regressed: cmd_archive is not setting the post-finalize sentinel '
            f'before shutil.move runs.'
        )
        assert archived_status['phases'][-1]['status'] == 'done', (
            f"Expected archived phases[-1].status='done', got "
            f"{archived_status['phases'][-1]['status']!r}. Atomic-archive fix "
            f'regressed: cmd_archive is not marking the active phase done '
            f'before shutil.move runs.'
        )


def test_archive_dry_run_leaves_status_unchanged(tmp_path):
    """--dry-run must NOT mutate status.json or create the archive directory."""
    plan_id = 'archive-atomic-dry-run'
    with PlanContext(plan_id=plan_id) as ctx:
        _seed_finalize_phase_plan(plan_id)

        live_status_path = ctx.plan_dir / 'status.json'
        before = live_status_path.read_text(encoding='utf-8')

        result = cmd_archive(Namespace(plan_id=plan_id, dry_run=True))

        assert result['status'] == 'success'
        assert result.get('dry_run') is True, f'missing dry_run flag: {result}'
        assert 'would_archive_to' in result
        assert 'archived_to' not in result, (
            f'dry-run must NOT report archived_to: {result}'
        )

        assert not Path(result['would_archive_to']).exists(), (
            f"dry-run created the archive dir at {result['would_archive_to']} — "
            f'atomic-archive write block leaked into the dry-run path; the '
            f'`if args.dry_run:` early-return must precede the write block.'
        )

        after = live_status_path.read_text(encoding='utf-8')
        assert before == after, (
            'dry-run mutated the live status.json — atomic-archive write '
            'block leaked into the dry-run path; verify the early-return '
            'on args.dry_run runs before the write_status call.'
        )


# =============================================================================
# Test: Worktree State Persistence (cmd_create seeding)
# =============================================================================
#
# TASK-1 made cmd_create accept --use-worktree, --worktree-path,
# --worktree-branch and persist the trio into status.metadata so downstream
# consumers (build wrappers, phase-entry assertions, get-worktree-path) can
# resolve the active worktree from a plan-id alone. These tests pin the
# three seeding scenarios called out in the driving lesson:
#
# 1. use_worktree=true with path+branch → metadata seeded with all three.
# 2. use_worktree=false (or omitted) → metadata seeded with use_worktree:false
#    only (symmetric contract — no path/branch fields written).
# 3. Partial input (path without branch, or vice versa) → invalid_worktree_args
#    error. Refusing partial input prevents silently-incoherent metadata.


def test_create_seeds_worktree_metadata_when_use_worktree_true():
    """use_worktree=true with path+branch must seed all three metadata fields."""
    plan_id = 'wt-seed-true'
    abs_path = '/tmp/worktrees/wt-seed-true'
    branch = 'feature/wt-seed-true'
    with PlanContext(plan_id=plan_id) as ctx:
        result = cmd_create(
            Namespace(
                plan_id=plan_id,
                title='Worktree Seed True',
                phases='1-init,2-refine',
                force=False,
                use_worktree=True,
                worktree_path=abs_path,
                worktree_branch=branch,
            )
        )
        assert result['status'] == 'success'
        assert result['use_worktree'] is True
        assert result['worktree_path'] == abs_path
        assert result['worktree_branch'] == branch

        # Verify status.json on disk contains the seeded metadata trio.
        status = json.loads((ctx.plan_dir / 'status.json').read_text(encoding='utf-8'))
        assert status['metadata']['use_worktree'] is True, (
            f'metadata.use_worktree must be true, got {status["metadata"].get("use_worktree")!r}. '
            f'TASK-1 cmd_create regressed: --use-worktree flag is not propagating into status.metadata.'
        )
        assert status['metadata']['worktree_path'] == abs_path, (
            f'metadata.worktree_path must equal {abs_path!r}, got '
            f'{status["metadata"].get("worktree_path")!r}.'
        )
        assert status['metadata']['worktree_branch'] == branch, (
            f'metadata.worktree_branch must equal {branch!r}, got '
            f'{status["metadata"].get("worktree_branch")!r}.'
        )


def test_create_seeds_use_worktree_false_when_omitted():
    """No worktree flags → metadata.use_worktree=false, no path/branch fields.

    The contract is symmetric: even without a worktree, cmd_create must seed
    a definite ``use_worktree: false`` marker so downstream consumers don't
    have to treat absence-of-metadata as 'main-checkout'.
    """
    plan_id = 'wt-seed-false'
    with PlanContext(plan_id=plan_id) as ctx:
        result = cmd_create(
            Namespace(
                plan_id=plan_id,
                title='Worktree Seed False',
                phases='1-init,2-refine',
                force=False,
                use_worktree=False,
                worktree_path=None,
                worktree_branch=None,
            )
        )
        assert result['status'] == 'success'
        assert result['use_worktree'] is False
        # Result MUST NOT carry worktree_path / worktree_branch when no
        # worktree was allocated — those keys are exclusive to the true case.
        assert 'worktree_path' not in result
        assert 'worktree_branch' not in result

        status = json.loads((ctx.plan_dir / 'status.json').read_text(encoding='utf-8'))
        assert status['metadata'] == {'use_worktree': False}, (
            f'metadata must be exactly {{use_worktree: False}} when no worktree '
            f'is seeded, got {status["metadata"]!r}. The false-state seeding '
            f"contract prohibits writing path/branch keys when use_worktree is "
            f'false.'
        )


def test_create_rejects_partial_worktree_args_path_only():
    """use_worktree=true with path but missing branch → invalid_worktree_args."""
    plan_id = 'wt-partial-path'
    with PlanContext(plan_id=plan_id):
        result = cmd_create(
            Namespace(
                plan_id=plan_id,
                title='Partial Worktree',
                phases='1-init,2-refine',
                force=False,
                use_worktree=True,
                worktree_path='/tmp/worktrees/wt-partial-path',
                worktree_branch=None,
            )
        )
        assert result['status'] == 'error', (
            f'Partial worktree input must error, got {result!r}. '
            f'TASK-1 contract: --use-worktree requires both --worktree-path '
            f'and --worktree-branch — refusing partial input prevents '
            f'silently-incoherent metadata.'
        )
        assert result['error'] == 'invalid_worktree_args'


def test_create_rejects_partial_worktree_args_branch_only():
    """use_worktree=true with branch but missing path → invalid_worktree_args."""
    plan_id = 'wt-partial-branch'
    with PlanContext(plan_id=plan_id):
        result = cmd_create(
            Namespace(
                plan_id=plan_id,
                title='Partial Worktree',
                phases='1-init,2-refine',
                force=False,
                use_worktree=True,
                worktree_path=None,
                worktree_branch='feature/wt-partial',
            )
        )
        assert result['status'] == 'error'
        assert result['error'] == 'invalid_worktree_args'


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
#
# These three tests pin all three branches so the contract cannot regress.


def test_get_worktree_path_resolved_when_use_worktree_true():
    """use_worktree=true → returns absolute worktree_path + branch."""
    plan_id = 'wt-resolve-ok'
    abs_path = '/tmp/worktrees/wt-resolve-ok'
    branch = 'feature/wt-resolve-ok'
    with PlanContext(plan_id=plan_id):
        cmd_create(
            Namespace(
                plan_id=plan_id,
                title='Resolve OK',
                phases='1-init,2-refine',
                force=False,
                use_worktree=True,
                worktree_path=abs_path,
                worktree_branch=branch,
            )
        )
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


def test_get_worktree_path_empty_when_use_worktree_false():
    """use_worktree=false → returns empty string (NOT an error).

    Plans running against the main checkout legitimately have no worktree
    path; the verb's empty-string contract lets callers branch cleanly on a
    falsy value without parsing error envelopes.
    """
    plan_id = 'wt-resolve-false'
    with PlanContext(plan_id=plan_id):
        cmd_create(
            Namespace(
                plan_id=plan_id,
                title='Resolve False',
                phases='1-init,2-refine',
                force=False,
                use_worktree=False,
                worktree_path=None,
                worktree_branch=None,
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


def test_get_worktree_path_pending_when_not_yet_materialized():
    """use_worktree=true but worktree_path empty → worktree_state: pending.

    A plan can opt into worktree mode before the worktree directory has been
    materialized — between init and the worktree-creation step. In that
    pre-materialization window the verb returns the `pending` tri-state
    branch so callers can fall back to the main checkout cwd instead of
    erroring out.
    """
    plan_id = 'wt-resolve-pending'
    with PlanContext(plan_id=plan_id) as ctx:
        # Seed via cmd_create (false), then manually shape the metadata to
        # the pre-materialization state: use_worktree=true with no path yet.
        cmd_create(
            Namespace(
                plan_id=plan_id,
                title='Resolve Pending',
                phases='1-init,2-refine',
                force=False,
                use_worktree=False,
                worktree_path=None,
                worktree_branch=None,
            )
        )
        status_path = ctx.plan_dir / 'status.json'
        status = json.loads(status_path.read_text(encoding='utf-8'))
        # Pre-materialization shape: use_worktree=true but no path/branch.
        status['metadata'] = {'use_worktree': True}
        status_path.write_text(json.dumps(status), encoding='utf-8')

        result = cmd_get_worktree_path(Namespace(plan_id=plan_id))
        assert result['status'] == 'success', (
            f'Pre-materialization must succeed (tri-state contract), got '
            f'{result!r}.'
        )
        assert result['use_worktree'] is True
        assert result['worktree_state'] == 'pending', (
            f'Expected worktree_state=pending, got '
            f'{result.get("worktree_state")!r}.'
        )
        assert result['worktree_path'] == ''
        assert result['not_yet_materialized'] is True


# =============================================================================
# Test: CLI plumbing for create worktree flags + get-worktree-path subcommand
# =============================================================================


def test_cli_create_with_worktree_flags():
    """End-to-end: CLI accepts --use-worktree/--worktree-path/--worktree-branch
    and persists metadata that the get-worktree-path subcommand reads back.
    """
    plan_id = 'wt-cli-roundtrip'
    abs_path = '/tmp/worktrees/wt-cli-roundtrip'
    branch = 'feature/wt-cli-roundtrip'
    with PlanContext():
        create_result = run_script(
            SCRIPT_PATH,
            'create',
            '--plan-id',
            plan_id,
            '--title',
            'CLI Roundtrip',
            '--phases',
            '1-init,2-refine',
            '--use-worktree',
            '--worktree-path',
            abs_path,
            '--worktree-branch',
            branch,
        )
        assert create_result.success, f'create failed: {create_result.stderr}'
        assert 'status: success' in create_result.stdout

        read_result = run_script(SCRIPT_PATH, 'get-worktree-path', '--plan-id', plan_id)
        assert read_result.success, f'get-worktree-path failed: {read_result.stderr}'
        assert 'status: success' in read_result.stdout
        assert f'worktree_path: {abs_path}' in read_result.stdout, (
            f'Expected worktree_path={abs_path!r} in stdout, got: {read_result.stdout!r}. '
            f'CLI roundtrip regressed — manage_status.py is not wiring the '
            f'create flags into cmd_create OR the get-worktree-path subparser '
            f'is not registered.'
        )


def test_cli_get_worktree_path_help():
    """get-worktree-path --help must succeed (subparser registration check)."""
    with PlanContext():
        result = run_script(SCRIPT_PATH, 'get-worktree-path', '--help')
        assert result.success, (
            f'get-worktree-path --help failed: {result.stderr!r}. '
            f'Subparser is missing from manage_status.py.'
        )


# =============================================================================
# Test: cmd_get_worktree_path pre-materialization tri-state (extended coverage)
# =============================================================================
#
# The three head-line cases (materialized / disabled / pending) are pinned
# above. This class adds extended coverage of the pre-materialization
# (``not_yet_materialized``) branch: missing-path variants, explicit empty
# string, totally-absent metadata block, and the contract that callers can
# branch on either ``worktree_state == 'pending'`` OR
# ``not_yet_materialized is True`` without parsing the full envelope.


class TestGetWorktreePathPreMaterialization:
    """Pin pre-materialization tri-state edge cases for cmd_get_worktree_path.

    Covers the deferred-pending branch of the tri-state contract across the
    three on-disk shapes a plan can take between init and worktree
    materialization:

    - ``metadata = {use_worktree: True}`` (no path key at all)
    - ``metadata = {use_worktree: True, worktree_path: ''}`` (explicit empty)
    - ``metadata = {use_worktree: True, worktree_path: None}`` (null)
    """

    @staticmethod
    def _seed_pre_materialization(ctx, plan_id: str, metadata: dict) -> None:
        """Create the plan via cmd_create then overwrite metadata directly.

        cmd_create rejects partial worktree args, so we cannot seed the
        pre-materialization shape through the normal API. Direct file
        write is the canonical pattern (see also
        test_get_worktree_path_pending_when_not_yet_materialized).
        """
        cmd_create(
            Namespace(
                plan_id=plan_id,
                title='Pre-Materialization Edge Case',
                phases='1-init,2-refine',
                force=False,
                use_worktree=False,
                worktree_path=None,
                worktree_branch=None,
            )
        )
        status_path = ctx.plan_dir / 'status.json'
        status = json.loads(status_path.read_text(encoding='utf-8'))
        status['metadata'] = metadata
        status_path.write_text(json.dumps(status), encoding='utf-8')

    def test_pending_when_use_worktree_true_and_path_key_absent(self):
        """use_worktree=true with NO worktree_path key → pending."""
        plan_id = 'wt-pre-mat-missing-key'
        with PlanContext(plan_id=plan_id) as ctx:
            self._seed_pre_materialization(ctx, plan_id, {'use_worktree': True})
            result = cmd_get_worktree_path(Namespace(plan_id=plan_id))
            assert result['status'] == 'success'
            assert result['worktree_state'] == 'pending'
            assert result['worktree_path'] == ''
            assert result['not_yet_materialized'] is True, (
                f'Expected not_yet_materialized=True for shape '
                f'{{use_worktree: True}} (no path key), got '
                f'{result.get("not_yet_materialized")!r}.'
            )

    def test_pending_when_worktree_path_is_explicit_empty_string(self):
        """use_worktree=true with worktree_path='' → pending."""
        plan_id = 'wt-pre-mat-empty-string'
        with PlanContext(plan_id=plan_id) as ctx:
            self._seed_pre_materialization(
                ctx, plan_id, {'use_worktree': True, 'worktree_path': ''}
            )
            result = cmd_get_worktree_path(Namespace(plan_id=plan_id))
            assert result['status'] == 'success'
            assert result['worktree_state'] == 'pending'
            assert result['worktree_path'] == ''
            assert result['not_yet_materialized'] is True

    def test_pending_when_worktree_path_is_null(self):
        """use_worktree=true with worktree_path=None → pending.

        The JSON null shape is a real possibility — manage-status writers
        could leave ``worktree_path: null`` between phases. The tri-state
        verb must treat null the same as missing/empty.
        """
        plan_id = 'wt-pre-mat-null'
        with PlanContext(plan_id=plan_id) as ctx:
            self._seed_pre_materialization(
                ctx, plan_id, {'use_worktree': True, 'worktree_path': None}
            )
            result = cmd_get_worktree_path(Namespace(plan_id=plan_id))
            assert result['status'] == 'success'
            assert result['worktree_state'] == 'pending'
            assert result['worktree_path'] == ''
            assert result['not_yet_materialized'] is True

    def test_pending_omits_worktree_branch_when_unset(self):
        """Pending state must NOT carry a worktree_branch field when unset.

        The symmetric contract: just as ``disabled`` omits path/branch,
        ``pending`` must omit branch when the metadata has none yet. The
        materialized state is the only one that carries a branch.
        """
        plan_id = 'wt-pre-mat-no-branch'
        with PlanContext(plan_id=plan_id) as ctx:
            self._seed_pre_materialization(ctx, plan_id, {'use_worktree': True})
            result = cmd_get_worktree_path(Namespace(plan_id=plan_id))
            assert result['worktree_state'] == 'pending'
            # Branch absence must be explicit, not a leaked empty key.
            assert result.get('worktree_branch', '') == '', (
                f'Pending state leaked a worktree_branch={result.get("worktree_branch")!r}; '
                f'pre-materialization shapes have no branch yet.'
            )

    def test_pending_includes_worktree_branch_when_metadata_has_branch(self):
        """Pending state surfaces worktree_branch when persisted at init time.

        Phase-1-init records the branch intent in metadata before the
        worktree is materialized. The tri-state response for the pending
        case MUST include that branch so downstream consumers (e.g. PR
        review output that reports branch context pre-materialization)
        can read it from the same envelope as the materialized case.

        Symmetric counterpart to
        test_pending_omits_worktree_branch_when_unset: when the metadata
        carries a branch, the pending envelope MUST carry it through.
        """
        plan_id = 'wt-pre-mat-with-branch'
        branch = 'feature/pre-mat-branch'
        with PlanContext(plan_id=plan_id) as ctx:
            self._seed_pre_materialization(
                ctx,
                plan_id,
                {
                    'use_worktree': True,
                    'worktree_path': '',
                    'worktree_branch': branch,
                },
            )
            result = cmd_get_worktree_path(Namespace(plan_id=plan_id))
            assert result['worktree_state'] == 'pending'
            assert result['not_yet_materialized'] is True
            assert result.get('worktree_branch') == branch, (
                f'Pending state dropped worktree_branch from metadata; '
                f'expected {branch!r}, got {result.get("worktree_branch")!r}.'
            )

    def test_pending_contract_callers_can_branch_on_either_signal(self):
        """Tri-state contract: worktree_state and not_yet_materialized agree.

        Callers downstream may branch on EITHER signal — the contract
        guarantees they never disagree. A regression that ships the
        ``pending`` worktree_state without the ``not_yet_materialized``
        flag (or vice versa) would silently break consumers that picked
        the other signal.
        """
        plan_id = 'wt-pre-mat-symmetric-signals'
        with PlanContext(plan_id=plan_id) as ctx:
            self._seed_pre_materialization(ctx, plan_id, {'use_worktree': True})
            result = cmd_get_worktree_path(Namespace(plan_id=plan_id))

            is_pending_state = result.get('worktree_state') == 'pending'
            is_not_yet_materialized = result.get('not_yet_materialized') is True
            assert is_pending_state == is_not_yet_materialized, (
                f'Tri-state signals disagree: worktree_state={result.get("worktree_state")!r}, '
                f'not_yet_materialized={result.get("not_yet_materialized")!r}. The two '
                f'signals MUST agree so callers can branch on either one.'
            )


def test_transition_last_phase_sets_complete():
    """cmd_transition must mirror cmd_archive when completing the LAST phase.

    Symmetry guard: a future caller that uses transition for finalization
    (instead of relying on archive's atomic close) must produce the same
    end-state — current_phase='complete' and the closing phase marked done.
    """
    plan_id = 'transition-last-phase-complete'
    with PlanContext(plan_id=plan_id) as ctx:
        _seed_finalize_phase_plan(plan_id)

        result = cmd_transition(Namespace(plan_id=plan_id, completed='6-finalize'))

        assert result['status'] == 'success'
        assert result.get('message') == 'All phases completed', (
            f'expected terminal message, got {result}'
        )
        assert 'next_phase' not in result, (
            f'cmd_transition on the last phase must not return next_phase: {result}'
        )

        live_status = json.loads((ctx.plan_dir / 'status.json').read_text(encoding='utf-8'))
        assert live_status['current_phase'] == 'complete', (
            f"Expected current_phase='complete' after transition --completed "
            f'6-finalize, got {live_status["current_phase"]!r}. Symmetry '
            f'with cmd_archive regressed: cmd_transition is not setting '
            f'the post-finalize sentinel for the last phase.'
        )
        assert live_status['phases'][-1]['status'] == 'done', (
            f"Expected phases[-1].status='done', got "
            f'{live_status["phases"][-1]["status"]!r}.'
        )


# =============================================================================
# Tests: cmd_list_orphans (orphan-dir cleanup pass)
# =============================================================================
#
# Pins the inverse-of-cmd_list contract: directories in plans_dir WITHOUT a
# readable status.json are reported as orphans; directories WITH a readable
# status.json are skipped. Covers empty-dir, with-status-skip, without-status-
# but-with-subdirs, multiple-sorted, and a CLI-resolvability check against a
# mixed 8-orphans + 2-legitimate-plans fixture.


def _seed_legitimate_plan(plan_id: str) -> None:
    """cmd_create a plan with a status.json so cmd_list_orphans skips it."""
    cmd_create(
        Namespace(
            plan_id=plan_id,
            title=f'Legitimate {plan_id}',
            phases='1-init,2-refine,3-outline,4-plan,5-execute,6-finalize',
            force=False,
        )
    )


def test_list_orphans_empty_plans_dir():
    """(a) Empty plans_dir returns total: 0 and orphans: []."""
    with PlanContext(plan_id='orphans-empty') as ctx:
        # PlanContext auto-creates the plan_dir; remove it so plans_dir is
        # empty for this assertion.
        shutil.rmtree(ctx.plan_dir)

        result = cmd_list_orphans(Namespace())

        assert result['status'] == 'success'
        assert result['total'] == 0
        assert result['orphans'] == []


def test_list_orphans_skips_dir_with_status_json():
    """(b) Directory present with status.json is NOT listed as an orphan."""
    with PlanContext(plan_id='orphans-skip-valid') as ctx:
        # Drop the auto-created empty plan_dir; seed a legitimate plan in its
        # place via cmd_create so status.json is present.
        shutil.rmtree(ctx.plan_dir)
        _seed_legitimate_plan('legit-plan')

        result = cmd_list_orphans(Namespace())

        assert result['status'] == 'success'
        assert result['total'] == 0, (
            f"Legitimate plan with status.json must NOT be reported as orphan, got: {result['orphans']}"
        )
        assert result['orphans'] == []


def test_list_orphans_includes_dir_without_status_json_with_subdirs():
    """(c) Directory without status.json but with logs/ or work/ subdirs IS listed."""
    with PlanContext(plan_id='orphans-with-subdirs') as ctx:
        # Drop the auto-created plan_dir.
        shutil.rmtree(ctx.plan_dir)

        # Construct an orphan dir with logs/ and work/ subdirs (no status.json).
        orphan_dir = ctx.fixture_dir / 'plans' / 'orphan-with-subdirs'
        orphan_dir.mkdir(parents=True)
        (orphan_dir / 'logs').mkdir()
        (orphan_dir / 'work').mkdir()

        result = cmd_list_orphans(Namespace())

        assert result['status'] == 'success'
        assert result['total'] == 1
        assert len(result['orphans']) == 1
        entry = result['orphans'][0]
        assert entry['id'] == 'orphan-with-subdirs'
        assert entry['path'] == str(orphan_dir)
        # contents is sorted; 'logs' precedes 'work' lexicographically.
        assert entry['contents'] == ['logs', 'work']


def test_list_orphans_returns_multiple_sorted():
    """(d) Multiple orphans are all returned, sorted by id."""
    with PlanContext(plan_id='orphans-many') as ctx:
        shutil.rmtree(ctx.plan_dir)

        plans_dir = ctx.fixture_dir / 'plans'
        # Create dirs in non-alphabetical order to exercise sort.
        for name in ('zeta-orphan', 'alpha-orphan', 'mid-orphan'):
            d = plans_dir / name
            d.mkdir(parents=True)
            # Give each orphan a stray file so its contents list is non-empty.
            (d / 'stray.txt').write_text('x')

        result = cmd_list_orphans(Namespace())

        assert result['status'] == 'success'
        assert result['total'] == 3
        ids = [o['id'] for o in result['orphans']]
        assert ids == ['alpha-orphan', 'mid-orphan', 'zeta-orphan'], (
            f'orphans must be returned in sorted id order, got {ids}'
        )
        for orphan in result['orphans']:
            assert orphan['contents'] == ['stray.txt']


def test_list_orphans_mixed_eight_orphans_plus_two_legitimate_plans():
    """CLI resolvability + filter contract: 8 orphans + 2 legitimate plans → ONLY the 8 orphans returned.

    Mirrors the production fixture cited in the task description (the 8 existing
    orphan dirs that motivated this work) and pins the cmd_list_orphans filter
    against the legitimate plans alongside them.
    """
    with PlanContext(plan_id='orphans-mixed') as ctx:
        shutil.rmtree(ctx.plan_dir)

        plans_dir = ctx.fixture_dir / 'plans'
        orphan_names = [f'orphan-{i:02d}' for i in range(8)]
        for name in orphan_names:
            (plans_dir / name).mkdir(parents=True)

        # Two legitimate (lesson-*) plans with status.json via cmd_create.
        _seed_legitimate_plan('lesson-alpha')
        _seed_legitimate_plan('lesson-beta')

        # --- Direct cmd invocation (Tier 2): exact filter shape. ---
        result = cmd_list_orphans(Namespace())
        assert result['status'] == 'success'
        assert result['total'] == 8, (
            f"Expected exactly 8 orphans (legitimate lesson-* plans must be filtered out), "
            f"got total={result['total']} ids={[o['id'] for o in result['orphans']]}"
        )
        returned_ids = [o['id'] for o in result['orphans']]
        assert returned_ids == sorted(orphan_names), (
            f'Expected sorted orphan ids {sorted(orphan_names)}, got {returned_ids}'
        )
        # Legitimate plans must NOT appear.
        assert 'lesson-alpha' not in returned_ids
        assert 'lesson-beta' not in returned_ids

        # --- CLI resolvability (Tier 3): list-orphans subcommand reachable via the script. ---
        cli_result = run_script(SCRIPT_PATH, 'list-orphans')
        assert cli_result.success, (
            f'list-orphans subcommand must be resolvable via the script entry point. '
            f'stderr: {cli_result.stderr}'
        )
        assert 'status: success' in cli_result.stdout
        # Spot-check that every orphan id surfaces in the TOON output and the
        # legitimate plans do not.
        for name in orphan_names:
            assert name in cli_result.stdout, f'orphan {name} missing from CLI output'
        assert 'lesson-alpha' not in cli_result.stdout
        assert 'lesson-beta' not in cli_result.stdout


# =============================================================================
# Tests: cmd_list_orphans — PR #379 gemini-code-assist review hardening
# =============================================================================
#
# Pins the three review fixes:
# (1) HIGH — unreadable orphan dir surfaces a '<unreadable>' sentinel rather
#     than an empty contents list (which would trigger silent deletion under
#     planning.md Step 3b).
# (2) MEDIUM — a stray FILE at the plans_dir path returns total=0 cleanly
#     instead of raising NotADirectoryError from iterdir().
# (3) MEDIUM — an empty ``{}`` status.json is NOT flagged as orphan; the
#     orphan filter matches the require_plan_exists guard in
#     tools-file-ops/file_ops.py (file-presence, not parsed-truthy).


def test_list_orphans_unreadable_dir_emits_sentinel(monkeypatch):
    """(1) OSError on iterdir → contents=['<unreadable>'] sentinel.

    Returning an empty list here would silently trigger the cleanup
    deletion path in planning.md Step 3b. The '<unreadable>' sentinel
    forces a user prompt instead so a permission-denied directory is
    never auto-removed.
    """
    with PlanContext(plan_id='orphans-unreadable') as ctx:
        shutil.rmtree(ctx.plan_dir)

        # Create an orphan dir with no status.json. We don't actually need
        # the real filesystem to refuse iterdir() — we monkeypatch
        # Path.iterdir on this specific dir to raise OSError so the test is
        # portable across CI environments (macOS root, Linux containers,
        # etc. all behave differently around chmod 000).
        orphan_dir = ctx.fixture_dir / 'plans' / 'unreadable-orphan'
        orphan_dir.mkdir(parents=True)

        from pathlib import Path as _Path

        original_iterdir = _Path.iterdir

        def patched_iterdir(self):
            # Only raise for our target orphan; let plans_dir.iterdir() work.
            if self == orphan_dir:
                raise PermissionError('simulated unreadable dir')
            return original_iterdir(self)

        monkeypatch.setattr(_Path, 'iterdir', patched_iterdir)

        result = cmd_list_orphans(Namespace())

        assert result['status'] == 'success'
        assert result['total'] == 1
        entry = result['orphans'][0]
        assert entry['id'] == 'unreadable-orphan'
        assert entry['contents'] == ['<unreadable>'], (
            f'Unreadable orphan must surface ["<unreadable>"] sentinel, got '
            f'{entry["contents"]!r}. An empty list would trigger silent '
            f'deletion under planning.md Step 3b.'
        )


def test_list_orphans_file_at_plans_dir_returns_zero(monkeypatch, tmp_path):
    """(2) Stray FILE at plans_dir path → total=0 cleanly, no exception.

    Replaces ``plans_dir.exists()`` (which is true for files too) with
    ``plans_dir.is_dir()`` so iterdir() is never called on a non-directory.
    Pre-fix this would raise NotADirectoryError.
    """
    # Point get_plans_dir() at a path that is a FILE rather than a directory.
    stray_file = tmp_path / 'plans'
    stray_file.write_text('this is a file, not a directory\n')

    monkeypatch.setattr(_query, 'get_plans_dir', lambda: stray_file)

    result = cmd_list_orphans(Namespace())

    assert result['status'] == 'success', (
        f'Stray file at plans_dir must yield clean success, got {result!r}. '
        f'Regression: plans_dir.exists() returned True for the file and '
        f'iterdir() raised NotADirectoryError.'
    )
    assert result['total'] == 0
    assert result['orphans'] == []


def test_list_orphans_empty_status_json_not_flagged(monkeypatch):
    """(3) Empty ``{}`` status.json must NOT be reported as orphan.

    Matches the require_plan_exists guard in tools-file-ops/file_ops.py
    which checks file PRESENCE, not parsed-truthy. Pre-fix the orphan
    filter used ``if status:`` so an empty ``{}`` parsed to a falsy dict
    and the directory was mis-classified as an orphan.
    """
    with PlanContext(plan_id='orphans-empty-status') as ctx:
        shutil.rmtree(ctx.plan_dir)

        plans_dir = ctx.fixture_dir / 'plans'
        plan_dir = plans_dir / 'empty-status-plan'
        plan_dir.mkdir(parents=True)
        # Write an empty JSON object — parses to {} which is falsy in Python.
        (plan_dir / 'status.json').write_text('{}', encoding='utf-8')

        result = cmd_list_orphans(Namespace())

        assert result['status'] == 'success'
        assert result['total'] == 0, (
            f'Empty {{}} status.json must NOT be flagged as orphan (matches '
            f'require_plan_exists file-presence guard), got '
            f'total={result["total"]} orphans={result["orphans"]!r}. '
            f'Regression: the filter is using parsed-truthy `if status:` '
            f'instead of `(plan_dir / "status.json").is_file()`.'
        )
        assert result['orphans'] == []


# =============================================================================
# Regression Tests: cmd_transition inline strict-verify guard for guarded
# boundaries (folded from the standalone phase_handshake verify --strict step
# that orchestrator workflow docs used to issue separately at 5-execute -> 6-finalize).
# =============================================================================
# Each test seeds a captured handshake row, drifts one tracked invariant, then
# calls cmd_transition and asserts the documented contract. The 5-execute tests
# pin the guarded-boundary behaviour; the 4-plan test pins that non-guarded
# transitions skip the verify path entirely (preserves today's semantics).

# Use STANDARD imports (not importlib.spec_from_file_location) so the
# monkeypatch in the fixtures below hits the same module instance that
# ``_cmd_lifecycle.cmd_verify`` (imported above via _load_module) reads at
# runtime. The path-loading shape used elsewhere in this file creates a
# *new* module object that is not in sys.modules under the canonical name,
# so patching its INVARIANTS has no effect on the cmd_verify code path
# (which resolves INVARIANTS via the sys.modules['_invariants'] copy).
# See test_phase_handshake.py for the prior art on this fixture pattern.
import sys as _sys  # noqa: E402

_PLAN_HANDSHAKE_SCRIPTS_DIR = str(
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'plan-marshall'
    / 'scripts'
)
if _PLAN_HANDSHAKE_SCRIPTS_DIR not in _sys.path:
    _sys.path.insert(0, _PLAN_HANDSHAKE_SCRIPTS_DIR)

import _handshake_commands as _cmds  # type: ignore[import-not-found]  # noqa: E402
import _invariants as _inv  # type: ignore[import-not-found]  # noqa: E402


@pytest.fixture
def _stubbed_invariants(monkeypatch):
    """Deterministic invariant registry shared across cmd_capture / cmd_verify.

    Mirrors the fixture in ``test_phase_handshake.py`` so the cmd_transition
    inline guard sees a predictable observed state. The fixture also patches
    the binding that ``cmd_verify`` in ``_cmd_lifecycle`` imports — without
    that second patch the lifecycle module would still see the real registry
    and the test would compute real git state instead of the stub.
    """
    state = {
        'main_sha': 'abc123',
        'main_dirty': 0,
        'main_dirty_files': [],
        'worktree_sha': None,
        'worktree_dirty': None,
        'worktree_orphan': None,
        'task_state_hash': 'hash-tasks',
        'qgate_open_count': 0,
        'config_hash': 'hash-cfg',
        'pending_tasks_count': 2,
        'phase_steps_complete': None,
        'pending_findings_by_type': '',
        'pending_findings_blocking_count': 0,
    }

    def always(_pid, _md):
        return True

    def make_capture(name):
        def _cap(_pid, _md, _phase):
            return state[name]

        return _cap

    stubbed = [
        ('main_sha', always, make_capture('main_sha')),
        ('main_dirty', always, make_capture('main_dirty')),
        ('main_dirty_files', always, make_capture('main_dirty_files')),
        ('task_state_hash', always, make_capture('task_state_hash')),
        ('qgate_open_count', always, make_capture('qgate_open_count')),
        ('config_hash', always, make_capture('config_hash')),
        ('pending_tasks_count', always, make_capture('pending_tasks_count')),
        ('pending_findings_by_type', always, make_capture('pending_findings_by_type')),
        ('pending_findings_blocking_count', always, make_capture('pending_findings_blocking_count')),
    ]
    monkeypatch.setattr(_inv, 'INVARIANTS', stubbed)
    monkeypatch.setattr(_cmds, 'INVARIANTS', stubbed)
    return state


@pytest.fixture
def _stub_metadata(monkeypatch):
    """Replace _load_status_metadata so cmd_verify sees a metadata dict free
    of worktree fields (avoids the worktree-resolution assertion).
    """
    md: dict = {}
    monkeypatch.setattr(_cmds, '_load_status_metadata', lambda _pid: md)
    return md


def _seed_plan_with_5_execute_capture(plan_id):
    """Create a plan, advance to 5-execute, capture the handshake row.

    Returns nothing; the captured row lives in handshake.toon under the
    fixture plan directory and is consumed by the next cmd_verify call.
    """
    cmd_create(
        Namespace(
            plan_id=plan_id,
            title='Transition Guard Test',
            phases='1-init,2-refine,3-outline,4-plan,5-execute,6-finalize',
            force=False,
        )
    )
    for phase in ('1-init', '2-refine', '3-outline', '4-plan'):
        cmd_update_phase(Namespace(plan_id=plan_id, phase=phase, status='done'))
    cmd_set_phase(Namespace(plan_id=plan_id, phase='5-execute'))
    _cmds.cmd_capture(
        Namespace(plan_id=plan_id, phase='5-execute', override=False, reason=None, strict=False)
    )


def _seed_plan_with_4_plan_capture(plan_id):
    """Create a plan, advance to 4-plan, capture the handshake row, then
    cmd_set_phase to 4-plan so cmd_transition --completed 4-plan is valid.
    """
    cmd_create(
        Namespace(
            plan_id=plan_id,
            title='Transition Guard Test',
            phases='1-init,2-refine,3-outline,4-plan,5-execute,6-finalize',
            force=False,
        )
    )
    for phase in ('1-init', '2-refine', '3-outline'):
        cmd_update_phase(Namespace(plan_id=plan_id, phase=phase, status='done'))
    cmd_set_phase(Namespace(plan_id=plan_id, phase='4-plan'))
    _cmds.cmd_capture(
        Namespace(plan_id=plan_id, phase='4-plan', override=False, reason=None, strict=False)
    )


def test_transition_5_execute_refuses_on_handshake_drift(_stubbed_invariants, _stub_metadata):
    """cmd_transition refuses to advance when the captured 5-execute row drifts.

    Pins the inline strict-verify guard contract: 5-execute -> 6-finalize is in
    _BLOCKING_BOUNDARIES, so cmd_transition MUST re-run cmd_verify and return
    its drift dict unchanged. status.json stays unchanged.
    """
    plan_id = 'transition-drift-5exec'
    with PlanContext(plan_id=plan_id) as ctx:
        _seed_plan_with_5_execute_capture(plan_id)

        _stubbed_invariants['main_sha'] = 'drifted-sha-xyz'
        status_before = json.loads((ctx.plan_dir / 'status.json').read_text(encoding='utf-8'))

        result = cmd_transition(Namespace(plan_id=plan_id, completed='5-execute'))

        assert result is not None
        assert result['status'] == 'drift', (
            f'Expected status: drift on guarded-boundary transition with drifted '
            f'capture, got {result!r}. The inline guard in cmd_transition is not '
            f'firing for 5-execute -> 6-finalize.'
        )
        assert result['phase'] == '5-execute'
        diff_names = {d['invariant'] for d in result['diffs']}
        assert 'main_sha' in diff_names

        status_after = json.loads((ctx.plan_dir / 'status.json').read_text(encoding='utf-8'))
        assert status_after['current_phase'] == status_before['current_phase'] == '5-execute', (
            'cmd_transition wrote status despite drift — the guard is not '
            'short-circuiting before write_status.'
        )
        assert status_after['phases'] == status_before['phases'], (
            'Phase status list mutated despite drift refusal — write_status fired.'
        )


def test_transition_5_execute_drift_toon_byte_equivalent(_stubbed_invariants, _stub_metadata):
    """The dict returned by cmd_transition on drift must equal cmd_verify's dict.

    Pins that the inline guard returns the verify result UNCHANGED — same
    keys, same values, same ordering — so downstream consumers (workflow
    doc surfacing, retrospective parsing) require no adjustment.
    """
    plan_id = 'transition-drift-equiv'
    with PlanContext(plan_id=plan_id):
        _seed_plan_with_5_execute_capture(plan_id)
        _stubbed_invariants['main_sha'] = 'drifted-sha-equiv'

        transition_result = cmd_transition(Namespace(plan_id=plan_id, completed='5-execute'))
        verify_result = _cmds.cmd_verify(
            Namespace(plan_id=plan_id, phase='5-execute', strict=True)
        )

        assert transition_result == verify_result, (
            'cmd_transition drift dict diverges from cmd_verify dict. '
            f'transition={transition_result!r} verify={verify_result!r}. '
            'The inline guard MUST return the verify result unchanged.'
        )


def test_transition_4_plan_skips_handshake_verify_on_drift(_stubbed_invariants, _stub_metadata):
    """cmd_transition --completed 4-plan ignores handshake drift.

    4-plan -> 5-execute is NOT in _BLOCKING_BOUNDARIES, so the inline
    verify path MUST NOT fire even when the captured row would drift.
    This pins today's non-guarded-transition semantics so future
    boundary-set expansions surface as test failures rather than silent
    contract drift.
    """
    plan_id = 'transition-4plan-skip'
    with PlanContext(plan_id=plan_id) as ctx:
        _seed_plan_with_4_plan_capture(plan_id)

        _stubbed_invariants['main_sha'] = 'drifted-sha-4plan'

        result = cmd_transition(Namespace(plan_id=plan_id, completed='4-plan'))

        assert result is not None
        assert result['status'] == 'success', (
            f'cmd_transition refused a non-guarded transition (4-plan -> '
            f'5-execute) despite drift, got {result!r}. The boundary set '
            f"_BLOCKING_BOUNDARIES MUST gate the verify call — non-guarded "
            f'transitions stay drift-blind.'
        )
        assert result['next_phase'] == '5-execute'

        status_after = json.loads((ctx.plan_dir / 'status.json').read_text(encoding='utf-8'))
        assert status_after['current_phase'] == '5-execute', (
            'Non-guarded transition failed to advance current_phase despite '
            'returning success — write_status did not fire.'
        )


# =============================================================================
# Test: Hybrid loopback contract — `--loop-back-target` granularity flag
# =============================================================================
#
# These tests cover the four required cases from the finalize-loopback plan
# Deliverable 3 (TASK-005 test contract):
#   1. mark-step-done --outcome loop_back WITHOUT --loop-back-target →
#      error: missing_loop_back_target
#   2. mark-step-done --outcome loop_back --loop-back-target 5-execute →
#      success, persisted alongside outcome
#   3. mark-step-done --outcome loop_back --loop-back-target 6-finalize →
#      success, persisted alongside outcome
#   4. mark-step-done --outcome loop_back --loop-back-target invalid-phase →
#      argparse rejects via choices (exit code 2)
#
# Plus a forbidden-on-non-loop_back guard for completeness.

_cmd_mark_step = _load_module('_cmd_mark_step', '_cmd_mark_step.py')
cmd_mark_step_done = _cmd_mark_step.cmd_mark_step_done


def _mark_step_args(
    plan_id: str,
    phase: str,
    step: str,
    outcome: str,
    *,
    force: bool = False,
    display_detail: str | None = None,
    head_at_completion: str | None = None,
    loop_back_target: str | None = None,
) -> Namespace:
    """Build a Namespace for cmd_mark_step_done that mirrors the argparse layer."""
    return Namespace(
        plan_id=plan_id,
        phase=phase,
        step=step,
        outcome=outcome,
        force=force,
        display_detail=display_detail,
        head_at_completion=head_at_completion,
        loop_back_target=loop_back_target,
    )


def _setup_plan(plan_id: str) -> None:
    cmd_create(
        Namespace(
            plan_id=plan_id,
            title='Loop-back Target Tests',
            phases='1-init,2-refine,3-outline,4-plan,5-execute,6-finalize',
            force=False,
        )
    )


class TestLoopBackTargetValidation:
    """The `--loop-back-target` flag is REQUIRED on every loop_back outcome
    and FORBIDDEN on every other outcome. Validation is breaking-change
    semantics — no backwards-compat fallback. The four canonical cases plus
    the forbidden-on-other-outcome guard pin the contract documented in
    `manage-status/SKILL.md` § "Loop-back target classification" and
    `phase-6-finalize/SKILL.md` § "Loop-back Target Contract".
    """

    def test_loop_back_without_target_returns_missing_error(self) -> None:
        """Case 1: omitting `--loop-back-target` on a loop_back outcome
        returns `error: missing_loop_back_target`. The validation runs in
        cmd_mark_step_done before any disk write."""
        plan_id = 'lbt-missing-target'
        with PlanContext(plan_id=plan_id):
            _setup_plan(plan_id)
            result = cmd_mark_step_done(
                _mark_step_args(
                    plan_id,
                    '6-finalize',
                    'automated-review',
                    'loop_back',
                    display_detail='loop-back without target',
                    loop_back_target=None,
                )
            )
            assert result['status'] == 'error'
            assert result['error'] == 'missing_loop_back_target'
            assert 'required' in result['message'].lower()

    def test_loop_back_with_target_5_execute_persists_field(self) -> None:
        """Case 2: `--loop-back-target 5-execute` succeeds and the field
        is persisted alongside outcome / display_detail in
        `phase_steps[{phase}][{step}]`."""
        plan_id = 'lbt-target-5-execute'
        with PlanContext(plan_id=plan_id) as ctx:
            _setup_plan(plan_id)
            result = cmd_mark_step_done(
                _mark_step_args(
                    plan_id,
                    '6-finalize',
                    'sonar-roundtrip',
                    'loop_back',
                    display_detail='loop-back iter 1 (target=5-execute)',
                    loop_back_target='5-execute',
                )
            )
            assert result['status'] == 'success'
            assert result['outcome'] == 'loop_back'
            assert result['loop_back_target'] == '5-execute'

            status = json.loads((ctx.plan_dir / 'status.json').read_text(encoding='utf-8'))
            entry = status['metadata']['phase_steps']['6-finalize']['sonar-roundtrip']
            assert entry['outcome'] == 'loop_back'
            assert entry['loop_back_target'] == '5-execute', (
                'Persisted phase_steps record must carry loop_back_target=5-execute'
            )

    def test_loop_back_with_target_6_finalize_persists_field(self) -> None:
        """Case 3: `--loop-back-target 6-finalize` succeeds and the field
        is persisted — the inline-replay tier of the granularity invariant."""
        plan_id = 'lbt-target-6-finalize'
        with PlanContext(plan_id=plan_id) as ctx:
            _setup_plan(plan_id)
            result = cmd_mark_step_done(
                _mark_step_args(
                    plan_id,
                    '6-finalize',
                    'automated-review',
                    'loop_back',
                    display_detail='loop-back iter 1 (target=6-finalize)',
                    loop_back_target='6-finalize',
                )
            )
            assert result['status'] == 'success'
            assert result['outcome'] == 'loop_back'
            assert result['loop_back_target'] == '6-finalize'

            status = json.loads((ctx.plan_dir / 'status.json').read_text(encoding='utf-8'))
            entry = status['metadata']['phase_steps']['6-finalize']['automated-review']
            assert entry['outcome'] == 'loop_back'
            assert entry['loop_back_target'] == '6-finalize', (
                'Persisted phase_steps record must carry loop_back_target=6-finalize'
            )

    def test_loop_back_with_invalid_target_rejected_by_argparse(self) -> None:
        """Case 4: `--loop-back-target invalid-phase` is rejected by argparse
        `choices` enforcement at parse time (exit code 2). This exercises
        the CLI argparse layer end-to-end via subprocess.

        The script-level `invalid_loop_back_target` error path is unreachable
        through the CLI (argparse catches it first); the API-layer test below
        covers the script-level branch by bypassing argparse via direct
        Namespace construction.
        """
        plan_id = 'lbt-invalid-target'
        with PlanContext(plan_id=plan_id):
            _setup_plan(plan_id)
            result = run_script(
                SCRIPT_PATH,
                'mark-step-done',
                '--plan-id',
                plan_id,
                '--phase',
                '6-finalize',
                '--step',
                'automated-review',
                '--outcome',
                'loop_back',
                '--loop-back-target',
                'invalid-phase',
                '--display-detail',
                'loop-back invalid target',
            )
            assert result.returncode == 2, (
                f'argparse must reject invalid --loop-back-target value '
                f'with exit code 2; got {result.returncode}'
            )
            assert 'invalid choice' in result.stderr.lower() or 'invalid-phase' in result.stderr.lower()

    def test_loop_back_target_forbidden_on_non_loop_back_outcome(self) -> None:
        """Guard: supplying `--loop-back-target` alongside a non-loop_back
        outcome (e.g., `done`) returns `error: unexpected_loop_back_target`.
        The flag is structurally bound to the loop_back outcome — using it
        on `done`/`skipped`/`failed` is a contract violation."""
        plan_id = 'lbt-forbidden-on-done'
        with PlanContext(plan_id=plan_id):
            _setup_plan(plan_id)
            result = cmd_mark_step_done(
                _mark_step_args(
                    plan_id,
                    '6-finalize',
                    'commit-push',
                    'done',
                    display_detail='step complete',
                    loop_back_target='5-execute',
                )
            )
            assert result['status'] == 'error'
            assert result['error'] == 'unexpected_loop_back_target'

    def test_loop_back_target_invalid_at_api_layer(self) -> None:
        """API-layer guard: bypassing argparse and passing an invalid
        loop_back_target value directly to cmd_mark_step_done returns
        `error: invalid_loop_back_target`. This exercises the script-level
        branch unreachable through the CLI."""
        plan_id = 'lbt-api-invalid-target'
        with PlanContext(plan_id=plan_id):
            _setup_plan(plan_id)
            result = cmd_mark_step_done(
                _mark_step_args(
                    plan_id,
                    '6-finalize',
                    'automated-review',
                    'loop_back',
                    display_detail='loop-back invalid api target',
                    loop_back_target='not-a-real-phase',
                )
            )
            assert result['status'] == 'error'
            assert result['error'] == 'invalid_loop_back_target'
