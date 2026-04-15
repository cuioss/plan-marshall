"""Tests for sonar.py - consolidated Sonar workflow script.

Tier 2 (direct import) tests with 2 subprocess tests for CLI plumbing.
"""

import json
import unittest

from conftest import get_script_path, run_script

# Import toon_parser - conftest sets up PYTHONPATH

# Script under test (for subprocess CLI plumbing tests)
SCRIPT_PATH = get_script_path('plan-marshall', 'workflow-integration-sonar', 'sonar.py')

# Tier 2 direct imports — conftest sets up PYTHONPATH for cross-skill imports
from sonar import (  # type: ignore[import-not-found]  # noqa: E402
    _FIX_SUGGESTIONS,
    _TEST_ACCEPTABLE_RULES,
    SUPPRESSABLE_RULES,
    triage_issue,
)
from triage_helpers import cmd_triage_batch_handler  # type: ignore[import-not-found]  # noqa: E402


class TestSonarTriage(unittest.TestCase):
    """Test sonar.py triage subcommand via direct import."""

    def test_triage_bug_major_fix(self):
        """Test triage recommends fix for MAJOR BUG."""
        issue = {
            'key': 'ISSUE-1',
            'type': 'BUG',
            'severity': 'MAJOR',
            'file': 'src/Example.java',
            'line': 42,
            'rule': 'java:S1234',
            'message': 'Test message',
        }
        result = triage_issue(issue)
        self.assertEqual(result['action'], 'fix')
        self.assertEqual(result['priority'], 'medium')
        self.assertEqual(result['status'], 'success')

    def test_triage_vulnerability_boost(self):
        """Test triage boosts priority for VULNERABILITY."""
        issue = {
            'key': 'ISSUE-2',
            'type': 'VULNERABILITY',
            'severity': 'MAJOR',
            'file': 'src/Security.java',
            'line': 10,
            'rule': 'java:S3649',
            'message': 'SQL injection',
        }
        result = triage_issue(issue)
        self.assertEqual(result['action'], 'fix')
        self.assertEqual(result['priority'], 'high')  # Boosted from medium

    def test_triage_suppressable_rule(self):
        """Test triage recommends suppress for suppressable rules."""
        issue = {
            'key': 'ISSUE-3',
            'type': 'CODE_SMELL',
            'severity': 'MINOR',
            'file': 'src/Example.java',
            'line': 5,
            'rule': 'java:S1135',  # TODO comment
            'message': 'Complete TODO',
        }
        result = triage_issue(issue)
        self.assertEqual(result['action'], 'suppress')
        self.assertIn('NOSONAR', result['suppression_string'])

    def test_triage_test_file_suppression(self):
        """Test triage handles test file patterns."""
        issue = {
            'key': 'ISSUE-4',
            'type': 'CODE_SMELL',
            'severity': 'MINOR',
            'file': 'src/test/java/ExampleTest.java',
            'line': 20,
            'rule': 'java:S106',  # System.out
            'message': 'Use logger',
        }
        result = triage_issue(issue)
        self.assertEqual(result['action'], 'suppress')
        # Reason comes from SUPPRESSABLE_RULES constant
        self.assertIn('acceptable', result['reason'].lower())

    def test_triage_invalid_json(self):
        """Test triage handles invalid JSON via cmd_triage_single."""
        from triage_helpers import cmd_triage_single  # type: ignore[import-not-found]

        result = cmd_triage_single('not-valid-json', triage_issue)
        self.assertEqual(result['status'], 'error')
        self.assertIn('Invalid JSON', result['error'])

    def test_triage_java_command_suggestion(self):
        """Test triage suggests Java command for .java files."""
        issue = {
            'key': 'ISSUE-5',
            'type': 'BUG',
            'severity': 'CRITICAL',
            'file': 'src/main/java/Service.java',
            'line': 100,
            'rule': 'java:S2095',
            'message': 'Close resource',
        }
        result = triage_issue(issue)
        self.assertEqual(result['action'], 'fix')
        self.assertNotIn('command_to_use', result)

    def test_triage_python_suppression_uses_hash_comment(self):
        """Test triage generates Python-style suppression comment for .py files."""
        issue = {
            'key': 'ISSUE-PY1',
            'type': 'CODE_SMELL',
            'severity': 'MINOR',
            'file': 'src/utils/helper.py',
            'line': 10,
            'rule': 'python:S1135',
            'message': 'Complete TODO',
        }
        result = triage_issue(issue)
        self.assertEqual(result['action'], 'suppress')
        self.assertTrue(result['suppression_string'].startswith('# NOSONAR'))

    def test_triage_java_suppression_uses_slash_comment(self):
        """Test triage generates Java-style suppression comment for .java files."""
        issue = {
            'key': 'ISSUE-J1',
            'type': 'CODE_SMELL',
            'severity': 'MINOR',
            'file': 'src/main/java/Example.java',
            'line': 5,
            'rule': 'java:S1135',
            'message': 'Complete TODO',
        }
        result = triage_issue(issue)
        self.assertEqual(result['action'], 'suppress')
        self.assertTrue(result['suppression_string'].startswith('// NOSONAR'))

    def test_triage_vulnerability_always_fix(self):
        """Test triage always fixes VULNERABILITY regardless of suppressable rule."""
        issue = {
            'key': 'ISSUE-V1',
            'type': 'VULNERABILITY',
            'severity': 'MINOR',
            'file': 'src/main/java/Example.java',
            'line': 10,
            'rule': 'java:S1135',  # Normally suppressable
            'message': 'Vulnerability detected',
        }
        result = triage_issue(issue)
        self.assertEqual(result['action'], 'fix')
        self.assertIn('VULNERABILITY', result['reason'])

    def test_triage_security_hotspot_always_fix(self):
        """Test triage always fixes SECURITY_HOTSPOT."""
        issue = {
            'key': 'ISSUE-SH1',
            'type': 'SECURITY_HOTSPOT',
            'severity': 'MAJOR',
            'file': 'src/main/java/Config.java',
            'line': 30,
            'rule': 'java:S4790',
            'message': 'Weak hash algorithm',
        }
        result = triage_issue(issue)
        self.assertEqual(result['action'], 'fix')
        self.assertEqual(result['priority'], 'high')


