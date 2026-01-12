#!/usr/bin/env python3
"""
Tests for the marketplace-sync.py script.

Tests subcommands:
- generate-wildcards: Generate permission wildcards from marketplace inventory
- ensure-executor: Ensure the executor permission exists
- cleanup-scripts: Remove redundant individual script permissions
- migrate-executor: Full migration to executor-only permission pattern
"""

import json
import sys
from pathlib import Path

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import (
    ScriptTestCase, TestRunner, run_script,
    MARKETPLACE_ROOT
)


# Script path to marketplace-sync.py
SCRIPT_PATH = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'marketplace-sync' / 'scripts' / 'marketplace-sync.py'


# =============================================================================
# Tests for generate-wildcards subcommand
# =============================================================================

class TestGenerateWildcards(ScriptTestCase):
    """Test marketplace-sync.py generate-wildcards subcommand."""

    bundle = 'plan-marshall'
    skill = 'marketplace-sync'
    script = 'marketplace-sync.py'

    def test_generates_skill_wildcards(self):
        """Should generate Skill() wildcards from inventory."""
        inventory = {
            "bundles": [
                {
                    "name": "builder",
                    "skills": [{"name": "builder-gradle-rules"}, {"name": "builder-maven-rules"}],
                    "commands": []
                }
            ]
        }

        result = run_script(
            SCRIPT_PATH,
            'generate-wildcards',
            input_data=json.dumps(inventory)
        )
        self.assert_success(result)
        data = result.json()

        self.assertIn('permissions', data)
        self.assertIn('skill_wildcards', data['permissions'])
        self.assertIn('Skill(builder:*)', data['permissions']['skill_wildcards'])

    def test_generates_command_wildcards(self):
        """Should generate SlashCommand() wildcards from inventory."""
        inventory = {
            "bundles": [
                {
                    "name": "pm-workflow",
                    "skills": [],
                    "commands": [{"name": "plan-manage"}, {"name": "task-implement"}]
                }
            ]
        }

        result = run_script(
            SCRIPT_PATH,
            'generate-wildcards',
            input_data=json.dumps(inventory)
        )
        self.assert_success(result)
        data = result.json()

        self.assertIn('permissions', data)
        self.assertIn('command_bundle_wildcards', data['permissions'])
        self.assertIn('SlashCommand(/pm-workflow:*)', data['permissions']['command_bundle_wildcards'])

    def test_includes_statistics(self):
        """Should include statistics in output."""
        inventory = {
            "bundles": [
                {
                    "name": "test-bundle",
                    "skills": [{"name": "skill1"}],
                    "commands": [{"name": "cmd1"}]
                }
            ]
        }

        result = run_script(
            SCRIPT_PATH,
            'generate-wildcards',
            input_data=json.dumps(inventory)
        )
        self.assert_success(result)
        data = result.json()

        self.assertIn('statistics', data)
        self.assertIn('bundles_scanned', data['statistics'])


# =============================================================================
# Tests for executor pattern subcommands
# =============================================================================

