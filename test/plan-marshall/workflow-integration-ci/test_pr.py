"""Tests for pr.py - consolidated PR workflow script (provider-agnostic)."""

import json
import sys
import unittest
from pathlib import Path

# Import shared infrastructure
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from toon_parser import parse_toon, parse_toon_table  # type: ignore[import-not-found]  # noqa: E402

from conftest import get_script_path, run_script  # noqa: E402

# Script under test
SCRIPT_PATH = get_script_path('plan-marshall', 'workflow-integration-ci', 'pr.py')


def run_pr_script(args: list) -> tuple:
    """Run pr.py with args and return (stdout, stderr, returncode)."""
    result = run_script(SCRIPT_PATH, *args)
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

    def test_triage_nitpick_is_low_priority_code_change(self):
        """Test triage classifies nitpick as low-priority code change."""
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
        self.assertEqual(result['action'], 'code_change')
        self.assertEqual(result['priority'], 'low')

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


class TestPRTriageBatch(unittest.TestCase):
    """Test pr.py triage-batch subcommand."""

    def test_triage_batch_multiple_comments(self):
        """Test batch triage processes multiple comments at once."""
        comments = [
            {'id': 'B1', 'body': 'This is a bug', 'path': 'src/A.java', 'line': 1, 'author': 'r1'},
            {'id': 'B2', 'body': 'LGTM!', 'path': None, 'line': None, 'author': 'r2'},
            {'id': 'B3', 'body': 'Why did you do this?', 'path': 'src/B.java', 'line': 5, 'author': 'r3'},
        ]
        stdout, _, code = run_pr_script(['triage-batch', '--comments', json.dumps(comments)])
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['summary']['total'], 3)
        self.assertEqual(result['summary']['code_change'], 1)
        self.assertEqual(result['summary']['ignore'], 1)
        self.assertEqual(result['summary']['explain'], 1)

    def test_triage_batch_empty_list(self):
        """Test batch triage with empty list."""
        stdout, _, code = run_pr_script(['triage-batch', '--comments', '[]'])
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
        self.assertEqual(result['summary']['total'], 0)

    def test_triage_batch_invalid_json(self):
        """Test batch triage with invalid JSON."""
        stdout, _, code = run_pr_script(['triage-batch', '--comments', 'not-json'])
        self.assertEqual(code, 1)
        result = parse_toon(stdout)
        self.assertEqual(result['status'], 'failure')

    def test_triage_batch_not_array(self):
        """Test batch triage rejects non-array input."""
        stdout, _, code = run_pr_script(['triage-batch', '--comments', '{"id": "C1"}'])
        self.assertEqual(code, 1)
        result = parse_toon(stdout)
        self.assertEqual(result['status'], 'failure')
        self.assertIn('array', result['error'])


class TestParseToonTable(unittest.TestCase):
    """Test parse_toon_table from toon_parser for PR comment parsing."""

    def test_parses_comments_with_space_indented_rows(self):
        """Test that space-indented TOON table rows are parsed correctly."""
        toon_output = (
            'status: success\n'
            'total: 2\n'
            'unresolved: 1\n'
            'comments[2]{id,author,body,path,line,resolved,created_at}:\n'
            '  PRRC_001\treviewer1\tFix this bug\tsrc/Main.java\t42\ttrue\t2026-03-25\n'
            '  PRRC_002\treviewer2\tAdd tests\tsrc/Test.java\t10\tfalse\t2026-03-25\n'
        )
        comments = parse_toon_table(toon_output, 'comments')
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
        toon_output = 'status: success\ntotal: 0\ncomments[0]{id,author,body,path,line,resolved,created_at}:\n'
        comments = parse_toon_table(toon_output, 'comments')
        self.assertEqual(len(comments), 0)

    def test_handles_dash_values_with_null_markers(self):
        """Test that dash values are converted to None via null_markers."""
        toon_output = (
            'comments[1]{id,author,body,path,line,resolved,created_at}:\n'
            '  PRRC_003\treviewer\tGeneral comment\t-\t-\tfalse\t2026-03-25\n'
        )
        comments = parse_toon_table(toon_output, 'comments', null_markers={'-'})
        self.assertEqual(len(comments), 1)
        self.assertIsNone(comments[0]['path'])
        self.assertIsNone(comments[0]['line'])

    def test_stops_at_next_toon_section(self):
        """Test that parser stops when reaching a new key: value section."""
        toon_output = (
            'comments[1]{id,author,body,path,line,resolved,created_at}:\n'
            '  PRRC_004\treviewer\tComment\tsrc/A.java\t1\ttrue\t2026-03-25\n'
            'next_section: value\n'
        )
        comments = parse_toon_table(toon_output, 'comments')
        self.assertEqual(len(comments), 1)

    def test_parses_thread_id_when_present(self):
        """Test that thread_id is included when the TOON header declares it."""
        toon_output = (
            'comments[1]{id,thread_id,author,body,path,line,resolved,created_at}:\n'
            '  PRRC_001\tPRRT_abc123\treviewer1\tFix bug\tsrc/Main.java\t42\ttrue\t2026-03-25\n'
        )
        comments = parse_toon_table(toon_output, 'comments')
        self.assertEqual(len(comments), 1)
        self.assertEqual(comments[0]['id'], 'PRRC_001')
        self.assertEqual(comments[0]['thread_id'], 'PRRT_abc123')
        self.assertEqual(comments[0]['author'], 'reviewer1')

    def test_no_thread_id_when_not_in_header(self):
        """Test that thread_id is absent when the TOON header does not declare it."""
        toon_output = (
            'comments[1]{id,author,body,path,line,resolved,created_at}:\n'
            '  PRRC_001\treviewer1\tFix bug\tsrc/Main.java\t42\ttrue\t2026-03-25\n'
        )
        comments = parse_toon_table(toon_output, 'comments')
        self.assertEqual(len(comments), 1)
        self.assertNotIn('thread_id', comments[0])

    def test_missing_key_returns_empty_list(self):
        """Test that a missing key returns empty list."""
        toon_output = 'status: success\ntotal: 0\n'
        comments = parse_toon_table(toon_output, 'comments')
        self.assertEqual(comments, [])


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


