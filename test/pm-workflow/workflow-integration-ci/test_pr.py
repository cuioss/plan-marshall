"""Tests for pr.py - consolidated PR workflow script (provider-agnostic)."""

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

# Import shared infrastructure
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from toon_parser import parse_toon  # type: ignore[import-not-found]  # noqa: E402

from conftest import _MARKETPLACE_SCRIPT_DIRS, get_script_path  # noqa: E402

# Script under test
SCRIPT_PATH = get_script_path('pm-workflow', 'workflow-integration-ci', 'pr.py')


def run_pr_script(args: list) -> tuple:
    """Run pr.py with args and return (stdout, stderr, returncode)."""
    env = os.environ.copy()
    pythonpath = os.pathsep.join(_MARKETPLACE_SCRIPT_DIRS)
    if 'PYTHONPATH' in env:
        pythonpath = pythonpath + os.pathsep + env['PYTHONPATH']
    env['PYTHONPATH'] = pythonpath
    result = subprocess.run([sys.executable, str(SCRIPT_PATH)] + args, capture_output=True, text=True, env=env)
    return result.stdout, result.stderr, result.returncode


class TestPRTriage(unittest.TestCase):
    """Test pr.py triage subcommand."""

    def test_triage_high_priority_bug(self):
        """Test triage identifies bug as high priority."""
        comment = {
            'id': 'C1',
            'body': 'This is a bug that needs to be fixed',
            'path': 'src/Main.java',
            'line': 42,
            'author': 'reviewer',
        }
        stdout, _, code = run_pr_script(['triage', '--comment', json.dumps(comment)])
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
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
        stdout, _, code = run_pr_script(['triage', '--comment', json.dumps(comment)])
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
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
        stdout, _, code = run_pr_script(['triage', '--comment', json.dumps(comment)])
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
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
        stdout, _, code = run_pr_script(['triage', '--comment', json.dumps(comment)])
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
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
        stdout, _, code = run_pr_script(['triage', '--comment', json.dumps(comment)])
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
        self.assertEqual(result['action'], 'explain')
        self.assertEqual(result['priority'], 'low')

    def test_triage_lgtm_ignored(self):
        """Test triage ignores LGTM comments."""
        comment = {'id': 'C6', 'body': 'LGTM!', 'path': None, 'line': None, 'author': 'approver'}
        stdout, _, code = run_pr_script(['triage', '--comment', json.dumps(comment)])
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
        self.assertEqual(result['action'], 'ignore')
        self.assertEqual(result['priority'], 'none')

    def test_triage_nitpick_ignored(self):
        """Test triage ignores nitpick comments."""
        comment = {
            'id': 'C7',
            'body': 'nit: extra space here',
            'path': 'src/Format.java',
            'line': 15,
            'author': 'reviewer',
        }
        stdout, _, code = run_pr_script(['triage', '--comment', json.dumps(comment)])
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
        self.assertEqual(result['action'], 'ignore')

    def test_triage_empty_body(self):
        """Test triage handles empty comment body."""
        comment = {'id': 'C8', 'body': '', 'path': 'src/Empty.java', 'line': 1, 'author': 'reviewer'}
        stdout, _, code = run_pr_script(['triage', '--comment', json.dumps(comment)])
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
        self.assertEqual(result['action'], 'ignore')
        self.assertIn('Empty', result['reason'])

    def test_triage_invalid_json(self):
        """Test triage handles invalid JSON."""
        stdout, _, code = run_pr_script(['triage', '--comment', 'not-valid-json'])
        self.assertEqual(code, 1)
        result = parse_toon(stdout)
        self.assertEqual(result['status'], 'failure')
        self.assertIn('Invalid JSON', result['error'])

    def test_triage_missing_comment(self):
        """Test triage without required comment arg."""
        _, stderr, code = run_pr_script(['triage'])
        self.assertNotEqual(code, 0)
        self.assertIn('--comment', stderr)

    def test_triage_location_formatting(self):
        """Test triage formats location correctly."""
        comment = {
            'id': 'C9',
            'body': 'Please fix this error',
            'path': 'src/File.java',
            'line': 99,
            'author': 'reviewer',
        }
        stdout, _, code = run_pr_script(['triage', '--comment', json.dumps(comment)])
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
        self.assertEqual(result['location'], 'src/File.java:99')


class TestPRFetchComments(unittest.TestCase):
    """Test pr.py fetch-comments subcommand.

    Note: These tests verify argument parsing without actual CI CLI calls.
    The fetch-comments command now uses marshal.json routing for provider abstraction.
    """

    def test_fetch_comments_help(self):
        """Test fetch-comments help output."""
        stdout, _, code = run_pr_script(['fetch-comments', '--help'])
        self.assertEqual(code, 0)
        self.assertIn('--pr', stdout)
        self.assertIn('--unresolved-only', stdout)


class TestPRMain(unittest.TestCase):
    """Test pr.py main entry point."""

    def test_no_subcommand(self):
        """Test error when no subcommand provided."""
        _, stderr, code = run_pr_script([])
        self.assertNotEqual(code, 0)

    def test_help(self):
        """Test help output."""
        stdout, _, code = run_pr_script(['--help'])
        self.assertEqual(code, 0)
        self.assertIn('fetch-comments', stdout)
        self.assertIn('triage', stdout)


if __name__ == '__main__':
    unittest.main()
