#!/usr/bin/env python3
"""Tests for manage-status.py create + JSON storage + worktree seeding.

Split from test_manage_status.py: covers cmd_create (incl. worktree-flag
seeding) and on-disk JSON storage assertions.
"""

import json
from argparse import Namespace
from pathlib import Path

import pytest

from conftest import get_script_path, run_script

# Script path for CLI plumbing tests
SCRIPT_PATH = get_script_path('plan-marshall', 'manage-status', 'manage-status.py')

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

cmd_create = _lifecycle.cmd_create


# =============================================================================
# Test: Create Command
# =============================================================================


def test_create_status(plan_context, monkeypatch):
    """Test creating a status.json with standard 6-phase model."""
    # Pin HOME and credentials dir defensively so status creation
    # cannot leak into real host paths.
    monkeypatch.setenv('HOME', str(plan_context.fixture_dir))
    monkeypatch.setenv('PLAN_MARSHALL_CREDENTIALS_DIR', str(plan_context.fixture_dir / 'creds'))
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


def test_create_status_custom_phases(plan_context):
    """Test creating a status.json with custom phases."""
    result = cmd_create(
        Namespace(plan_id='custom-plan', title='Custom Test', phases='init,execute,finalize', force=False)
    )
    assert result['status'] == 'success'


def test_create_status_force_overwrite(plan_context):
    """Test force overwrite of existing status.json."""
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


def test_create_status_already_exists(plan_context):
    """Test create fails if status already exists without force."""
    # Create first plan
    cmd_create(Namespace(plan_id='exists-plan', title='First Plan', phases='1-init,2-refine', force=False))
    # Try to create again without --force
    result = cmd_create(
        Namespace(plan_id='exists-plan', title='Second Plan', phases='1-init,2-refine', force=False)
    )
    assert result['status'] == 'error'
    assert result['error'] == 'file_exists'


def test_create_invalid_plan_id(plan_context):
    """Test create fails with invalid plan_id (sys.exit(1) from require_valid_plan_id)."""
    with pytest.raises(SystemExit) as exc_info:
        cmd_create(Namespace(plan_id='Invalid_Plan', title='Test', phases='1-init', force=False))
    assert exc_info.value.code == 0


# =============================================================================
# Test: JSON Storage Format
# =============================================================================


def test_json_storage_format(plan_context):
    """Test that status is stored in JSON format."""
    cmd_create(Namespace(plan_id='json-plan', title='JSON Test', phases='1-init,2-refine,3-outline', force=False))
    # Directly read the status.json file
    status_file = plan_context.plan_dir_for('json-plan') / 'status.json'
    assert status_file.exists(), 'status.json should exist'

    content = json.loads(status_file.read_text(encoding='utf-8'))
    assert content['title'] == 'JSON Test'
    assert content['current_phase'] == '1-init'
    assert len(content['phases']) == 3
    assert 'created' in content
    assert 'updated' in content


def test_json_phases_structure(plan_context):
    """Test that phases are stored with correct structure."""
    cmd_create(
        Namespace(plan_id='phases-plan', title='Phases Test', phases='1-init,2-refine,3-outline', force=False)
    )
    status_file = plan_context.plan_dir_for('phases-plan') / 'status.json'
    content = json.loads(status_file.read_text(encoding='utf-8'))

    # Check phases structure
    phases = content['phases']
    assert phases[0] == {'name': '1-init', 'status': 'in_progress'}
    assert phases[1] == {'name': '2-refine', 'status': 'pending'}
    assert phases[2] == {'name': '3-outline', 'status': 'pending'}


def test_json_metadata_structure(plan_context):
    """Test that metadata is stored correctly."""
    from argparse import Namespace as _NS
    # Use the metadata-set verb via importlib to seed a value, then check JSON.
    _query = _load_module('_status_cmd_query', '_status_query.py')
    cmd_metadata = _query.cmd_metadata

    cmd_create(_NS(plan_id='metadata-json-plan', title='Metadata Test', phases='1-init', force=False))
    cmd_metadata(_NS(plan_id='metadata-json-plan', set=True, get=False, field='change_type', value='feature'))

    status_file = plan_context.plan_dir_for('metadata-json-plan') / 'status.json'
    content = json.loads(status_file.read_text(encoding='utf-8'))

    assert 'metadata' in content
    assert content['metadata']['change_type'] == 'feature'


# =============================================================================
# Test: Worktree State Persistence (cmd_create seeding)
# =============================================================================
#
# cmd_create accepts --use-worktree, --worktree-path, --worktree-branch and
# persists the trio into status.metadata so downstream consumers (build
# wrappers, phase-entry assertions, get-worktree-path) can resolve the active
# worktree from a plan-id alone.