class TestParseCommentsOutput(unittest.TestCase):
    """Test parse_comments_output — TOON parsing logic extracted from fetch_comments."""

    @classmethod
    def setUpClass(cls):
        """Import parse_comments_output from pr.py via sys.path."""
        # conftest already added scripts dirs to sys.path
        from pr import parse_comments_output  # type: ignore[import-not-found]
        cls.parse = staticmethod(parse_comments_output)

    def test_parses_full_toon_output(self):
        """Test parsing a complete TOON output with multiple comments."""
        toon = (
            'status: success\n'
            'operation: pr_comments\n'
            'provider: github\n'
            'pr_number: 42\n'
            'total: 2\n'
            'unresolved: 1\n'
            'comments[2]{id,thread_id,author,body,path,line,resolved,created_at}:\n'
            '  PRRC_001\tPRRT_abc\talice\tFix this\tsrc/A.java\t10\ttrue\t2026-01-01\n'
            '  PRRC_002\tPRRT_def\tbob\tAdd test\tsrc/B.java\t20\tfalse\t2026-01-02\n'
        )
        result = self.parse(toon, 42)
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['pr_number'], 42)
        self.assertEqual(result['provider'], 'github')
        self.assertEqual(result['total_comments'], 2)
        self.assertEqual(result['unresolved_count'], 1)
        self.assertEqual(len(result['comments']), 2)
        self.assertEqual(result['comments'][0]['id'], 'PRRC_001')
        self.assertEqual(result['comments'][1]['body'], 'Add test')

    def test_parses_empty_comments(self):
        """Test parsing TOON with zero comments."""
        toon = (
            'status: success\n'
            'provider: gitlab\n'
            'total: 0\n'
            'unresolved: 0\n'
            'comments[0]{id,author,body,path,line,resolved,created_at}:\n'
        )
        result = self.parse(toon, 99)
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['pr_number'], 99)
        self.assertEqual(result['total_comments'], 0)
        self.assertEqual(result['unresolved_count'], 0)
        self.assertEqual(len(result['comments']), 0)

    def test_dash_null_markers(self):
        """Test that dash values in path/line are parsed as None."""
        toon = (
            'status: success\n'
            'provider: github\n'
            'total: 1\n'
            'unresolved: 1\n'
            'comments[1]{id,author,body,path,line,resolved,created_at}:\n'
            '  PRRC_003\treviewer\tGeneral note\t-\t-\tfalse\t2026-01-01\n'
        )
        result = self.parse(toon, 10)
        self.assertEqual(len(result['comments']), 1)
        self.assertIsNone(result['comments'][0]['path'])
        self.assertIsNone(result['comments'][0]['line'])

    def test_defaults_provider_when_missing(self):
        """Test fallback to 'unknown' when provider is not in TOON output."""
        toon = (
            'status: success\n'
            'total: 0\n'
            'comments[0]{id,author,body,path,line,resolved,created_at}:\n'
        )
        result = self.parse(toon, 1)
        self.assertEqual(result['provider'], 'unknown')

    def test_computes_unresolved_from_comments_when_missing(self):
        """Test that unresolved count is computed from comment data when not in TOON header."""
        toon = (
            'status: success\n'
            'provider: github\n'
            'comments[2]{id,author,body,path,line,resolved,created_at}:\n'
            '  C1\ta\tComment 1\tsrc/A.java\t1\ttrue\t2026-01-01\n'
            '  C2\tb\tComment 2\tsrc/B.java\t2\tfalse\t2026-01-02\n'
        )
        result = self.parse(toon, 5)
        self.assertEqual(result['total_comments'], 2)
        self.assertEqual(result['unresolved_count'], 1)


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
