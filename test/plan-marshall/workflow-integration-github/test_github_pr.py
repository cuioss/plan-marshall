"""Tests for workflow-integration-github pr.py - GitHub PR workflow script.

Tier 2 (direct import) tests with subprocess tests for CLI plumbing.
Adapted from workflow-integration-ci tests for GitHub-specific provider.
"""

import importlib.util
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from conftest import get_script_path, run_script

# Script under test (for subprocess CLI plumbing tests)
SCRIPT_PATH = get_script_path('plan-marshall', 'workflow-integration-github', 'github_pr.py')

# Tier 2 direct imports — use explicit path to avoid module name collision
# with workflow-integration-gitlab/scripts/pr.py
_pr_path = Path(SCRIPT_PATH)
_spec = importlib.util.spec_from_file_location('github_pr', _pr_path)
assert _spec is not None and _spec.loader is not None
github_pr = importlib.util.module_from_spec(_spec)
sys.modules['github_pr'] = github_pr
_spec.loader.exec_module(github_pr)

classify_comment = github_pr.classify_comment
fetch_comments = github_pr.fetch_comments
get_current_pr_number = github_pr.get_current_pr_number
triage_comment = github_pr.triage_comment

from triage_helpers import cmd_triage_batch_handler  # type: ignore[import-not-found]  # noqa: E402


class TestPRTriage(unittest.TestCase):
    """Test pr.py triage via direct import."""

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
        self.assertEqual(result['status'], 'success')

    def test_triage_security_issue(self):
        """Test triage identifies security issues as high priority."""
        comment = {
            'id': 'C2',
            'body': 'Security vulnerability here - potential injection',
            'path': 'src/Auth.java',
            'line': 10,
            'author': 'security-reviewer',
        }
        result = triage_comment(comment)
        self.assertEqual(result['action'], 'code_change')
        self.assertEqual(result['priority'], 'high')

    def test_triage_medium_priority_change_request(self):
        """Test triage identifies change requests as medium priority."""
        comment = {
            'id': 'C3',
            'body': 'Please add validation for the input parameters',
            'path': 'src/Service.java',
            'line': 25,
            'author': 'reviewer',
        }
        result = triage_comment(comment)
        self.assertEqual(result['action'], 'code_change')
        self.assertEqual(result['priority'], 'medium')

    def test_triage_low_priority_naming(self):
        """Test triage identifies naming issues as low priority."""
        comment = {
            'id': 'C4',
            'body': 'Consider renaming this variable to be more descriptive',
            'path': 'src/Utils.java',
            'line': 5,
            'author': 'reviewer',
        }
        result = triage_comment(comment)
        self.assertEqual(result['action'], 'code_change')
        self.assertEqual(result['priority'], 'low')

    def test_triage_explanation_request(self):
        """Test triage identifies questions requiring explanation."""
        comment = {
            'id': 'C5',
            'body': 'Why did you choose this approach?',
            'path': 'src/Design.java',
            'line': 100,
            'author': 'reviewer',
        }
        result = triage_comment(comment)
        self.assertEqual(result['action'], 'explain')
        self.assertEqual(result['priority'], 'low')

    def test_triage_lgtm_ignored(self):
        """Test triage ignores LGTM comments."""
        comment = {'id': 'C6', 'body': 'LGTM!', 'path': None, 'line': None, 'author': 'approver'}
        result = triage_comment(comment)
        self.assertEqual(result['action'], 'ignore')
        self.assertEqual(result['priority'], 'low')

    def test_triage_empty_body(self):
        """Test triage handles empty comment body."""
        comment = {'id': 'C8', 'body': '', 'path': 'src/Empty.java', 'line': 1, 'author': 'reviewer'}
        result = triage_comment(comment)
        self.assertEqual(result['action'], 'ignore')
        self.assertIn('Empty', result['reason'])


class TestPRTriageBatch(unittest.TestCase):
    """Test pr.py triage-batch via direct import."""

    def test_triage_batch_multiple_comments(self):
        """Test batch triage processes multiple comments at once."""
        comments = [
            {'id': 'B1', 'body': 'This is a bug', 'path': 'src/A.java', 'line': 1, 'author': 'r1'},
            {'id': 'B2', 'body': 'LGTM!', 'path': None, 'line': None, 'author': 'r2'},
            {'id': 'B3', 'body': 'Why did you do this?', 'path': 'src/B.java', 'line': 5, 'author': 'r3'},
        ]
        result = cmd_triage_batch_handler(json.dumps(comments), triage_comment, ['code_change', 'explain', 'ignore'])
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['summary']['total'], 3)
        self.assertEqual(result['summary']['code_change'], 1)
        self.assertEqual(result['summary']['ignore'], 1)
        self.assertEqual(result['summary']['explain'], 1)

    def test_triage_batch_empty_list(self):
        """Test batch triage with empty list."""
        result = cmd_triage_batch_handler('[]', triage_comment, ['code_change', 'explain', 'ignore'])
        self.assertEqual(result['summary']['total'], 0)


