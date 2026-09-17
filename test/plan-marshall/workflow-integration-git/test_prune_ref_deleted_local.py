# SPDX-License-Identifier: FSL-1.1-ALv2
"""Regression test for prune-local-and-remote-ref tolerated deleted-local path.

When the local branch is already deleted, the verb must still prune
refs/remotes/origin/{branch} and report the tolerated local delete rather than
branch_delete_failed.
"""

from __future__ import annotations

import subprocess
from argparse import Namespace
from pathlib import Path

import pytest

from conftest import load_script_module

_mod = load_script_module(
    'plan-marshall', 'workflow-integration-git', '_cmd_prune_ref.py', '_cmd_prune_ref_deleted_local'
)

cmd_prune_ref = _mod.cmd_prune_ref


def _init_repo(path: Path, branch: str = 'main') -> None:
    subprocess.run(['git', 'init', '-q', '-b', branch, str(path)], check=True)
    subprocess.run(['git', '-C', str(path), 'config', 'user.email', 't@t.test'], check=True)
    subprocess.run(['git', '-C', str(path), 'config', 'user.name', 'Test'], check=True)
    (path / 'README.md').write_text('x\n')
    subprocess.run(['git', '-C', str(path), 'add', 'README.md'], check=True)
    subprocess.run(['git', '-C', str(path), 'commit', '-m', 'init'], check=True)


class TestPruneRefDeletedLocal:
    def test_deleted_local_still_prunes_remote_ref(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _init_repo(tmp_path, branch='main')
        orig = _mod.run_git

        def fake_run_git(args, **kwargs):
            if '--abbrev-ref' in args:
                return (0, 'main', '')
            if '-D' in args:
                return (1, '', 'error: branch not found')
            if '--verify' in args:
                return (1, '', '')
            if 'show-ref' in args:
                return (0, '', '')
            if 'update-ref' in args:
                return (0, '', '')
            return orig(args, **kwargs)

        monkeypatch.setattr(_mod, 'run_git', fake_run_git)
        args = Namespace(plan_id=None, project_dir=str(tmp_path), head='feature/x', mode='local_and_remote')

        result = cmd_prune_ref(args)

        assert result['status'] == 'success'
        assert result['local_deleted'] is True
        assert result['remote_ref_deleted'] is True
        assert 'local_delete_warning' in result
        assert 'already deleted' in result['local_delete_warning']
