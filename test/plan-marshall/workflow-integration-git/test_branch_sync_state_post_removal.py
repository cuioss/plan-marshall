# SPDX-License-Identifier: FSL-1.1-ALv2
"""Regression test for branch-sync-state post-removal fallback.

After branch-cleanup removes the worktree (move-back then remove-worktree then
delete-branch), branch-sync-state must still return remote_absent_landed with
barrier_action skip for a landed branch instead of plan_resolution_failed.
"""

from __future__ import annotations

import subprocess
from argparse import Namespace
from pathlib import Path

from conftest import load_script_module

git_workflow = load_script_module(
    'plan-marshall', 'workflow-integration-git', 'git-workflow.py', 'git_workflow_post_removal'
)

BRANCH = 'feature/sync-plan'


def _git_init_with_identity(work: Path) -> None:
    subprocess.run(['git', 'init', '-q', '-b', 'main', str(work)], check=True)
    subprocess.run(['git', '-C', str(work), 'config', 'user.email', 't@t.test'], check=True)
    subprocess.run(['git', '-C', str(work), 'config', 'user.name', 'Test'], check=True)


def _seed_merged_and_deleted(tmp_path: Path) -> Path:
    origin = tmp_path / 'origin.git'
    origin.mkdir()
    subprocess.run(['git', 'init', '--bare'], cwd=origin, capture_output=True)
    work = tmp_path / 'work'
    work.mkdir()
    _git_init_with_identity(work)
    (work / '.gitignore').write_text('.plan/\n')
    (work / 'file.txt').write_text('one')
    subprocess.run(['git', 'add', '.'], cwd=work, capture_output=True)
    subprocess.run(['git', 'commit', '-m', 'init'], cwd=work, capture_output=True)
    subprocess.run(['git', 'remote', 'add', 'origin', f'file://{origin}'], cwd=work, capture_output=True)
    subprocess.run(['git', 'push', '-u', 'origin', 'main'], cwd=work, capture_output=True)
    subprocess.run(['git', 'checkout', '-b', BRANCH], cwd=work, capture_output=True)
    (work / 'feature.txt').write_text('feat')
    subprocess.run(['git', 'add', '.'], cwd=work, capture_output=True)
    subprocess.run(['git', 'commit', '-m', 'feature work'], cwd=work, capture_output=True)
    subprocess.run(['git', 'checkout', 'main'], cwd=work, capture_output=True)
    subprocess.run(['git', 'merge', '--ff-only', BRANCH], cwd=work, capture_output=True)
    subprocess.run(['git', 'push', 'origin', 'main'], cwd=work, capture_output=True)
    subprocess.run(['git', 'checkout', 'main'], cwd=work, capture_output=True)
    return work


class TestBranchSyncStatePostRemoval:
    def test_post_removal_returns_landed_with_skip(self, tmp_path: Path, monkeypatch) -> None:
        work = _seed_merged_and_deleted(tmp_path)

        def _unresolved(plan_id: str):
            return None, {
                'status': 'error',
                'plan_id': plan_id,
                'error': 'plan_resolution_failed',
                'message': 'No worktree configured for this plan',
            }

        monkeypatch.setattr(git_workflow, '_resolve_worktree_path_for_plan', _unresolved)
        monkeypatch.setattr(git_workflow, '_read_metadata_field', lambda plan_id, field: BRANCH)
        monkeypatch.setattr(git_workflow, 'main_checkout_root', lambda: work)

        result = git_workflow.cmd_branch_sync_state(Namespace(plan_id='sync-plan'))

        assert result['status'] == 'success'
        assert result['state'] == 'remote_absent_landed'
        assert result['barrier_action'] == 'skip'
        assert result['probe_source'] == 'main_checkout_fallback'