class TestGitHubProviderDirect(unittest.TestCase):
    """Test that GitHub provider is used directly (no provider detection)."""

    def test_get_current_pr_number_uses_github_directly(self):
        """Test that get_current_pr_number calls github.view_pr_data directly."""
        with patch.object(github_pr, '_github') as mock_github:
            mock_github.view_pr_data.return_value = {'status': 'success', 'pr_number': 42}
            result = get_current_pr_number()
            self.assertEqual(result, 42)
            mock_github.view_pr_data.assert_called_once()

    def test_get_current_pr_number_returns_none_on_failure(self):
        """Test that get_current_pr_number returns None when GitHub returns error."""
        with patch.object(github_pr, '_github') as mock_github:
            mock_github.view_pr_data.return_value = {'status': 'error', 'error': 'Not found'}
            result = get_current_pr_number()
            self.assertIsNone(result)

    def test_fetch_comments_uses_github_directly(self):
        """Test that fetch_comments calls github.fetch_pr_comments_data directly."""
        with patch.object(github_pr, '_github') as mock_github:
            mock_github.fetch_pr_comments_data.return_value = {
                'status': 'success',
                'provider': 'github',
                'total': 1,
                'unresolved': 0,
                'comments': [{'id': 'C1', 'body': 'Test', 'path': 'f.py', 'line': 1}],
            }
            result = fetch_comments(123)
            self.assertEqual(result['status'], 'success')
            self.assertEqual(result['provider'], 'github')
            self.assertEqual(result['total_comments'], 1)
            mock_github.fetch_pr_comments_data.assert_called_once_with(123, False)

    def test_fetch_comments_preserves_kind_field(self):
        """Pass-through: fetch_comments must preserve the unified `kind`
        discriminator on every comment returned by fetch_pr_comments_data."""
        with patch.object(github_pr, '_github') as mock_github:
            mock_github.fetch_pr_comments_data.return_value = {
                'status': 'success',
                'provider': 'github',
                'total': 3,
                'unresolved': 3,
                'comments': [
                    {'id': 'I1', 'kind': 'inline', 'body': 'a', 'path': 'f.py', 'line': 1},
                    {'id': 'R1', 'kind': 'review_body', 'body': 'b', 'path': '', 'line': 0},
                    {'id': 'C1', 'kind': 'issue_comment', 'body': 'c', 'path': '', 'line': 0},
                ],
            }
            result = fetch_comments(456)
            self.assertEqual(result['status'], 'success')
            kinds = [c.get('kind') for c in result['comments']]
            self.assertEqual(kinds, ['inline', 'review_body', 'issue_comment'])


class TestClassifyCommentOrdering(unittest.TestCase):
    """Test that classify_comment checks code_change BEFORE ignore."""

    def test_lgtm_with_fix_request_is_code_change(self):
        """LGTM with actionable fix request should be code_change, not ignore."""
        result = classify_comment('LGTM, but please fix the typo in the variable name')
        self.assertEqual(result['action'], 'code_change')

    def test_pure_lgtm_still_ignored(self):
        """Pure LGTM without actionable content should still be ignore."""
        result = classify_comment('LGTM!')
        self.assertEqual(result['action'], 'ignore')


class TestToonContract(unittest.TestCase):
    """Verify output matches the contract documented in SKILL.md."""

    def test_triage_output_contract(self):
        """Verify triage output has all documented fields."""
        comment = {
            'id': 'CONTRACT1',
            'body': 'Please fix this bug',
            'path': 'src/File.java',
            'line': 10,
            'author': 'reviewer',
        }
        result = triage_comment(comment)
        required_fields = {'comment_id', 'action', 'reason', 'priority', 'suggested_implementation', 'status'}
        missing = required_fields - set(result.keys())
        self.assertEqual(missing, set(), f'Missing contract fields: {missing}')


# =============================================================================
# Subprocess (Tier 3) tests — CLI plumbing only
# =============================================================================


class TestPRMain(unittest.TestCase):
    """Test pr.py main entry point (CLI plumbing)."""

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

    def test_triage_missing_comment(self):
        """Test triage without required comment arg."""
        result = run_script(SCRIPT_PATH, 'triage')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('--comment', result.stderr)


class TestPRProjectDirPlumbing(unittest.TestCase):
    """Verify github_pr.main() strips --project-dir and forwards cwd."""

    def test_main_project_dir_sets_default_cwd(self):
        """main() installs --project-dir value as process-global default cwd
        before argparse runs."""
        import json

        import ci_base  # type: ignore[import-not-found]

        saved_argv = sys.argv
        saved_cwd = ci_base.get_default_cwd()
        try:
            ci_base.set_default_cwd(None)
            comment = json.dumps({'id': 'P1', 'body': 'LGTM', 'path': None, 'line': None, 'author': 'a'})
            sys.argv = [
                'github_pr.py',
                '--project-dir',
                '/tmp/worktree-pr',
                'triage',
                '--comment',
                comment,
            ]
            github_pr.main()
            self.assertEqual(ci_base.get_default_cwd(), '/tmp/worktree-pr')
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
            comment = json.dumps({'id': 'P2', 'body': 'ok', 'path': None, 'line': None, 'author': 'a'})
            sys.argv = [
                'github_pr.py',
                '--project-dir=/tmp/worktree-pr2',
                'triage',
                '--comment',
                comment,
            ]
            github_pr.main()
            self.assertEqual(ci_base.get_default_cwd(), '/tmp/worktree-pr2')
        finally:
            sys.argv = saved_argv
            ci_base.set_default_cwd(saved_cwd)


if __name__ == '__main__':
    unittest.main()
