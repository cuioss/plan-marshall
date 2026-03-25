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
SCRIPT_PATH = get_script_path('plan-marshall', 'workflow-integration-ci', 'pr.py')


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


class TestParseToonComments(unittest.TestCase):
    """Test parse_toon_comments function directly."""

    def _import_parse_toon_comments(self):
        """Import parse_toon_comments from pr.py."""
        import importlib.util

        spec = importlib.util.spec_from_file_location('pr', SCRIPT_PATH)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.parse_toon_comments

    def test_parses_comments_with_space_indented_rows(self):
        """Test that space-indented TOON table rows are parsed correctly."""
        parse_toon_comments = self._import_parse_toon_comments()
        toon_output = (
            'status: success\n'
            'total: 2\n'
            'unresolved: 1\n'
            'comments[2]{id,author,body,path,line,resolved,created_at}:\n'
            '  PRRC_001\treviewer1\tFix this bug\tsrc/Main.java\t42\ttrue\t2026-03-25\n'
            '  PRRC_002\treviewer2\tAdd tests\tsrc/Test.java\t10\tfalse\t2026-03-25\n'
        )
        comments = parse_toon_comments(toon_output)
        self.assertEqual(len(comments), 2)
        self.assertEqual(comments[0]['id'], 'PRRC_001')
        self.assertEqual(comments[0]['author'], 'reviewer1')
        self.assertEqual(comments[0]['body'], 'Fix this bug')
        self.assertEqual(comments[0]['path'], 'src/Main.java')
        self.assertEqual(comments[0]['line'], 42)
        self.assertTrue(comments[0]['resolved'])
        self.assertEqual(comments[1]['id'], 'PRRC_002')
        self.assertFalse(comments[1]['resolved'])

    def test_parses_empty_comments_table(self):
        """Test parsing a TOON output with no comment rows."""
        parse_toon_comments = self._import_parse_toon_comments()
        toon_output = 'status: success\ntotal: 0\ncomments[0]{id,author,body,path,line,resolved,created_at}:\n'
        comments = parse_toon_comments(toon_output)
        self.assertEqual(len(comments), 0)

    def test_handles_dash_values_for_path_and_line(self):
        """Test that dash values are converted to None."""
        parse_toon_comments = self._import_parse_toon_comments()
        toon_output = (
            'comments[1]{id,author,body,path,line,resolved,created_at}:\n'
            '  PRRC_003\treviewer\tGeneral comment\t-\t-\tfalse\t2026-03-25\n'
        )
        comments = parse_toon_comments(toon_output)
        self.assertEqual(len(comments), 1)
        self.assertIsNone(comments[0]['path'])
        self.assertIsNone(comments[0]['line'])

    def test_stops_at_next_toon_section(self):
        """Test that parser stops when reaching a new key: value section."""
        parse_toon_comments = self._import_parse_toon_comments()
        toon_output = (
            'comments[1]{id,author,body,path,line,resolved,created_at}:\n'
            '  PRRC_004\treviewer\tComment\tsrc/A.java\t1\ttrue\t2026-03-25\n'
            'next_section: value\n'
        )
        comments = parse_toon_comments(toon_output)
        self.assertEqual(len(comments), 1)

    def test_parses_thread_id_when_present(self):
        """Test that thread_id is included when the TOON header declares it."""
        parse_toon_comments = self._import_parse_toon_comments()
        toon_output = (
            'comments[1]{id,thread_id,author,body,path,line,resolved,created_at}:\n'
            '  PRRC_001\tPRRT_abc123\treviewer1\tFix bug\tsrc/Main.java\t42\ttrue\t2026-03-25\n'
        )
        comments = parse_toon_comments(toon_output)
        self.assertEqual(len(comments), 1)
        self.assertEqual(comments[0]['id'], 'PRRC_001')
        self.assertEqual(comments[0]['thread_id'], 'PRRT_abc123')
        self.assertEqual(comments[0]['author'], 'reviewer1')

    def test_no_thread_id_when_not_in_header(self):
        """Test that thread_id is absent when the TOON header does not declare it."""
        parse_toon_comments = self._import_parse_toon_comments()
        toon_output = (
            'comments[1]{id,author,body,path,line,resolved,created_at}:\n'
            '  PRRC_001\treviewer1\tFix bug\tsrc/Main.java\t42\ttrue\t2026-03-25\n'
        )
        comments = parse_toon_comments(toon_output)
        self.assertEqual(len(comments), 1)
        self.assertNotIn('thread_id', comments[0])


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
