"""Tests for _cmd_force_push.py — force-push-with-lease verb.

Tier 2 (direct import) tests covering:
* _resolve_branch_and_path  — --plan-id missing executor, missing branch, base branch guard
* _verify_git_repo          — non-git path
* cmd_force_push            — success path, branch_not_found, push_rejected, push_failed,
                              lease_check_failed, base-branch rejection

Tier 3 (subprocess CLI plumbing) tests covering:
* Missing required args (argparse rejects)
* force-push-with-lease --project-dir path with --branch (escape-hatch)
"""

from __future__ import annotations

import importlib.util
import subprocess
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from toon_parser import parse_toon  # type: ignore[import-not-found]

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


class TestVerifyGitRepo(unittest.TestCase):
    """Direct-import tests for the git-repo verification helper."""

    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        self.path = Path(self._tmpdir)

    def tearDown(self) -> None:
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_returns_none_for_valid_git_repo(self) -> None:
        """Returns None when path is a valid git working tree."""
        _init_repo(self.path)
        result = _verify_git_repo(self.path)
        self.assertIsNone(result)

    def test_returns_error_for_non_git_path(self) -> None:
        """Returns an error string when path is not a git repo."""
        result = _verify_git_repo(self.path)
        self.assertIsNotNone(result)
        self.assertIn('working tree', result or '')


# ---------------------------------------------------------------------------
# Tier 2: _resolve_branch_and_path
# ---------------------------------------------------------------------------


class TestResolveBranchAndPath(unittest.TestCase):
    """Direct-import tests for argument resolution."""

    def test_project_dir_path_missing_branch_returns_error(self) -> None:
        """--project-dir without --branch produces missing_required_arg error."""
        args = Namespace(plan_id=None, project_dir='/some/path', branch=None)
        branch, path, error = _resolve_branch_and_path(args)
        self.assertIsNone(branch)
        self.assertIsNone(path)
        self.assertIsNotNone(error)
        assert error is not None
        self.assertEqual(error['error_type'], 'missing_required_arg')

    def test_project_dir_with_branch_returns_path(self) -> None:
        """--project-dir + --branch escape-hatch resolves successfully."""
        args = Namespace(plan_id=None, project_dir='/some/path', branch='feature/x')
        branch, path, error = _resolve_branch_and_path(args)
        self.assertIsNone(error)
        self.assertEqual(branch, 'feature/x')
        self.assertEqual(path, Path('/some/path'))

    def test_no_args_returns_error(self) -> None:
        """Neither --plan-id nor --project-dir → missing_required_arg error."""
        args = Namespace(plan_id=None, project_dir=None, branch=None)
        branch, path, error = _resolve_branch_and_path(args)
        self.assertIsNone(branch)
        self.assertIsNone(path)
        self.assertIsNotNone(error)


# ---------------------------------------------------------------------------
# Tier 2: cmd_force_push — project-dir escape-hatch path
# ---------------------------------------------------------------------------


class TestCmdForcePushEscapeHatch(unittest.TestCase):
    """Direct-import tests for cmd_force_push via --project-dir."""

    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        self.path = Path(self._tmpdir)

    def tearDown(self) -> None:
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_project_dir_not_a_git_repo_returns_error(self) -> None:
        """--project-dir pointing at a non-git directory → project_dir_not_a_git_repo."""
        args = Namespace(plan_id=None, project_dir=str(self.path), branch='feature/x')
        result = cmd_force_push(args)
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['error_type'], 'project_dir_not_a_git_repo')
        self.assertEqual(result['operation'], 'force-push-with-lease')

    def test_branch_not_found_locally_returns_error(self) -> None:
        """Branch that does not exist locally → branch_not_found."""
        _init_repo(self.path)
        args = Namespace(plan_id=None, project_dir=str(self.path), branch='feature/nonexistent')
        result = cmd_force_push(args)
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['error_type'], 'branch_not_found')
        self.assertIn('feature/nonexistent', result['message'])

    def test_main_branch_rejection(self) -> None:
        """Attempting to push 'main' → branch_not_found (base branch guard)."""
        _init_repo(self.path)
        args = Namespace(plan_id=None, project_dir=str(self.path), branch='main')
        result = cmd_force_push(args)
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['error_type'], 'branch_not_found')
        self.assertIn('base branch', result['message'])

    def test_master_branch_rejection(self) -> None:
        """Attempting to push 'master' → branch_not_found (base branch guard)."""
        _init_repo(self.path)
        # Create master branch
        subprocess.run(['git', '-C', str(self.path), 'checkout', '-b', 'master'], check=True)
        args = Namespace(plan_id=None, project_dir=str(self.path), branch='master')
        result = cmd_force_push(args)
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['error_type'], 'branch_not_found')
        self.assertIn('base branch', result['message'])

    def test_envelope_includes_project_dir_when_supplied(self) -> None:
        """Response envelope echoes project_dir when --project-dir is used."""
        _init_repo(self.path)
        # Use a nonexistent branch to get an early error (avoids needing a remote).
        args = Namespace(plan_id=None, project_dir=str(self.path), branch='feature/x')
        result = cmd_force_push(args)
        self.assertIn('project_dir', result)
        self.assertEqual(result['project_dir'], str(self.path))

    def test_envelope_excludes_plan_id_when_project_dir_path(self) -> None:
        """When --project-dir path is used, plan_id must not appear in response."""
        _init_repo(self.path)
        args = Namespace(plan_id=None, project_dir=str(self.path), branch='feature/x')
        result = cmd_force_push(args)
        self.assertNotIn('plan_id', result)


