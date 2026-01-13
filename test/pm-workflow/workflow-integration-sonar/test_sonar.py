"""Tests for sonar.py - consolidated Sonar workflow script."""

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path


def get_script_path():
    """Get the path to sonar.py."""
    return Path(__file__).parent.parent.parent.parent / \
           "marketplace/bundles/pm-workflow/skills/workflow-integration-sonar/scripts/sonar.py"


def run_script(args: list) -> tuple:
    """Run sonar.py with args and return (stdout, stderr, returncode)."""
    script_path = get_script_path()
    result = subprocess.run(
        [sys.executable, str(script_path)] + args,
        capture_output=True,
        text=True
    )
    return result.stdout, result.stderr, result.returncode


class TestSonarFetch(unittest.TestCase):
    """Test sonar.py fetch subcommand."""

    def test_fetch_with_project_only(self):
        """Test fetch with just project key."""
        stdout, stderr, code = run_script([
            "fetch", "--project", "my-project"
        ])
        self.assertEqual(code, 0)
        result = json.loads(stdout)
        self.assertEqual(result["project_key"], "my-project")
        self.assertIsNone(result["pull_request_id"])
        self.assertEqual(result["status"], "instruction_generated")

    def test_fetch_with_pr(self):
        """Test fetch with project and PR."""
        stdout, stderr, code = run_script([
            "fetch", "--project", "my-project", "--pr", "123"
        ])
        self.assertEqual(code, 0)
        result = json.loads(stdout)
        self.assertEqual(result["project_key"], "my-project")
        self.assertEqual(result["pull_request_id"], "123")
        self.assertIn("pullRequestId", result["mcp_instruction"]["parameters"])

    def test_fetch_with_severities(self):
        """Test fetch with severity filter."""
        stdout, stderr, code = run_script([
            "fetch", "--project", "my-project", "--severities", "BLOCKER,CRITICAL"
        ])
        self.assertEqual(code, 0)
        result = json.loads(stdout)
        mcp_params = result["mcp_instruction"]["parameters"]
        self.assertEqual(mcp_params["severities"], "BLOCKER,CRITICAL")

    def test_fetch_missing_project(self):
        """Test fetch without required project arg."""
        stdout, stderr, code = run_script(["fetch"])
        self.assertNotEqual(code, 0)
        self.assertIn("--project", stderr)

    def test_fetch_mcp_instruction_structure(self):
        """Test that MCP instruction is properly formatted."""
        stdout, stderr, code = run_script([
            "fetch", "--project", "test-proj", "--pr", "456"
        ])
        self.assertEqual(code, 0)
        result = json.loads(stdout)
        mcp = result["mcp_instruction"]
        self.assertEqual(mcp["tool"], "mcp__sonarqube__search_sonar_issues_in_projects")
        self.assertIn("test-proj", mcp["parameters"]["projects"])


class TestSonarTriage(unittest.TestCase):
    """Test sonar.py triage subcommand."""

    def test_triage_bug_major_fix(self):
        """Test triage recommends fix for MAJOR BUG."""
        issue = {
            "key": "ISSUE-1",
            "type": "BUG",
            "severity": "MAJOR",
            "file": "src/Example.java",
            "line": 42,
            "rule": "java:S1234",
            "message": "Test message"
        }
        stdout, stderr, code = run_script([
            "triage", "--issue", json.dumps(issue)
        ])
        self.assertEqual(code, 0)
        result = json.loads(stdout)
        self.assertEqual(result["action"], "fix")
        self.assertEqual(result["priority"], "medium")
        self.assertEqual(result["status"], "success")

    def test_triage_vulnerability_boost(self):
        """Test triage boosts priority for VULNERABILITY."""
        issue = {
            "key": "ISSUE-2",
            "type": "VULNERABILITY",
            "severity": "MAJOR",
            "file": "src/Security.java",
            "line": 10,
            "rule": "java:S3649",
            "message": "SQL injection"
        }
        stdout, stderr, code = run_script([
            "triage", "--issue", json.dumps(issue)
        ])
        self.assertEqual(code, 0)
        result = json.loads(stdout)
        self.assertEqual(result["action"], "fix")
        self.assertEqual(result["priority"], "high")  # Boosted from medium

    def test_triage_suppressable_rule(self):
        """Test triage recommends suppress for suppressable rules."""
        issue = {
            "key": "ISSUE-3",
            "type": "CODE_SMELL",
            "severity": "MINOR",
            "file": "src/Example.java",
            "line": 5,
            "rule": "java:S1135",  # TODO comment
            "message": "Complete TODO"
        }
        stdout, stderr, code = run_script([
            "triage", "--issue", json.dumps(issue)
        ])
        self.assertEqual(code, 0)
        result = json.loads(stdout)
        self.assertEqual(result["action"], "suppress")
        self.assertIn("NOSONAR", result["suppression_string"])

    def test_triage_test_file_suppression(self):
        """Test triage handles test file patterns."""
        issue = {
            "key": "ISSUE-4",
            "type": "CODE_SMELL",
            "severity": "MINOR",
            "file": "src/test/java/ExampleTest.java",
            "line": 20,
            "rule": "java:S106",  # System.out
            "message": "Use logger"
        }
        stdout, stderr, code = run_script([
            "triage", "--issue", json.dumps(issue)
        ])
        self.assertEqual(code, 0)
        result = json.loads(stdout)
        self.assertEqual(result["action"], "suppress")
        # Reason comes from SUPPRESSABLE_RULES constant
        self.assertIn("acceptable", result["reason"].lower())

    def test_triage_invalid_json(self):
        """Test triage handles invalid JSON."""
        stdout, stderr, code = run_script([
            "triage", "--issue", "not-valid-json"
        ])
        self.assertEqual(code, 1)
        result = json.loads(stdout)
        self.assertEqual(result["status"], "failure")
        self.assertIn("Invalid JSON", result["error"])

    def test_triage_missing_issue(self):
        """Test triage without required issue arg."""
        stdout, stderr, code = run_script(["triage"])
        self.assertNotEqual(code, 0)
        self.assertIn("--issue", stderr)

    def test_triage_java_command_suggestion(self):
        """Test triage suggests Java command for .java files."""
        issue = {
            "key": "ISSUE-5",
            "type": "BUG",
            "severity": "CRITICAL",
            "file": "src/main/java/Service.java",
            "line": 100,
            "rule": "java:S2095",
            "message": "Close resource"
        }
        stdout, stderr, code = run_script([
            "triage", "--issue", json.dumps(issue)
        ])
        self.assertEqual(code, 0)
        result = json.loads(stdout)
        self.assertEqual(result["action"], "fix")
        self.assertEqual(result["command_to_use"], "/java-implement-code")


class TestSonarMain(unittest.TestCase):
    """Test sonar.py main entry point."""

    def test_no_subcommand(self):
        """Test error when no subcommand provided."""
        stdout, stderr, code = run_script([])
        self.assertNotEqual(code, 0)

    def test_help(self):
        """Test help output."""
        stdout, stderr, code = run_script(["--help"])
        # argparse exits with 0 for help
        self.assertEqual(code, 0)
        self.assertIn("fetch", stdout)
        self.assertIn("triage", stdout)


if __name__ == "__main__":
    unittest.main()