class TestExecutorPattern(ScriptTestCase):
    """Test marketplace-sync.py executor pattern subcommands."""

    bundle = 'plan-marshall'
    skill = 'marketplace-sync'
    script = 'marketplace-sync.py'

    def test_ensure_executor_adds_permission(self):
        """Should add executor permission when missing."""
        claude_dir = self.temp_dir / '.claude'
        claude_dir.mkdir()
        settings_file = claude_dir / 'settings.json'
        settings_file.write_text(json.dumps({
            "permissions": {
                "allow": ["Bash(git:*)"],
                "deny": [],
                "ask": []
            }
        }))

        result = run_script(
            SCRIPT_PATH,
            'ensure-executor',
            '--target', 'project',
            cwd=self.temp_dir
        )
        self.assert_success(result)
        data = result.json()

        self.assertTrue(data.get('success'))
        self.assertEqual(data.get('action'), 'added')

        settings = json.loads(settings_file.read_text())
        self.assertIn('Bash(python3 .plan/execute-script.py *)', settings['permissions']['allow'])

    def test_ensure_executor_already_exists(self):
        """Should report when executor permission already exists."""
        claude_dir = self.temp_dir / '.claude'
        claude_dir.mkdir()
        settings_file = claude_dir / 'settings.json'
        settings_file.write_text(json.dumps({
            "permissions": {
                "allow": ["Bash(python3 .plan/execute-script.py *)"],
                "deny": [],
                "ask": []
            }
        }))

        result = run_script(
            SCRIPT_PATH,
            'ensure-executor',
            '--target', 'project',
            cwd=self.temp_dir
        )
        self.assert_success(result)
        data = result.json()

        self.assertTrue(data.get('success'))
        self.assertEqual(data.get('action'), 'already_exists')

    def test_cleanup_scripts_removes_individual_permissions(self):
        """Should remove individual script permissions."""
        claude_dir = self.temp_dir / '.claude'
        claude_dir.mkdir()
        settings_file = claude_dir / 'settings.json'
        settings_file.write_text(json.dumps({
            "permissions": {
                "allow": [
                    "Bash(git:*)",
                    "Bash(python3 /path/to/marketplace/bundles/test/skills/foo/scripts/*:*)",
                    "Bash(python3 /path/to/marketplace/bundles/test/skills/bar/scripts/*:*)"
                ],
                "deny": [],
                "ask": []
            }
        }))

        result = run_script(
            SCRIPT_PATH,
            'cleanup-scripts',
            '--target', 'project',
            cwd=self.temp_dir
        )
        self.assert_success(result)
        data = result.json()

        self.assertTrue(data.get('success'))
        self.assertEqual(data.get('individual_count'), 2)

        settings = json.loads(settings_file.read_text())
        self.assertEqual(len(settings['permissions']['allow']), 1)
        self.assertIn('Bash(git:*)', settings['permissions']['allow'])

    def test_migrate_executor_full_migration(self):
        """Should add executor and remove individual permissions."""
        claude_dir = self.temp_dir / '.claude'
        claude_dir.mkdir()
        settings_file = claude_dir / 'settings.json'
        settings_file.write_text(json.dumps({
            "permissions": {
                "allow": [
                    "Bash(git:*)",
                    "Bash(python3 /path/to/marketplace/bundles/test/skills/foo/scripts/*:*)"
                ],
                "deny": [],
                "ask": []
            }
        }))

        result = run_script(
            SCRIPT_PATH,
            'migrate-executor',
            '--target', 'project',
            cwd=self.temp_dir
        )
        self.assert_success(result)
        data = result.json()

        self.assertTrue(data.get('success'))
        self.assertIn('executor', data)
        self.assertIn('cleanup', data)

        settings = json.loads(settings_file.read_text())
        self.assertIn('Bash(python3 .plan/execute-script.py *)', settings['permissions']['allow'])
        self.assertIn('Bash(git:*)', settings['permissions']['allow'])
        # Individual script permission should be removed
        self.assertEqual(len(settings['permissions']['allow']), 2)


# =============================================================================
# Simple function-based tests for quick validation
# =============================================================================

def test_script_exists():
    """Verify the script exists."""
    assert SCRIPT_PATH.exists(), f"Script not found: {SCRIPT_PATH}"


def test_help_works():
    """Script should respond to --help."""
    result = run_script(SCRIPT_PATH, '--help')
    assert result.returncode == 0


def test_generate_wildcards_help():
    """generate-wildcards subcommand should have help."""
    result = run_script(SCRIPT_PATH, 'generate-wildcards', '--help')
    assert result.returncode == 0


def test_ensure_executor_help():
    """ensure-executor subcommand should have help."""
    result = run_script(SCRIPT_PATH, 'ensure-executor', '--help')
    assert result.returncode == 0


def test_cleanup_scripts_help():
    """cleanup-scripts subcommand should have help."""
    result = run_script(SCRIPT_PATH, 'cleanup-scripts', '--help')
    assert result.returncode == 0


def test_migrate_executor_help():
    """migrate-executor subcommand should have help."""
    result = run_script(SCRIPT_PATH, 'migrate-executor', '--help')
    assert result.returncode == 0


# =============================================================================
# Main
# =============================================================================

if __name__ == '__main__':
    import unittest

    # Check if script exists first
    if not SCRIPT_PATH.exists():
        print(f"ERROR: Script not found: {SCRIPT_PATH}")
        sys.exit(1)

    # Run unittest-based tests
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestGenerateWildcards))
    suite.addTests(loader.loadTestsFromTestCase(TestExecutorPattern))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Also run simple function tests
    print("\n" + "=" * 50)
    print("Running simple function tests...")
    print("=" * 50)

    simple_tests = [
        test_script_exists,
        test_help_works,
        test_generate_wildcards_help,
        test_ensure_executor_help,
        test_cleanup_scripts_help,
        test_migrate_executor_help,
    ]

    simple_runner = TestRunner()
    simple_runner.add_tests(simple_tests)
    simple_result = simple_runner.run()

    # Exit with combined result
    sys.exit(0 if result.wasSuccessful() and simple_result == 0 else 1)
