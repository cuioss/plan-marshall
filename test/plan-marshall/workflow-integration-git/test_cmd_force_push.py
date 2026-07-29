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

import importlib.util
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

from conftest import get_script_path, run_script

# ---------------------------------------------------------------------------
# Load module under test
# ---------------------------------------------------------------------------

_FORCE_PUSH_PATH = get_script_path('plan-marshall', 'workflow-integration-git', '_cmd_force_push.py')
_SCRIPT_PATH = get_script_path('plan-marshall', 'workflow-integration-git', 'git-workflow.py')

_spec = importlib.util.spec_from_file_location('_cmd_force_push', _FORCE_PUSH_PATH)
assert _spec is not None and _spec.loader is not None
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

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


class TestVerifyGitRepo:
    """Direct-import tests for the git-repo verification helper."""

    def test_returns_none_for_valid_git_repo(self, tmp_path: Path) -> None:
        """Returns None when path is a valid git working tree."""
        _init_repo(tmp_path)

        result = _verify_git_repo(tmp_path)

        assert result is None

    def test_returns_error_for_non_git_path(self, outside_repo_dir: Path) -> None:
        """Returns an error string when path is not a git repo."""
        # Must be OUTSIDE the repo: pytest's tmp_path now roots under the
        # repo-local --basetemp, which IS a valid git working tree.
        result = _verify_git_repo(outside_repo_dir)

        assert result is not None
        assert 'working tree' in result


# ---------------------------------------------------------------------------
# Tier 2: _resolve_branch_and_path
# ---------------------------------------------------------------------------


class TestResolveBranchAndPath:
    """Direct-import tests for argument resolution."""

    def test_project_dir_path_missing_branch_returns_error(self) -> None:
        """--project-dir without --branch produces missing_required_arg error."""
        args = Namespace(plan_id=None, project_dir='/some/path', branch=None)

        branch, path, error = _resolve_branch_and_path(args)

        assert branch is None
        assert path is None
        assert error is not None
        assert error['error_type'] == 'missing_required_arg'

    def test_project_dir_with_branch_returns_path(self) -> None:
        """--project-dir + --branch escape-hatch resolves successfully."""
        args = Namespace(plan_id=None, project_dir='/some/path', branch='feature/x')

        branch, path, error = _resolve_branch_and_path(args)

        assert error is None
        assert branch == 'feature/x'
        assert path == Path('/some/path')

    def test_no_args_returns_error(self) -> None:
        """Neither --plan-id nor --project-dir → missing_required_arg error."""
        args = Namespace(plan_id=None, project_dir=None, branch=None)

        branch, path, error = _resolve_branch_and_path(args)

        assert branch is None
        assert path is None
        assert error is not None


# ---------------------------------------------------------------------------
# Tier 2: cmd_force_push — project-dir escape-hatch path
# ---------------------------------------------------------------------------