class TestSonarTriageBatch(unittest.TestCase):
    """Test sonar.py triage-batch via direct import."""

    def test_triage_batch_multiple_issues(self):
        """Test batch triage processes multiple issues at once."""
        issues = [
            {
                'key': 'B1',
                'type': 'BUG',
                'severity': 'MAJOR',
                'file': 'src/A.java',
                'line': 1,
                'rule': 'java:S1234',
                'message': 'Bug',
            },
            {
                'key': 'B2',
                'type': 'CODE_SMELL',
                'severity': 'MINOR',
                'file': 'src/B.java',
                'line': 5,
                'rule': 'java:S1135',
                'message': 'TODO',
            },
            {
                'key': 'B3',
                'type': 'VULNERABILITY',
                'severity': 'CRITICAL',
                'file': 'src/C.java',
                'line': 10,
                'rule': 'java:S3649',
                'message': 'SQL injection',
            },
        ]
        result = cmd_triage_batch_handler(json.dumps(issues), triage_issue, ['fix', 'suppress'])
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['summary']['total'], 3)
        self.assertEqual(result['summary']['fix'], 2)
        self.assertEqual(result['summary']['suppress'], 1)

    def test_triage_batch_empty_list(self):
        """Test batch triage with empty list."""
        result = cmd_triage_batch_handler('[]', triage_issue, ['fix', 'suppress'])
        self.assertEqual(result['summary']['total'], 0)

    def test_triage_batch_invalid_json(self):
        """Test batch triage with invalid JSON."""
        result = cmd_triage_batch_handler('not-json', triage_issue, ['fix', 'suppress'])
        self.assertEqual(result['status'], 'error')

    def test_triage_batch_not_array(self):
        """Test batch triage rejects non-array input."""
        result = cmd_triage_batch_handler('{"key": "I1"}', triage_issue, ['fix', 'suppress'])
        self.assertEqual(result['status'], 'error')
        self.assertIn('array', result['error'])


