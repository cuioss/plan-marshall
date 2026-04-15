"""Tests for workflow-integration-gitlab pr.py - GitLab MR workflow script.

Tier 2 (direct import) tests with subprocess tests for CLI plumbing.
"""

import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from conftest import get_script_path, run_script

# Script under test (for subprocess CLI plumbing tests)
SCRIPT_PATH = get_script_path('plan-marshall', 'workflow-integration-gitlab', 'gitlab_pr.py')

# Tier 2 direct imports — use explicit path to avoid module name collision
_pr_path = Path(SCRIPT_PATH)
_spec = importlib.util.spec_from_file_location('gitlab_pr', _pr_path)
assert _spec is not None and _spec.loader is not None
gitlab_pr = importlib.util.module_from_spec(_spec)
sys.modules['gitlab_pr'] = gitlab_pr
_spec.loader.exec_module(gitlab_pr)

classify_comment = gitlab_pr.classify_comment
fetch_comments = gitlab_pr.fetch_comments
get_current_pr_number = gitlab_pr.get_current_pr_number
triage_comment = gitlab_pr.triage_comment



class TestGitLabPRTriage(unittest.TestCase):
    """Test GitLab pr.py triage via direct import."""

    def test_triage_high_priority_bug(self):
        """Test triage identifies bug as high priority."""
        comment = {
            'id': 'C1',
            'body': 'This is a bug that needs to be fixed',
            'path': 'src/Main.java',
            'line': 42,
            'author': 'reviewer',
        }
        result = triage_comment(comment)
        self.assertEqual(result['action'], 'code_change')
        self.assertEqual(result['priority'], 'high')

    def test_triage_lgtm_ignored(self):
        """Test triage ignores LGTM comments."""
        comment = {'id': 'C6', 'body': 'LGTM!', 'path': None, 'line': None, 'author': 'approver'}
        result = triage_comment(comment)
        self.assertEqual(result['action'], 'ignore')


class TestGitLabProviderDirect(unittest.TestCase):
    """Test that GitLab provider is used directly (no provider detection)."""

    def test_get_current_pr_number_uses_gitlab_directly(self):
        """Test that get_current_pr_number calls gitlab.view_pr_data directly."""
        with patch.object(gitlab_pr, '_gitlab') as mock_gitlab:
            mock_gitlab.view_pr_data.return_value = {'status': 'success', 'pr_number': 42}
            result = get_current_pr_number()
            self.assertEqual(result, 42)
            mock_gitlab.view_pr_data.assert_called_once()

    def test_fetch_comments_uses_gitlab_directly(self):
        """Test that fetch_comments calls gitlab.fetch_pr_comments_data directly."""
        with patch.object(gitlab_pr, '_gitlab') as mock_gitlab:
            mock_gitlab.fetch_pr_comments_data.return_value = {
                'status': 'success',
                'provider': 'gitlab',
                'total': 1,
                'unresolved': 0,
                'comments': [{'id': 'C1', 'body': 'Test', 'path': 'f.py', 'line': 1}],
            }
            result = fetch_comments(123)
            self.assertEqual(result['status'], 'success')
            self.assertEqual(result['provider'], 'gitlab')
            mock_gitlab.fetch_pr_comments_data.assert_called_once_with(123, False)


class TestGitLabPRMain(unittest.TestCase):
    """Test GitLab pr.py main entry point (CLI plumbing)."""

    def test_no_subcommand(self):
        """Test error when no subcommand provided."""
        result = run_script(SCRIPT_PATH)
        self.assertNotEqual(result.returncode, 0)

    def test_help(self):
        """Test help output."""
        result = run_script(SCRIPT_PATH, '--help')
        self.assertEqual(result.returncode, 0)
        self.assertIn('fetch-comments', result.stdout)
        self.assertIn('triage', result.stdout)


class TestGitLabPRProjectDirPlumbing(unittest.TestCase):
    """Verify gitlab_pr.main() strips --project-dir and forwards cwd."""

    def test_main_project_dir_sets_default_cwd(self):
        """main() installs --project-dir value as process-global default cwd
        before argparse runs."""
        import json

        import ci_base  # type: ignore[import-not-found]

        saved_argv = sys.argv
        saved_cwd = ci_base.get_default_cwd()
        try:
            ci_base.set_default_cwd(None)
            comment = json.dumps(
                {'id': 'P1', 'body': 'LGTM', 'path': None, 'line': None, 'author': 'a'}
            )
            sys.argv = [
                'gitlab_pr.py',
                '--project-dir',
                '/tmp/worktree-glpr',
                'triage',
                '--comment',
                comment,
            ]
            gitlab_pr.main()
            self.assertEqual(ci_base.get_default_cwd(), '/tmp/worktree-glpr')
            self.assertNotIn('--project-dir', sys.argv)
        finally:
            sys.argv = saved_argv
            ci_base.set_default_cwd(saved_cwd)

    def test_main_project_dir_equals_form(self):
        """The --project-dir=PATH form is also accepted."""
        import json

        import ci_base  # type: ignore[import-not-found]

        saved_argv = sys.argv
        saved_cwd = ci_base.get_default_cwd()
        try:
            ci_base.set_default_cwd(None)
            comment = json.dumps(
                {'id': 'P2', 'body': 'ok', 'path': None, 'line': None, 'author': 'a'}
            )
            sys.argv = [
                'gitlab_pr.py',
                '--project-dir=/tmp/worktree-glpr2',
                'triage',
                '--comment',
                comment,
            ]
            gitlab_pr.main()
            self.assertEqual(ci_base.get_default_cwd(), '/tmp/worktree-glpr2')
        finally:
            sys.argv = saved_argv
            ci_base.set_default_cwd(saved_cwd)


if __name__ == '__main__':
    unittest.main()