class TestCmdForcePushEscapeHatch:
    """Direct-import tests for cmd_force_push via --project-dir."""

    def test_project_dir_not_a_git_repo_returns_error(self, outside_repo_dir: Path) -> None:
        """--project-dir pointing at a non-git directory → project_dir_not_a_git_repo."""
        # Must be OUTSIDE the repo: pytest's tmp_path now roots under the
        # repo-local --basetemp, which IS a git repo (would surface a later
        # branch_not_found error instead of project_dir_not_a_git_repo).
        args = Namespace(plan_id=None, project_dir=str(outside_repo_dir), branch='feature/x')

        result = cmd_force_push(args)

        assert result['status'] == 'error'
        assert result['error_type'] == 'project_dir_not_a_git_repo'
        assert result['operation'] == 'force-push-with-lease'

    def test_branch_not_found_locally_returns_error(self, tmp_path: Path) -> None:
        """Branch that does not exist locally → branch_not_found."""
        _init_repo(tmp_path)
        args = Namespace(plan_id=None, project_dir=str(tmp_path), branch='feature/nonexistent')

        result = cmd_force_push(args)

        assert result['status'] == 'error'
        assert result['error_type'] == 'branch_not_found'
        assert 'feature/nonexistent' in result['message']

    def test_main_branch_rejection(self, tmp_path: Path) -> None:
        """Attempting to push 'main' → branch_not_found (base branch guard)."""
        _init_repo(tmp_path)
        args = Namespace(plan_id=None, project_dir=str(tmp_path), branch='main')

        result = cmd_force_push(args)

        assert result['status'] == 'error'
        assert result['error_type'] == 'branch_not_found'
        assert 'base branch' in result['message']

    def test_master_branch_rejection(self, tmp_path: Path) -> None:
        """Attempting to push 'master' → branch_not_found (base branch guard)."""
        _init_repo(tmp_path)
        subprocess.run(['git', '-C', str(tmp_path), 'checkout', '-b', 'master'], check=True)
        args = Namespace(plan_id=None, project_dir=str(tmp_path), branch='master')

        result = cmd_force_push(args)

        assert result['status'] == 'error'
        assert result['error_type'] == 'branch_not_found'
        assert 'base branch' in result['message']

    def test_envelope_includes_project_dir_when_supplied(self, tmp_path: Path) -> None:
        """Response envelope echoes project_dir when --project-dir is used."""
        _init_repo(tmp_path)
        # Use a nonexistent branch to get an early error (avoids needing a remote).
        args = Namespace(plan_id=None, project_dir=str(tmp_path), branch='feature/x')

        result = cmd_force_push(args)

        assert 'project_dir' in result
        assert result['project_dir'] == str(tmp_path)

    def test_envelope_excludes_plan_id_when_project_dir_path(self, tmp_path: Path) -> None:
        """When --project-dir path is used, plan_id must not appear in response."""
        _init_repo(tmp_path)
        args = Namespace(plan_id=None, project_dir=str(tmp_path), branch='feature/x')

        result = cmd_force_push(args)

        assert 'plan_id' not in result


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
        _patch_run_git(monkeypatch, {
            ('push', 'origin'): (1, '', 'error: failed to push some refs\n! [rejected] feature/x -> feature/x (non-fast-forward)'),
        })
        args = Namespace(plan_id=None, project_dir=str(tmp_path), branch='feature/x')

        result = cmd_force_push(args)

        assert result['status'] == 'rejected'
        assert result['error_type'] == 'push_rejected_non_fast_forward'

    def test_generic_push_failure_mapped_to_push_failed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Non-rejection push failure → push_failed."""
        _init_repo(tmp_path)
        _create_feature_branch(tmp_path, 'feature/x')
        _patch_run_git(monkeypatch, {
            ('push', 'origin'): (1, '', 'error: could not connect to remote'),
        })
        args = Namespace(plan_id=None, project_dir=str(tmp_path), branch='feature/x')

        result = cmd_force_push(args)

        assert result['status'] == 'error'
        assert result['error_type'] == 'push_failed'

    def test_success_path_returns_success_status(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Successful push returns status=success and branch/remote fields."""
        _init_repo(tmp_path)
        _create_feature_branch(tmp_path, 'feature/x')
        _patch_run_git(monkeypatch, {
            ('push', 'origin'): (0, '', ''),
            ('ls-remote', 'origin'): (0, 'abc123\trefs/heads/feature/x\n', ''),
        })
        args = Namespace(plan_id=None, project_dir=str(tmp_path), branch='feature/x')

        result = cmd_force_push(args)

        assert result['status'] == 'success'
        assert result['branch'] == 'feature/x'
        assert result['remote'] == 'origin'
        assert 'remote_sha' in result
        assert result['remote_sha'] == 'abc123'

    def test_success_without_ls_remote_omits_remote_sha(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When ls-remote fails, remote_sha is absent (not None or empty)."""
        _init_repo(tmp_path)
        _create_feature_branch(tmp_path, 'feature/x')
        _patch_run_git(monkeypatch, {
            ('push', 'origin'): (0, '', ''),
            ('ls-remote', 'origin'): (1, '', 'connection failed'),
        })
        args = Namespace(plan_id=None, project_dir=str(tmp_path), branch='feature/x')

        result = cmd_force_push(args)

        assert result['status'] == 'success'
        assert 'remote_sha' not in result


# ---------------------------------------------------------------------------
# Tier 2: _resolve_branch_and_path — the --plan-id resolver path
# ---------------------------------------------------------------------------


class TestResolveBranchAndPathViaResolver:
    """The ``--plan-id`` path resolves BOTH worktree faces through the resolver.

    ``force-push-with-lease`` is the one verb in this bundle that needs the path
    face AND the branch face, so it exercises both seams of the single
    ``get-worktree-path`` channel. The retired implementation shelled out once
    and hand-parsed both values out of the TOON; the migrated one asks the
    resolver for each face.
    """

    def test_plan_id_resolves_path_and_branch_from_the_resolver(self) -> None:
        """Both faces come from the resolver, each reached exactly once."""
        args = Namespace(plan_id='fp-plan', project_dir=None, branch=None)

        with patch_worktree_faces(True) as (path_mock, branch_mock):
            branch, path, error = _resolve_branch_and_path(args)

        assert error is None, error
        assert branch == CANONICAL_WORKTREE_BRANCH
        assert path == Path(CANONICAL_WORKTREE)
        assert path_mock.call_count == 1, 'path face not resolved exactly once'
        assert branch_mock.call_count == 1, 'branch face not resolved exactly once'

    def test_plan_without_a_dedicated_worktree_is_refused(self) -> None:
        """``use_worktree=false`` is refused rather than answered with the main checkout.

        This verb force-pushes a plan's feature branch; silently answering with
        the main checkout would target the wrong tree. The ``has_worktree`` face
        is what makes that refusal expressible without re-reading status.
        """
        args = Namespace(plan_id='fp-no-worktree', project_dir=None, branch=None)

        with patch_worktree_faces(False):
            branch, path, error = _resolve_branch_and_path(args)

        assert branch is None
        assert path is None
        assert error is not None
        assert error['error_type'] == 'worktree_not_materialized'

    def test_absent_branch_is_refused(self) -> None:
        """A resolvable worktree with no recorded branch is an incomplete plan."""
        args = Namespace(plan_id='fp-no-branch', project_dir=None, branch=None)

        with patch_worktree_faces(True, worktree_branch=''):
            branch, path, error = _resolve_branch_and_path(args)

        assert branch is None
        assert path is None
        assert error is not None
        assert error['error_type'] == 'worktree_not_materialized'

    def test_resolution_failure_surfaces_the_resolver_message(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A ``WorktreeResolutionError`` is surfaced verbatim, not swallowed."""
        import file_ops  # noqa: PLC0415

        def _raise(_plan_id):
            raise file_ops.WorktreeResolutionError('metadata is corrupt')

        monkeypatch.setattr(file_ops, '_query_worktree_path', _raise)
        args = Namespace(plan_id='fp-corrupt', project_dir=None, branch=None)

        branch, path, error = _resolve_branch_and_path(args)

        assert branch is None
        assert path is None
        assert error is not None
        assert error['error_type'] == 'plan_not_found'
        assert 'metadata is corrupt' in error['message']

    def test_no_plan_sentinel_is_refused_by_the_worktree_verb(self) -> None:
        """``NO_PLAN`` has no dedicated worktree, so this verb refuses it.

        The sentinel is accepted by the RESOLVER — it resolves to the main
        checkout — but ``force-push-with-lease`` needs a plan's feature branch,
        and the sentinel has none. Refusing here is the correct outcome, and
        asserting it keeps a future reader from "fixing" the sentinel into a
        main-branch force push.
        """
        args = Namespace(plan_id=NO_PLAN_SENTINEL, project_dir=None, branch=None)

        with patch_worktree_faces(True) as (path_mock, branch_mock):
            branch, path, error = _resolve_branch_and_path(args)

        assert error is not None
        assert error['error_type'] == 'worktree_not_materialized'
        assert path_mock.call_count == 0, 'the sentinel must never reach get-worktree-path'
        assert branch_mock.call_count == 0, 'the sentinel must never reach get-worktree-path'


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
            _SCRIPT_PATH, 'force-push-with-lease',
            '--project-dir', str(tmp_path),
        )

        parsed = parse_toon(result.stdout)
        assert parsed['status'] == 'error'
        assert parsed['error_type'] == 'missing_required_arg'

    def test_help_flag_shows_force_push_subcommand(self) -> None:
        """--help lists force-push-with-lease in output."""
        result = run_script(_SCRIPT_PATH, '--help')

        assert result.returncode == 0
        assert 'force-push-with-lease' in result.stdout