# ---------------------------------------------------------------------------
# Tier 2: cmd_force_push — push failure error mapping
# ---------------------------------------------------------------------------


class TestCmdForcePushPushFailures(unittest.TestCase):
    """Test push error categorization by monkeypatching run_git."""

    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        self.path = Path(self._tmpdir)
        _init_repo(self.path)
        _create_feature_branch(self.path, 'feature/x')
        self._orig_run_git = _mod.run_git

    def tearDown(self) -> None:
        import shutil
        _mod.run_git = self._orig_run_git
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def _patch_run_git(self, responses: dict) -> None:
        """Patch run_git to return canned responses keyed by args tuple."""
        def fake_run_git(args, **kwargs):
            key = tuple(args)
            for pattern, response in responses.items():
                if all(p in key for p in pattern):
                    return response
            # Fall through to real git for rev-parse --verify (branch existence)
            return self._orig_run_git(args, **kwargs)
        _mod.run_git = fake_run_git

    def test_non_fast_forward_rejection_mapped_to_push_rejected(self) -> None:
        """Lease violation with 'rejected' + 'non-fast-forward' → push_rejected_non_fast_forward."""
        self._patch_run_git({
            ('push', 'origin'): (1, '', 'error: failed to push some refs\n! [rejected] feature/x -> feature/x (non-fast-forward)'),
        })
        args = Namespace(plan_id=None, project_dir=str(self.path), branch='feature/x')
        result = cmd_force_push(args)
        self.assertEqual(result['status'], 'rejected')
        self.assertEqual(result['error_type'], 'push_rejected_non_fast_forward')

    def test_generic_push_failure_mapped_to_push_failed(self) -> None:
        """Non-rejection push failure → push_failed."""
        self._patch_run_git({
            ('push', 'origin'): (1, '', 'error: could not connect to remote'),
        })
        args = Namespace(plan_id=None, project_dir=str(self.path), branch='feature/x')
        result = cmd_force_push(args)
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['error_type'], 'push_failed')

    def test_success_path_returns_success_status(self) -> None:
        """Successful push returns status=success and branch/remote fields."""
        self._patch_run_git({
            ('push', 'origin'): (0, '', ''),
            ('ls-remote', 'origin'): (0, 'abc123\trefs/heads/feature/x\n', ''),
        })
        args = Namespace(plan_id=None, project_dir=str(self.path), branch='feature/x')
        result = cmd_force_push(args)
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['branch'], 'feature/x')
        self.assertEqual(result['remote'], 'origin')
        self.assertIn('remote_sha', result)
        self.assertEqual(result['remote_sha'], 'abc123')

    def test_success_without_ls_remote_omits_remote_sha(self) -> None:
        """When ls-remote fails, remote_sha is absent (not None or empty)."""
        self._patch_run_git({
            ('push', 'origin'): (0, '', ''),
            ('ls-remote', 'origin'): (1, '', 'connection failed'),
        })
        args = Namespace(plan_id=None, project_dir=str(self.path), branch='feature/x')
        result = cmd_force_push(args)
        self.assertEqual(result['status'], 'success')
        self.assertNotIn('remote_sha', result)


# ---------------------------------------------------------------------------
# Tier 3: CLI plumbing
# ---------------------------------------------------------------------------


class TestCmdForcePushCli(unittest.TestCase):
    """Subprocess tests for CLI plumbing of force-push-with-lease."""

    def test_missing_plan_id_and_project_dir_exits_with_error(self) -> None:
        """Neither --plan-id nor --project-dir produces a structured error."""
        result = run_script(_SCRIPT_PATH, 'force-push-with-lease')
        # Expected: exit 0 with TOON error (argparse supplies both as optional)
        parsed = parse_toon(result.stdout)
        self.assertEqual(parsed['status'], 'error')

    def test_project_dir_requires_branch(self) -> None:
        """--project-dir without --branch returns missing_required_arg error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_script(
                _SCRIPT_PATH, 'force-push-with-lease',
                '--project-dir', tmpdir,
            )
            parsed = parse_toon(result.stdout)
            self.assertEqual(parsed['status'], 'error')
            self.assertEqual(parsed['error_type'], 'missing_required_arg')

    def test_help_flag_shows_force_push_subcommand(self) -> None:
        """--help lists force-push-with-lease in output."""
        result = run_script(_SCRIPT_PATH, '--help')
        self.assertEqual(result.returncode, 0)
        self.assertIn('force-push-with-lease', result.stdout)


if __name__ == '__main__':
    unittest.main()