class TestSonarRulesConfig(unittest.TestCase):
    """Test that sonar rules are loaded from sonar-rules.json config."""

    def test_suppressable_rules_loaded(self):
        """Test that suppressable rules are loaded from config."""
        self.assertIn('java:S1135', SUPPRESSABLE_RULES)
        self.assertIn('python:S1481', SUPPRESSABLE_RULES)
        self.assertIn('javascript:S1135', SUPPRESSABLE_RULES)

    def test_fix_suggestions_loaded(self):
        """Test that fix suggestions are loaded from config."""
        self.assertIn('java:S2095', _FIX_SUGGESTIONS)
        self.assertIn('python:S5131', _FIX_SUGGESTIONS)
        self.assertIn('javascript:S3649', _FIX_SUGGESTIONS)

    def test_test_acceptable_rules_loaded(self):
        """Test that test-acceptable rules are loaded from config."""
        self.assertIn('java:S106', _TEST_ACCEPTABLE_RULES)
        # java:S2699 (missing assertions) removed — tests without assertions are a real quality gap
        self.assertNotIn('java:S2699', _TEST_ACCEPTABLE_RULES)
        self.assertIn('python:S106', _TEST_ACCEPTABLE_RULES)


class TestToonContract(unittest.TestCase):
    """Verify output matches the contract documented in SKILL.md."""

    def test_triage_output_contract(self):
        """Verify triage output has all documented fields."""
        issue = {
            'key': 'CONTRACT-1',
            'type': 'BUG',
            'severity': 'MAJOR',
            'file': 'src/Example.java',
            'line': 42,
            'rule': 'java:S1234',
            'message': 'Test message',
        }
        result = triage_issue(issue)
        required_fields = {
            'issue_key',
            'action',
            'reason',
            'priority',
            'suggested_implementation',
            'suppression_string',
            'status',
        }
        missing = required_fields - set(result.keys())
        self.assertEqual(missing, set(), f'Missing contract fields: {missing}')

    def test_triage_suppress_output_contract(self):
        """Verify suppression output includes suppression_string."""
        issue = {
            'key': 'CONTRACT-2',
            'type': 'CODE_SMELL',
            'severity': 'MINOR',
            'file': 'src/Example.java',
            'line': 5,
            'rule': 'java:S1135',
            'message': 'Complete TODO',
        }
        result = triage_issue(issue)
        self.assertEqual(result['action'], 'suppress')
        self.assertIsNotNone(result['suppression_string'])
        self.assertIn('NOSONAR', result['suppression_string'])

    def test_triage_batch_output_contract(self):
        """Verify triage-batch output has all documented fields."""
        issues = [
            {
                'key': 'B1',
                'type': 'BUG',
                'severity': 'MAJOR',
                'file': 'src/A.java',
                'line': 1,
                'rule': 'java:S1234',
                'message': 'Bug',
            },
        ]
        result = cmd_triage_batch_handler(json.dumps(issues), triage_issue, ['fix', 'suppress'])
        required_fields = {'results', 'summary', 'status'}
        missing = required_fields - set(result.keys())
        self.assertEqual(missing, set(), f'Missing contract fields: {missing}')
        # Summary sub-structure
        summary = result['summary']
        for field in ('total', 'fix', 'suppress'):
            self.assertIn(field, summary, f'Missing summary.{field}')


