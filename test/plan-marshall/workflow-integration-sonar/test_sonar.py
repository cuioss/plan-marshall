"""Tests for sonar.py - consolidated Sonar workflow script."""

import json
import sys
import unittest
from pathlib import Path

# Import shared infrastructure
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from toon_parser import parse_toon  # type: ignore[import-not-found]  # noqa: E402

from conftest import get_script_path, run_script  # noqa: E402

# Script under test
SCRIPT_PATH = get_script_path('plan-marshall', 'workflow-integration-sonar', 'sonar.py')


def run_sonar_script(args: list) -> tuple:
    """Run sonar.py with args and return (stdout, stderr, returncode)."""
    result = run_script(SCRIPT_PATH, *args)
    return result.stdout, result.stderr, result.returncode


class TestSonarFetch(unittest.TestCase):
    """Test sonar.py fetch subcommand."""

    def test_fetch_with_project_only(self):
        """Test fetch with just project key."""
        stdout, stderr, code = run_sonar_script(['fetch', '--project', 'my-project'])
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
        self.assertEqual(result['project_key'], 'my-project')
        self.assertIsNone(result['pull_request_id'])
        self.assertEqual(result['status'], 'success')

    def test_fetch_with_pr(self):
        """Test fetch with project and PR."""
        stdout, stderr, code = run_sonar_script(['fetch', '--project', 'my-project', '--pr', '123'])
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
        self.assertEqual(result['project_key'], 'my-project')
        self.assertEqual(str(result['pull_request_id']), '123')
        self.assertIn('pullRequestId', result['mcp_instruction']['parameters'])

    def test_fetch_with_severities(self):
        """Test fetch with severity filter."""
        stdout, stderr, code = run_sonar_script(['fetch', '--project', 'my-project', '--severities', 'BLOCKER,CRITICAL'])
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
        mcp_params = result['mcp_instruction']['parameters']
        self.assertEqual(mcp_params['severities'], 'BLOCKER,CRITICAL')

    def test_fetch_missing_project(self):
        """Test fetch without required project arg."""
        stdout, stderr, code = run_sonar_script(['fetch'])
        self.assertNotEqual(code, 0)
        self.assertIn('--project', stderr)

    def test_fetch_mcp_instruction_structure(self):
        """Test that MCP instruction is properly formatted."""
        stdout, stderr, code = run_sonar_script(['fetch', '--project', 'test-proj', '--pr', '456'])
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
        mcp = result['mcp_instruction']
        self.assertEqual(mcp['tool'], 'mcp__sonarqube__search_sonar_issues_in_projects')
        self.assertIn('test-proj', mcp['parameters']['projects'])


class TestSonarTriage(unittest.TestCase):
    """Test sonar.py triage subcommand."""

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
        stdout, stderr, code = run_sonar_script(['triage', '--issue', json.dumps(issue)])
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
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
        stdout, stderr, code = run_sonar_script(['triage', '--issue', json.dumps(issue)])
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
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
        stdout, stderr, code = run_sonar_script(['triage', '--issue', json.dumps(issue)])
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
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
        stdout, stderr, code = run_sonar_script(['triage', '--issue', json.dumps(issue)])
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
        self.assertEqual(result['action'], 'suppress')
        # Reason comes from SUPPRESSABLE_RULES constant
        self.assertIn('acceptable', result['reason'].lower())

    def test_triage_invalid_json(self):
        """Test triage handles invalid JSON."""
        stdout, stderr, code = run_sonar_script(['triage', '--issue', 'not-valid-json'])
        self.assertEqual(code, 1)
        result = parse_toon(stdout)
        self.assertEqual(result['status'], 'failure')
        self.assertIn('Invalid JSON', result['error'])

    def test_triage_missing_issue(self):
        """Test triage without required issue arg."""
        stdout, stderr, code = run_sonar_script(['triage'])
        self.assertNotEqual(code, 0)
        self.assertIn('--issue', stderr)

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
        stdout, stderr, code = run_sonar_script(['triage', '--issue', json.dumps(issue)])
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
        self.assertEqual(result['action'], 'fix')
        self.assertIsNone(result.get('command_to_use'))

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
        stdout, _, code = run_sonar_script(['triage', '--issue', json.dumps(issue)])
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
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
        stdout, _, code = run_sonar_script(['triage', '--issue', json.dumps(issue)])
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
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
        stdout, _, code = run_sonar_script(['triage', '--issue', json.dumps(issue)])
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
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
        stdout, _, code = run_sonar_script(['triage', '--issue', json.dumps(issue)])
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
        self.assertEqual(result['action'], 'fix')
        self.assertEqual(result['priority'], 'high')


class TestSonarTriageBatch(unittest.TestCase):
    """Test sonar.py triage-batch subcommand."""

    def test_triage_batch_multiple_issues(self):
        """Test batch triage processes multiple issues at once."""
        issues = [
            {'key': 'B1', 'type': 'BUG', 'severity': 'MAJOR', 'file': 'src/A.java', 'line': 1, 'rule': 'java:S1234', 'message': 'Bug'},
            {'key': 'B2', 'type': 'CODE_SMELL', 'severity': 'MINOR', 'file': 'src/B.java', 'line': 5, 'rule': 'java:S1135', 'message': 'TODO'},
            {'key': 'B3', 'type': 'VULNERABILITY', 'severity': 'CRITICAL', 'file': 'src/C.java', 'line': 10, 'rule': 'java:S3649', 'message': 'SQL injection'},
        ]
        stdout, _, code = run_sonar_script(['triage-batch', '--issues', json.dumps(issues)])
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['summary']['total'], 3)
        self.assertEqual(result['summary']['fix'], 2)
        self.assertEqual(result['summary']['suppress'], 1)

    def test_triage_batch_empty_list(self):
        """Test batch triage with empty list."""
        stdout, _, code = run_sonar_script(['triage-batch', '--issues', '[]'])
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
        self.assertEqual(result['summary']['total'], 0)

    def test_triage_batch_invalid_json(self):
        """Test batch triage with invalid JSON."""
        stdout, _, code = run_sonar_script(['triage-batch', '--issues', 'not-json'])
        self.assertEqual(code, 1)
        result = parse_toon(stdout)
        self.assertEqual(result['status'], 'failure')

    def test_triage_batch_not_array(self):
        """Test batch triage rejects non-array input."""
        stdout, _, code = run_sonar_script(['triage-batch', '--issues', '{"key": "I1"}'])
        self.assertEqual(code, 1)
        result = parse_toon(stdout)
        self.assertEqual(result['status'], 'failure')
        self.assertIn('array', result['error'])


class TestSonarMain(unittest.TestCase):
    """Test sonar.py main entry point."""

    def test_no_subcommand(self):
        """Test error when no subcommand provided."""
        stdout, stderr, code = run_sonar_script([])
        self.assertNotEqual(code, 0)

    def test_help(self):
        """Test help output."""
        stdout, stderr, code = run_sonar_script(['--help'])
        # argparse exits with 0 for help
        self.assertEqual(code, 0)
        self.assertIn('fetch', stdout)
        self.assertIn('triage', stdout)
        self.assertIn('triage-batch', stdout)


if __name__ == '__main__':
    unittest.main()
