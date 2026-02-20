"""Tests for git-workflow.py - consolidated git workflow script."""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# Import shared infrastructure
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from toon_parser import parse_toon  # type: ignore[import-not-found]  # noqa: E402

from conftest import _MARKETPLACE_SCRIPT_DIRS, get_script_path  # noqa: E402

# Script under test
SCRIPT_PATH = get_script_path('pm-workflow', 'workflow-integration-git', 'git-workflow.py')


def run_git_script(args: list) -> tuple:
    """Run git-workflow.py with args and return (stdout, stderr, returncode)."""
    env = os.environ.copy()
    pythonpath = os.pathsep.join(_MARKETPLACE_SCRIPT_DIRS)
    if 'PYTHONPATH' in env:
        pythonpath = pythonpath + os.pathsep + env['PYTHONPATH']
    env['PYTHONPATH'] = pythonpath
    result = subprocess.run([sys.executable, str(SCRIPT_PATH)] + args, capture_output=True, text=True, env=env)
    return result.stdout, result.stderr, result.returncode


class TestFormatCommit(unittest.TestCase):
    """Test git-workflow.py format-commit subcommand."""

    def test_basic_format(self):
        """Test basic commit message formatting."""
        stdout, _, code = run_git_script(['format-commit', '--type', 'feat', '--subject', 'add new feature'])
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
        self.assertEqual(result['type'], 'feat')
        self.assertEqual(result['subject'], 'add new feature')
        self.assertIn('feat: add new feature', result['formatted_message'])
        self.assertEqual(result['status'], 'success')

    def test_format_with_scope(self):
        """Test commit message with scope."""
        stdout, _, code = run_git_script(
            ['format-commit', '--type', 'fix', '--scope', 'auth', '--subject', 'fix login bug']
        )
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
        self.assertEqual(result['scope'], 'auth')
        self.assertIn('fix(auth):', result['formatted_message'])

    def test_format_with_body(self):
        """Test commit message with body."""
        stdout, _, code = run_git_script(
            [
                'format-commit',
                '--type',
                'docs',
                '--subject',
                'update readme',
                '--body',
                'Added installation instructions',
            ]
        )
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
        self.assertEqual(result['body'], 'Added installation instructions')
        self.assertIn('Added installation instructions', stdout)

    def test_format_with_breaking_change(self):
        """Test commit message with breaking change."""
        stdout, _, code = run_git_script(
            ['format-commit', '--type', 'feat', '--subject', 'change api', '--breaking', 'API signature changed']
        )
        self.assertEqual(code, 0)
        self.assertIn('feat!:', stdout)
        self.assertIn('BREAKING CHANGE:', stdout)

    def test_format_with_footer(self):
        """Test commit message with footer."""
        stdout, _, code = run_git_script(
            ['format-commit', '--type', 'fix', '--subject', 'fix crash', '--footer', 'Fixes #123']
        )
        self.assertEqual(code, 0)
        self.assertIn('Fixes #123', stdout)

    def test_all_commit_types(self):
        """Test all valid commit types."""
        valid_types = ['feat', 'fix', 'docs', 'style', 'refactor', 'perf', 'test', 'chore']
        for commit_type in valid_types:
            stdout, _, code = run_git_script(['format-commit', '--type', commit_type, '--subject', 'test subject'])
            self.assertEqual(code, 0, f'Failed for type: {commit_type}')
            result = parse_toon(stdout)
            self.assertEqual(result['type'], commit_type)

    def test_validation_warning_long_subject(self):
        """Test validation warning for long subject."""
        long_subject = 'a' * 55  # Exceeds 50 chars
        stdout, _, code = run_git_script(['format-commit', '--type', 'fix', '--subject', long_subject])
        self.assertEqual(code, 0)  # Still valid, just warning
        result = parse_toon(stdout)
        self.assertTrue(result['validation']['valid'])
        self.assertTrue(any('50 chars' in w for w in result['validation']['warnings']))

    def test_validation_error_very_long_subject(self):
        """Test validation error for very long subject."""
        very_long_subject = 'a' * 75  # Exceeds 72 chars
        stdout, _, code = run_git_script(['format-commit', '--type', 'fix', '--subject', very_long_subject])
        self.assertEqual(code, 1)  # Invalid
        result = parse_toon(stdout)
        self.assertFalse(result['validation']['valid'])

    def test_validation_warning_past_tense(self):
        """Test validation warning for past tense verb."""
        stdout, _, code = run_git_script(['format-commit', '--type', 'fix', '--subject', 'fixed the bug'])
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
        self.assertTrue(any('imperative' in w.lower() for w in result['validation']['warnings']))

    def test_missing_required_args(self):
        """Test error when required args missing."""
        _, stderr, code = run_git_script(['format-commit'])
        self.assertNotEqual(code, 0)
        self.assertIn('--type', stderr)

    def test_claude_footer_present(self):
        """Test that Claude footer is present."""
        stdout, _, code = run_git_script(['format-commit', '--type', 'feat', '--subject', 'add feature'])
        self.assertEqual(code, 0)
        self.assertIn('Claude Code', stdout)
        self.assertIn('Co-Authored-By', stdout)


class TestAnalyzeDiff(unittest.TestCase):
    """Test git-workflow.py analyze-diff subcommand."""

    def test_analyze_bug_fix(self):
        """Test analysis detects bug fix patterns."""
        diff_content = """diff --git a/src/main/java/Service.java b/src/main/java/Service.java
--- a/src/main/java/Service.java
+++ b/src/main/java/Service.java
-    return null;
+    if (value == null) throw new IllegalArgumentException();
+    return value;
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.diff', delete=False) as f:
            f.write(diff_content)
            f.flush()

            stdout, _, code = run_git_script(['analyze-diff', '--file', f.name])
            self.assertEqual(code, 0)
            result = parse_toon(stdout)
            self.assertEqual(result['status'], 'success')

    def test_analyze_file_not_found(self):
        """Test error when diff file not found."""
        stdout, _, code = run_git_script(['analyze-diff', '--file', '/nonexistent/file.diff'])
        self.assertEqual(code, 1)
        result = parse_toon(stdout)
        self.assertEqual(result['status'], 'failure')
        self.assertIn('not found', result['error'])

    def test_missing_file_arg(self):
        """Test error when file arg missing."""
        _, stderr, code = run_git_script(['analyze-diff'])
        self.assertNotEqual(code, 0)
        self.assertIn('--file', stderr)


class TestMain(unittest.TestCase):
    """Test git-workflow.py main entry point."""

    def test_no_subcommand(self):
        """Test error when no subcommand provided."""
        _, stderr, code = run_git_script([])
        self.assertNotEqual(code, 0)

    def test_help(self):
        """Test help output."""
        stdout, _, code = run_git_script(['--help'])
        self.assertEqual(code, 0)
        self.assertIn('format-commit', stdout)
        self.assertIn('analyze-diff', stdout)


if __name__ == '__main__':
    unittest.main()