def test_create_seeds_worktree_metadata_when_use_worktree_true(plan_context):
    """use_worktree=true with path+branch must seed all three metadata fields."""
    plan_id = 'wt-seed-true'
    abs_path = '/tmp/worktrees/wt-seed-true'
    branch = 'feature/wt-seed-true'
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
    status = json.loads((plan_context.plan_dir_for(plan_id) / 'status.json').read_text(encoding='utf-8'))
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


def test_create_seeds_use_worktree_false_when_omitted(plan_context):
    """No worktree flags → metadata.use_worktree=false, no path/branch fields.

    The contract is symmetric: even without a worktree, cmd_create must seed
    a definite ``use_worktree: false`` marker so downstream consumers don't
    have to treat absence-of-metadata as 'main-checkout'.
    """
    plan_id = 'wt-seed-false'
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

    status = json.loads((plan_context.plan_dir_for(plan_id) / 'status.json').read_text(encoding='utf-8'))
    assert status['metadata'] == {'use_worktree': False}, (
        f'metadata must be exactly {{use_worktree: False}} when no worktree '
        f'is seeded, got {status["metadata"]!r}. The false-state seeding '
        f"contract prohibits writing path/branch keys when use_worktree is "
        f'false.'
    )


def test_create_rejects_use_worktree_without_branch(plan_context):
    """use_worktree=true with path supplied but no branch → invalid_worktree_args.

    --worktree-branch is the only required-together flag with --use-worktree;
    omitting it fails closed regardless of whether --worktree-path is supplied,
    because the branch name is the irreducible piece of intent phase-5-execute
    cannot back-derive at materialization time.
    """
    plan_id = 'wt-no-branch'
    result = cmd_create(
        Namespace(
            plan_id=plan_id,
            title='Missing Branch',
            phases='1-init,2-refine',
            force=False,
            use_worktree=True,
            worktree_path='/tmp/worktrees/wt-no-branch',
            worktree_branch=None,
        )
    )
    assert result['status'] == 'error', (
        f'Missing --worktree-branch must error, got {result!r}. '
        f'Deferred-materialization contract: --use-worktree requires '
        f'--worktree-branch (path is optional).'
    )
    assert result['error'] == 'invalid_worktree_args'
    assert '--worktree-branch' in result['message']


def test_create_seeds_deferred_path_when_only_branch_supplied(plan_context):
    """use_worktree=true with branch only (no path) → metadata seeds the
    empty-string sentinel for worktree_path.

    The deferred-materialization shape: phase-1-init has the worktree branch
    name committed but the worktree directory is not yet allocated. The script
    persists ``metadata.use_worktree: true``, ``metadata.worktree_branch:
    <branch>``, and ``metadata.worktree_path: ''`` (empty-string sentinel
    marking the deferred window). Phase-5-execute Step 2.5 back-fills the
    resolved path on first task execution.
    """
    plan_id = 'wt-deferred-path'
    branch = 'feature/wt-deferred-path'
    result = cmd_create(
        Namespace(
            plan_id=plan_id,
            title='Deferred Worktree Path',
            phases='1-init,2-refine',
            force=False,
            use_worktree=True,
            worktree_path=None,  # <-- the deferred-materialization shape
            worktree_branch=branch,
        )
    )
    assert result['status'] == 'success', (
        f'Deferred-path create must succeed, got {result!r}. '
        f'--use-worktree with --worktree-branch only is the canonical '
        f'phase-1-init shape; --worktree-path is filled in by '
        f'phase-5-execute Step 2.5.'
    )
    assert result['use_worktree'] is True
    assert result['worktree_branch'] == branch
    # The result surfaces the empty-string sentinel for worktree_path.
    assert result['worktree_path'] == ''

    # Verify on-disk status.json carries the sentinel exactly.
    status = json.loads((plan_context.plan_dir_for(plan_id) / 'status.json').read_text(encoding='utf-8'))
    assert status['metadata']['use_worktree'] is True
    assert status['metadata']['worktree_branch'] == branch
    assert status['metadata']['worktree_path'] == '', (
        f'metadata.worktree_path must be the empty-string sentinel, got '
        f'{status["metadata"].get("worktree_path")!r}.'
    )


# =============================================================================
# Test: CLI plumbing for create worktree flags
# =============================================================================


def test_cli_create_with_worktree_flags(plan_context):
    """End-to-end: CLI accepts --use-worktree/--worktree-path/--worktree-branch
    and persists metadata that the get-worktree-path subcommand reads back.
    """
    plan_id = 'wt-cli-roundtrip'
    abs_path = '/tmp/worktrees/wt-cli-roundtrip'
    branch = 'feature/wt-cli-roundtrip'
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
        f'CLI roundtrip regressed — manage-status.py is not wiring the '
        f'create flags into cmd_create OR the get-worktree-path subparser '
        f'is not registered.'
    )
