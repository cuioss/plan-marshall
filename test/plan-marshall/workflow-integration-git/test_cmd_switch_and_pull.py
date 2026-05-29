"""Tests for _cmd_switch_and_pull.py — switch-and-pull verb.

Tier 2 (direct import) tests covering:
* _resolve_project_dir — --project-dir escape-hatch path
* _verify_git_repo     — non-git path detection
* cmd_switch_and_pull  — remote branch not found, merge_conflict on checkout,
                         pull failure, success path with commits_pulled, and
                         success path with zero commits_pulled

Tier 3 (subprocess CLI plumbing) tests:
* Missing --base arg is rejected
* --project-dir with --base produces a structured error (non-git path)
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

_SWITCH_AND_PULL_PATH = get_script_path(
    'plan-marshall', 'workflow-integration-git', '_cmd_switch_and_pull.py'
)
_SCRIPT_PATH = get_script_path('plan-marshall', 'workflow-integration-git', 'git-workflow.py')

_spec = importlib.util.spec_from_file_location('_cmd_switch_and_pull', _SWITCH_AND_PULL_PATH)
assert _spec is not None and _spec.loader is not None
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

cmd_switch_and_pull = _mod.cmd_switch_and_pull
_resolve_project_dir = _mod._resolve_project_dir
_verify_git_repo = _mod._verify_git_repo
_find_executor = _mod._find_executor


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _init_repo(path: Path) -> str:
    """Initialise a minimal git repo on main, return the initial HEAD SHA."""
    subprocess.run(['git', 'init', '-q', '-b', 'main', str(path)], check=True)
    subprocess.run(['git', '-C', str(path), 'config', 'user.email', 't@t.test'], check=True)
    subprocess.run(['git', '-C', str(path), 'config', 'user.name', 'Test'], check=True)
    (path / 'README.md').write_text('initial\n')
    subprocess.run(['git', '-C', str(path), 'add', 'README.md'], check=True)
    subprocess.run(['git', '-C', str(path), 'commit', '-m', 'init'], check=True)
    result = subprocess.run(
        ['git', '-C', str(path), 'rev-parse', 'HEAD'],
        capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()


# ---------------------------------------------------------------------------
# Tier 2: _verify_git_repo
# ---------------------------------------------------------------------------


class TestVerifyGitRepo(unittest.TestCase):
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

    def test_returns_error_string_for_non_git_path(self) -> None:
        """Returns an error string when path is not a git repo."""
        result = _verify_git_repo(self.path)
        self.assertIsNotNone(result)
        self.assertIn('working tree', result or '')


# ---------------------------------------------------------------------------
# Tier 2: _resolve_project_dir — escape-hatch path
# ---------------------------------------------------------------------------


class TestResolveProjectDir(unittest.TestCase):
    def test_project_dir_returns_path(self) -> None:
        """--project-dir escape-hatch resolves to a Path object."""
        args = Namespace(plan_id=None, project_dir='/some/path')
        path, error = _resolve_project_dir(args)
        self.assertIsNone(error)
        self.assertEqual(path, Path('/some/path'))

    def test_missing_both_args_returns_error(self) -> None:
        """Neither --plan-id nor --project-dir → missing_required_arg."""
        args = Namespace(plan_id=None, project_dir=None)
        path, error = _resolve_project_dir(args)
        self.assertIsNone(path)
        self.assertIsNotNone(error)
        assert error is not None
        self.assertEqual(error['error_type'], 'missing_required_arg')


# ---------------------------------------------------------------------------
# Tier 2: cmd_switch_and_pull — project-dir escape-hatch
# ---------------------------------------------------------------------------


class TestCmdSwitchAndPullEscapeHatch(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        self.path = Path(self._tmpdir)
        self._orig_run_git = _mod.run_git

    def tearDown(self) -> None:
        import shutil
        _mod.run_git = self._orig_run_git
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_non_git_project_dir_returns_error(self) -> None:
        """--project-dir that is not a git repo → project_dir_not_a_git_repo."""
        args = Namespace(plan_id=None, project_dir=str(self.path), base='main')
        result = cmd_switch_and_pull(args)
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['error_type'], 'project_dir_not_a_git_repo')
        self.assertEqual(result['operation'], 'switch-and-pull')

    def test_remote_branch_not_found_returns_error(self) -> None:
        """When ls-remote returns empty output, error_type is branch_not_found."""
        _init_repo(self.path)

        def fake_run_git(args, **kwargs):
            if 'ls-remote' in args:
                return (0, '', '')  # empty: branch not found on remote
            return self._orig_run_git(args, **kwargs)

        _mod.run_git = fake_run_git
        args = Namespace(plan_id=None, project_dir=str(self.path), base='main')
        result = cmd_switch_and_pull(args)
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['error_type'], 'branch_not_found')
        self.assertIn('origin/main', result['message'])

    def test_ls_remote_failure_returns_branch_not_found(self) -> None:
        """When ls-remote exits non-zero, error_type is branch_not_found."""
        _init_repo(self.path)

        def fake_run_git(args, **kwargs):
            if 'ls-remote' in args:
                return (1, '', 'connection refused')
            return self._orig_run_git(args, **kwargs)

        _mod.run_git = fake_run_git
        args = Namespace(plan_id=None, project_dir=str(self.path), base='main')
        result = cmd_switch_and_pull(args)
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['error_type'], 'branch_not_found')

    def test_checkout_conflict_keywords_classification(self) -> None:
        """Checkout failure keywords are classified correctly.

        This test patches run_git to intercept ALL git calls after git-repo
        verification, so the checkout error type classification can be tested
        without relying on the real git binary for the checkout step.
        """
        _init_repo(self.path)
        # After the patch, ALL run_git calls are intercepted (not just some).
        # We must cover: rev-parse --show-toplevel, ls-remote, rev-parse HEAD, checkout.

        for keyword, expected_type in [
            ('conflict', 'merge_conflict'),
            ('overwrite', 'merge_conflict'),
            ('uncommitted', 'merge_conflict'),
            ('unrelated error here', 'pull_failed'),
        ]:
            with self.subTest(keyword=keyword, expected=expected_type):
                # Re-save orig in case a previous subtest left the patch.
                orig = self._orig_run_git

                def make_fake(kw: str, _orig=orig):
                    def fake_run_git(git_args, **kwargs):
                        a = list(git_args)
                        if 'rev-parse' in a and '--show-toplevel' in a:
                            # _verify_git_repo — must succeed for real.
                            return _orig(git_args, **kwargs)
                        if 'ls-remote' in a:
                            return (0, 'abc123\trefs/heads/main\n', '')
                        if 'rev-parse' in a:
                            # pre_sha capture.
                            return (0, 'deadbeef', '')
                        if 'checkout' in a:
                            return (1, '', f'error: {kw}')
                        return (0, '', '')
                    return fake_run_git

                _mod.run_git = make_fake(keyword)
                args = Namespace(plan_id=None, project_dir=str(self.path), base='main')
                result = cmd_switch_and_pull(args)
                _mod.run_git = orig  # restore after each sub-iteration

                self.assertEqual(result['status'], 'error', f'keyword={keyword!r}')
                self.assertEqual(
                    result['error_type'], expected_type,
                    f'keyword={keyword!r}: expected {expected_type!r}, got {result["error_type"]!r}',
                )

    def test_pull_failure_returns_pull_failed(self) -> None:
        """git pull non-zero exit → pull_failed."""
        _init_repo(self.path)

        def fake_run_git(args, **kwargs):
            if 'ls-remote' in args:
                return (0, 'abc123\trefs/heads/main\n', '')
            if 'rev-parse' in args and 'HEAD' in args:
                return (0, 'abc123', '')
            if 'checkout' in args:
                return (0, '', '')
            if 'pull' in args:
                return (1, '', 'error: network unreachable')
            return self._orig_run_git(args, **kwargs)

        _mod.run_git = fake_run_git
        args = Namespace(plan_id=None, project_dir=str(self.path), base='main')
        result = cmd_switch_and_pull(args)
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['error_type'], 'pull_failed')
        self.assertIn('pre_sha', result)

    def test_success_path_returns_required_fields(self) -> None:
        """Successful switch-and-pull returns status, pre_sha, post_sha, commits_pulled."""
        _init_repo(self.path)
        pre_sha = 'aaa111'
        post_sha = 'bbb222'

        def fake_run_git(args, **kwargs):
            if 'ls-remote' in args:
                return (0, f'{post_sha}\trefs/heads/main\n', '')
            if 'rev-parse' in args and 'HEAD' in args:
                return (0, pre_sha, '')
            if 'checkout' in args:
                return (0, '', '')
            if 'pull' in args:
                return (0, '', '')
            if 'rev-list' in args and '--count' in args:
                return (0, '2', '')
            if 'rev-parse' in args:
                return (0, post_sha, '')
            return self._orig_run_git(args, **kwargs)

        _mod.run_git = fake_run_git
        args = Namespace(plan_id=None, project_dir=str(self.path), base='main')
        result = cmd_switch_and_pull(args)
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['operation'], 'switch-and-pull')
        self.assertEqual(result['base_branch'], 'main')
        self.assertIn('pre_sha', result)
        self.assertIn('post_sha', result)
        self.assertIn('commits_pulled', result)
        self.assertEqual(result['commits_pulled'], 2)

    def test_success_zero_commits_pulled(self) -> None:
        """Already-up-to-date pull returns commits_pulled = 0."""
        _init_repo(self.path)
        sha = 'aaa111'

        def fake_run_git(args, **kwargs):
            if 'ls-remote' in args:
                return (0, f'{sha}\trefs/heads/main\n', '')
            if 'rev-parse' in args and 'HEAD' in args:
                return (0, sha, '')
            if 'checkout' in args:
                return (0, '', '')
            if 'pull' in args:
                return (0, 'Already up to date.', '')
            if 'rev-list' in args and '--count' in args:
                return (0, '0', '')
            if 'rev-parse' in args:
                return (0, sha, '')
            return self._orig_run_git(args, **kwargs)

        _mod.run_git = fake_run_git
        args = Namespace(plan_id=None, project_dir=str(self.path), base='main')
        result = cmd_switch_and_pull(args)
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['commits_pulled'], 0)

    def test_envelope_echoes_base_branch(self) -> None:
        """Response envelope always includes operation and base_branch."""
        _init_repo(self.path)

        def fake_run_git(args, **kwargs):
            if 'ls-remote' in args:
                return (0, '', '')  # trigger branch_not_found early
            return self._orig_run_git(args, **kwargs)

        _mod.run_git = fake_run_git
        args = Namespace(plan_id=None, project_dir=str(self.path), base='develop')
        result = cmd_switch_and_pull(args)
        self.assertEqual(result['operation'], 'switch-and-pull')
        self.assertEqual(result['base_branch'], 'develop')


# ---------------------------------------------------------------------------
# Tier 2: _find_executor — helper-based executor path resolution
# ---------------------------------------------------------------------------


class TestFindExecutor(unittest.TestCase):
    """Direct-import tests for _find_executor's helper-based resolution.

    _find_executor delegates to ``file_ops.get_executor_path()`` (worktree-safe
    resolution via git-common-dir) and returns the resolved path only when it
    exists on disk, falling back to None on RuntimeError (no git repo) or a
    missing executor file.
    """

    def setUp(self) -> None:
        import file_ops  # type: ignore[import-not-found]
        self._file_ops = file_ops
        self._orig_get_executor_path = file_ops.get_executor_path
        self._tmpdir = tempfile.mkdtemp()
        self.path = Path(self._tmpdir)

    def tearDown(self) -> None:
        import shutil
        self._file_ops.get_executor_path = self._orig_get_executor_path
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_returns_resolved_path_when_executor_exists(self) -> None:
        """When get_executor_path resolves an existing file, return it."""
        executor = self.path / 'execute-script.py'
        executor.write_text('# executor\n')
        self._file_ops.get_executor_path = lambda: executor
        result = _find_executor()
        self.assertEqual(result, executor)

    def test_returns_none_when_executor_missing(self) -> None:
        """When the resolved path does not exist on disk, return None."""
        missing = self.path / 'execute-script.py'  # never created
        self._file_ops.get_executor_path = lambda: missing
        result = _find_executor()
        self.assertIsNone(result)

    def test_returns_none_when_helper_raises_runtime_error(self) -> None:
        """When get_executor_path raises RuntimeError (no git repo), return None."""
        def _raise() -> Path:
            raise RuntimeError('no git repository')
        self._file_ops.get_executor_path = _raise
        result = _find_executor()
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# Tier 3: CLI plumbing
# ---------------------------------------------------------------------------


class TestCmdSwitchAndPullCli(unittest.TestCase):
    """Subprocess tests for switch-and-pull CLI plumbing."""

    def test_missing_base_arg_exits_nonzero(self) -> None:
        """--base is required; omitting it produces argparse error (exit != 0)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_script(
                _SCRIPT_PATH, 'switch-and-pull',
                '--project-dir', tmpdir,
            )
            self.assertNotEqual(result.returncode, 0)

    def test_non_git_project_dir_returns_toon_error(self) -> None:
        """Non-git --project-dir + --base produces structured TOON error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_script(
                _SCRIPT_PATH, 'switch-and-pull',
                '--project-dir', tmpdir,
                '--base', 'main',
            )
            parsed = parse_toon(result.stdout)
            self.assertEqual(parsed['status'], 'error')
            self.assertEqual(parsed['error_type'], 'project_dir_not_a_git_repo')

    def test_help_shows_switch_and_pull(self) -> None:
        """--help lists switch-and-pull subcommand."""
        result = run_script(_SCRIPT_PATH, '--help')
        self.assertEqual(result.returncode, 0)
        self.assertIn('switch-and-pull', result.stdout)


if __name__ == '__main__':
    unittest.main()
