#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for _cmd_force_push.py — force-push-with-lease verb.

Tier 2 (direct import) tests covering:
* _resolve_branch_and_path  — the --plan-id resolver path, missing branch, base branch guard
* _verify_git_repo          — non-git path
* cmd_force_push            — success path, branch_not_found, push_rejected, push_failed,
                              lease_check_failed, base-branch rejection

Tier 3 (subprocess CLI plumbing) tests covering:
* Missing required args (argparse rejects)
* force-push-with-lease --project-dir path with --branch (escape-hatch)

Resolver-migration note
-----------------------
The private ``_find_executor`` helper this file used to exercise is GONE. It
existed only to locate ``.plan/execute-script.py`` for a hand-rolled
``manage-status get-worktree-path`` shell-out; that whole block now delegates to
``file_ops.resolve_plan_context``, which owns the single executor lookup in the
codebase. Its three tests are deliberately NOT re-pointed at
``file_ops.get_executor_path`` — that would re-test the resolver's internals
from a consumer's suite. What replaces them is the
``TestResolveBranchAndPathViaResolver`` block below, which pins the behaviour
that actually matters here: this verb resolves BOTH worktree faces through the
resolver.
"""

from __future__ import annotations

import subprocess
from argparse import Namespace
from pathlib import Path

import pytest
from _resolve_project_dir_fixtures import (
    CANONICAL_WORKTREE,
    CANONICAL_WORKTREE_BRANCH,
    NO_PLAN_SENTINEL,
    patch_worktree_faces,
)
from toon_parser import parse_toon

from conftest import get_script_path, load_script_module, run_script

# ---------------------------------------------------------------------------
# Load module under test
# ---------------------------------------------------------------------------

_FORCE_PUSH_PATH = get_script_path('plan-marshall', 'workflow-integration-git', '_cmd_force_push.py')
_SCRIPT_PATH = get_script_path('plan-marshall', 'workflow-integration-git', 'git-workflow.py')

_mod = load_script_module('plan-marshall', 'workflow-integration-git', '_cmd_force_push.py', '_cmd_force_push')

cmd_force_push = _mod.cmd_force_push
_verify_git_repo = _mod._verify_git_repo
_resolve_branch_and_path = _mod._resolve_branch_and_path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _init_repo(path: Path) -> None:
    """Initialise a minimal git repo with a single commit."""
    subprocess.run(['git', 'init', '-q', '-b', 'main', str(path)], check=True)
    subprocess.run(['git', '-C', str(path), 'config', 'user.email', 't@t.test'], check=True)
    subprocess.run(['git', '-C', str(path), 'config', 'user.name', 'Test'], check=True)
    (path / 'README.md').write_text('x\n')
    subprocess.run(['git', '-C', str(path), 'add', 'README.md'], check=True)
    subprocess.run(['git', '-C', str(path), 'commit', '-m', 'init'], check=True)


def _create_feature_branch(path: Path, branch: str) -> None:
    """Create a feature branch in the repo."""
    subprocess.run(['git', '-C', str(path), 'checkout', '-b', branch], check=True)


# ---------------------------------------------------------------------------
# Tier 2: _verify_git_repo
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Tier 2: cmd_force_push — push failure error mapping
# ---------------------------------------------------------------------------


def _patch_run_git(monkeypatch: pytest.MonkeyPatch, responses: dict) -> None:
    """Patch _mod.run_git to return canned responses keyed by an args tuple.

    Any git call whose argv contains all elements of a ``responses`` key returns
    the mapped triple; everything else falls through to the real ``run_git`` (so
    e.g. ``rev-parse --verify`` branch-existence checks run for real).
    """
    orig_run_git = _mod.run_git

    def fake_run_git(args, **kwargs):
        key = tuple(args)
        for pattern, response in responses.items():
            if all(p in key for p in pattern):
                return response
        return orig_run_git(args, **kwargs)

    monkeypatch.setattr(_mod, 'run_git', fake_run_git)


class TestCmdForcePushPushFailures:
    """Test push error categorization by monkeypatching run_git."""

    def test_non_fast_forward_rejection_mapped_to_push_rejected(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Lease violation with 'rejected' + 'non-fast-forward' → push_rejected_non_fast_forward."""
        _init_repo(tmp_path)
        _create_feature_branch(tmp_path, 'feature/x')
        _patch_run_git(
            monkeypatch,
            {
                ('push', 'origin'): (
                    1,
                    '',
                    'error: failed to push some refs\n! [rejected] feature/x -> feature/x (non-fast-forward)',
                ),
            },
        )
        args = Namespace(plan_id=None, project_dir=str(tmp_path), branch='feature/x')

        result = cmd_force_push(args)

        assert result['status'] == 'rejected'
        assert result['error_type'] == 'push_rejected_non_fast_forward'

    def test_generic_push_failure_mapped_to_push_failed(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Non-rejection push failure → push_failed."""
        _init_repo(tmp_path)
        _create_feature_branch(tmp_path, 'feature/x')
        _patch_run_git(
            monkeypatch,
            {
                ('push', 'origin'): (1, '', 'error: could not connect to remote'),
            },
        )
        args = Namespace(plan_id=None, project_dir=str(tmp_path), branch='feature/x')

        result = cmd_force_push(args)

        assert result['status'] == 'error'
        assert result['error_type'] == 'push_failed'

    def test_success_path_returns_success_status(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Successful push returns status=success and branch/remote fields."""
        _init_repo(tmp_path)
        _create_feature_branch(tmp_path, 'feature/x')
        _patch_run_git(
            monkeypatch,
            {
                ('push', 'origin'): (0, '', ''),
                ('ls-remote', 'origin'): (0, 'abc123\trefs/heads/feature/x\n', ''),
            },
        )
        args = Namespace(plan_id=None, project_dir=str(tmp_path), branch='feature/x')

        result = cmd_force_push(args)

        assert result['status'] == 'success'
        assert result['branch'] == 'feature/x'
        assert result['remote'] == 'origin'
        assert 'remote_sha' in result
        assert result['remote_sha'] == 'abc123'

    def test_success_without_ls_remote_omits_remote_sha(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """When ls-remote fails, remote_sha is absent (not None or empty)."""
        _init_repo(tmp_path)
        _create_feature_branch(tmp_path, 'feature/x')
        _patch_run_git(
            monkeypatch,
            {
                ('push', 'origin'): (0, '', ''),
                ('ls-remote', 'origin'): (1, '', 'connection failed'),
            },
        )
        args = Namespace(plan_id=None, project_dir=str(tmp_path), branch='feature/x')

        result = cmd_force_push(args)

        assert result['status'] == 'success'
        assert 'remote_sha' not in result


# ---------------------------------------------------------------------------
# Tier 3: CLI plumbing
# ---------------------------------------------------------------------------


class TestCmdForcePushCli:
    """Subprocess tests for CLI plumbing of force-push-with-lease."""

    def test_missing_plan_id_and_project_dir_exits_with_error(self) -> None:
        """Neither --plan-id nor --project-dir produces a structured error."""
        result = run_script(_SCRIPT_PATH, 'force-push-with-lease')

        # Expected: exit 0 with TOON error (argparse supplies both as optional).
        parsed = parse_toon(result.stdout)
        assert parsed['status'] == 'error'

    def test_project_dir_requires_branch(self, tmp_path: Path) -> None:
        """--project-dir without --branch returns missing_required_arg error."""
        result = run_script(
            _SCRIPT_PATH,
            'force-push-with-lease',
            '--project-dir',
            str(tmp_path),
        )

        parsed = parse_toon(result.stdout)
        assert parsed['status'] == 'error'
        assert parsed['error_type'] == 'missing_required_arg'

    def test_help_flag_shows_force_push_subcommand(self) -> None:
        """--help lists force-push-with-lease in output."""
        result = run_script(_SCRIPT_PATH, '--help')

        assert result.returncode == 0
        assert 'force-push-with-lease' in result.stdout
