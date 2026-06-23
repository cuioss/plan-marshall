#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-status.py create + JSON storage + worktree intent.

Split from test_manage_status.py: covers cmd_create (incl. the use_worktree
intent persistence) and on-disk JSON storage assertions. Create persists only
``metadata.use_worktree``; the feature branch and the resolved worktree_path
are derived and back-filled at phase-5-execute Step 2.5.
"""

import json
from argparse import Namespace

import pytest

from conftest import get_script_path, load_script_module, run_script

# Script path for CLI plumbing tests
SCRIPT_PATH = get_script_path('plan-marshall', 'manage-status', 'manage-status.py')


_lifecycle = load_script_module('plan-marshall', 'manage-status', '_cmd_lifecycle.py', '_status_cmd_lifecycle')

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
    _query = load_script_module('plan-marshall', 'manage-status', '_status_query.py', '_status_cmd_query')
    cmd_metadata = _query.cmd_metadata

    cmd_create(Namespace(plan_id='metadata-json-plan', title='Metadata Test', phases='1-init', force=False))
    cmd_metadata(Namespace(plan_id='metadata-json-plan', set=True, get=False, field='change_type', value='feature'))

    status_file = plan_context.plan_dir_for('metadata-json-plan') / 'status.json'
    content = json.loads(status_file.read_text(encoding='utf-8'))

    assert 'metadata' in content
    assert content['metadata']['change_type'] == 'feature'


# =============================================================================
# Test: Worktree intent persistence (cmd_create seeding)
# =============================================================================
#
# cmd_create persists ONLY the use_worktree intent at create. The feature
# branch (feature/{plan_id}) and the resolved worktree_path are derived and
# back-filled by phase-5-execute Step 2.5 at materialization — they are NOT
# seeded at create. The create surface accepts only --use-worktree for worktree
# intent: the --worktree-branch / --worktree-path flags are gone.


def test_create_seeds_only_use_worktree_when_use_worktree_true(plan_context):
    """use_worktree=true persists exactly {use_worktree: True} — no path, no branch.

    The empty-string worktree_path sentinel and the early worktree_branch
    persistence are removed (B-strip): create writes neither key. Phase-5-execute
    Step 2.5 derives feature/{plan_id} and back-fills both worktree_branch and
    the resolved worktree_path at materialization.
    """
    plan_id = 'wt-seed-true'
    result = cmd_create(
        Namespace(
            plan_id=plan_id,
            title='Worktree Seed True',
            phases='1-init,2-refine',
            force=False,
            use_worktree=True,
        )
    )
    assert result['status'] == 'success'
    assert result['use_worktree'] is True
    # The result MUST NOT carry worktree_path / worktree_branch — create no
    # longer persists or echoes them.
    assert 'worktree_path' not in result
    assert 'worktree_branch' not in result

    # Verify status.json on disk persists ONLY the use_worktree intent.
    status = json.loads((plan_context.plan_dir_for(plan_id) / 'status.json').read_text(encoding='utf-8'))
    assert status['metadata'] == {'use_worktree': True}, (
        f'metadata must be exactly {{use_worktree: True}} at create, got '
        f'{status["metadata"]!r}. B-strip removed the worktree_path sentinel '
        f'and the early worktree_branch persistence — only use_worktree is '
        f'durable at create.'
    )


def test_create_seeds_use_worktree_false_when_omitted(plan_context):
    """No worktree flag → metadata.use_worktree=false, no path/branch fields.

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
        )
    )
    assert result['status'] == 'success'
    assert result['use_worktree'] is False
    # Result MUST NOT carry worktree_path / worktree_branch.
    assert 'worktree_path' not in result
    assert 'worktree_branch' not in result

    status = json.loads((plan_context.plan_dir_for(plan_id) / 'status.json').read_text(encoding='utf-8'))
    assert status['metadata'] == {'use_worktree': False}, (
        f'metadata must be exactly {{use_worktree: False}} when no worktree '
        f'is seeded, got {status["metadata"]!r}. The false-state seeding '
        f'contract prohibits writing path/branch keys.'
    )


def test_create_ignores_stale_worktree_args_if_passed(plan_context):
    """cmd_create no longer reads worktree_path / worktree_branch from args.

    Even if a stale caller passes those attributes on the Namespace, they are
    ignored: only use_worktree drives the persisted metadata. This guards the
    contract that the branch/path are never seeded at create.
    """
    plan_id = 'wt-ignore-stale'
    result = cmd_create(
        Namespace(
            plan_id=plan_id,
            title='Ignore Stale Args',
            phases='1-init,2-refine',
            force=False,
            use_worktree=True,
            worktree_path='/tmp/worktrees/wt-ignore-stale',
            worktree_branch='feature/wt-ignore-stale',
        )
    )
    assert result['status'] == 'success'
    status = json.loads((plan_context.plan_dir_for(plan_id) / 'status.json').read_text(encoding='utf-8'))
    assert status['metadata'] == {'use_worktree': True}, (
        f'Stale worktree_path / worktree_branch args must be ignored — metadata '
        f'must be exactly {{use_worktree: True}}, got {status["metadata"]!r}.'
    )


# =============================================================================
# Test: CLI plumbing for create --use-worktree
# =============================================================================


def test_cli_create_with_use_worktree(plan_context):
    """End-to-end: CLI accepts --use-worktree and persists only the intent.

    The --worktree-branch / --worktree-path flags are removed from the create
    subparser; get-worktree-path reports the unmaterialized state because no
    path is persisted at create.
    """
    plan_id = 'wt-cli-roundtrip'
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
    )
    assert create_result.success, f'create failed: {create_result.stderr}'
    assert 'status: success' in create_result.stdout

    status = json.loads((plan_context.plan_dir_for(plan_id) / 'status.json').read_text(encoding='utf-8'))
    assert status['metadata'] == {'use_worktree': True}, (
        f'CLI create --use-worktree must persist only {{use_worktree: True}}, '
        f'got {status["metadata"]!r}.'
    )


def test_cli_create_rejects_removed_worktree_branch_flag(plan_context):
    """The create subparser no longer accepts --worktree-branch (argparse exits 2)."""
    result = run_script(
        SCRIPT_PATH,
        'create',
        '--plan-id',
        'wt-removed-branch-flag',
        '--title',
        'Removed Branch Flag',
        '--phases',
        '1-init,2-refine',
        '--use-worktree',
        '--worktree-branch',
        'feature/wt-removed-branch-flag',
    )
    assert not result.success, (
        f'create with the removed --worktree-branch flag must fail (argparse '
        f'exit 2), got success. stdout={result.stdout!r}'
    )