class TestSonarConfigLoading(unittest.TestCase):
    """Test sonar.py config file loading edge cases."""

    def test_triage_works_with_minimal_issue_fields(self):
        """Test triage handles issue with only partial fields (defaults applied)."""
        issue = {'key': 'MINIMAL-1'}
        result = triage_issue(issue)
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['action'], 'fix')
        self.assertEqual(result['issue_key'], 'MINIMAL-1')

    def test_triage_empty_issue_object(self):
        """Test triage handles completely empty issue dict."""
        result = triage_issue({})
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['issue_key'], 'unknown')


# =============================================================================
# Subprocess (Tier 3) tests — CLI plumbing only
# =============================================================================


def run_sonar_script(args: list) -> tuple:
    """Run sonar.py with args and return (stdout, stderr, returncode)."""
    result = run_script(SCRIPT_PATH, *args)
    return result.stdout, result.stderr, result.returncode


class TestSonarMain(unittest.TestCase):
    """Test sonar.py main entry point (CLI plumbing)."""

    def test_no_subcommand(self):
        """Test error when no subcommand provided."""
        stdout, stderr, code = run_sonar_script([])
        self.assertNotEqual(code, 0)

    def test_help(self):
        """Test help output."""
        stdout, stderr, code = run_sonar_script(['--help'])
        # argparse exits with 0 for help
        self.assertEqual(code, 0)
        self.assertIn('triage', stdout)
        self.assertIn('triage-batch', stdout)

    def test_triage_missing_issue(self):
        """Test triage without required issue arg."""
        stdout, stderr, code = run_sonar_script(['triage'])
        self.assertNotEqual(code, 0)
        self.assertIn('--issue', stderr)


class TestSonarProjectDirNoop(unittest.TestCase):
    """Verify sonar.py accepts --project-dir as a top-level no-op.

    Sonar triage is pure in-memory so the cwd has no functional effect — the
    flag is accepted for API uniformity with github/gitlab scripts and must
    not be rejected by argparse.
    """

    def test_project_dir_accepted_before_subcommand(self):
        """--project-dir PATH triage --issue ... must succeed."""
        issue = json.dumps(
            {
                'key': 'ISSUE-1',
                'type': 'BUG',
                'severity': 'MAJOR',
                'file': 'src/X.java',
                'line': 1,
                'rule': 'java:S1234',
                'message': 'm',
            }
        )
        stdout, stderr, code = run_sonar_script(
            ['--project-dir', '/tmp/sonar-wt', 'triage', '--issue', issue]
        )
        self.assertEqual(code, 0, f'stderr={stderr}')
        self.assertIn('status', stdout)

    def test_project_dir_equals_form(self):
        """--project-dir=PATH form is also accepted."""
        issue = json.dumps(
            {
                'key': 'ISSUE-2',
                'type': 'BUG',
                'severity': 'MINOR',
                'file': 'src/Y.java',
                'line': 2,
                'rule': 'java:S1111',
                'message': 'm',
            }
        )
        stdout, stderr, code = run_sonar_script(
            ['--project-dir=/tmp/sonar-wt2', 'triage', '--issue', issue]
        )
        self.assertEqual(code, 0, f'stderr={stderr}')

    def test_project_dir_not_visible_to_argparse(self):
        """The flag must be stripped before argparse runs — feeding an
        unknown value to --project-dir must not cause an 'unrecognized
        argument' error."""
        issue = json.dumps(
            {
                'key': 'ISSUE-3',
                'type': 'BUG',
                'severity': 'MAJOR',
                'file': 'src/Z.java',
                'line': 3,
                'rule': 'java:S1234',
                'message': 'm',
            }
        )
        stdout, stderr, code = run_sonar_script(
            ['--project-dir', '/nonexistent/path', 'triage', '--issue', issue]
        )
        self.assertEqual(code, 0, f'stderr={stderr}')
        self.assertNotIn('unrecognized arguments', stderr)


if __name__ == '__main__':
    unittest.main()
