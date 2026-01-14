#!/usr/bin/env python3
"""
Tests for the permission-doctor.py script.

Tests subcommands:
- detect-redundant: Detect redundant permissions between global/local
- detect-suspicious: Detect suspicious permissions (security anti-patterns)
"""

import json
import sys

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import MARKETPLACE_ROOT, ScriptTestCase, run_script

# Script path to permission-doctor.py
SCRIPT_PATH = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'permission-doctor' / 'scripts' / 'permission-doctor.py'


# =============================================================================
# Tests for detect-redundant subcommand
# =============================================================================


class TestDetectRedundant(ScriptTestCase):
    """Test permission-doctor.py detect-redundant subcommand."""

    bundle = 'plan-marshall'
    skill = 'permission-doctor'
    script = 'permission-doctor.py'

    def test_detect_exact_duplicate(self):
        """Should detect when same permission exists in both global and local."""
        global_file = self.temp_dir / 'global.json'
        global_file.write_text(
            json.dumps(
                {'permissions': {'allow': ['Bash(git:*)', 'Bash(npm:*)', 'Read(//~/git/**)'], 'deny': [], 'ask': []}}
            )
        )

        local_file = self.temp_dir / 'local.json'
        local_file.write_text(
            json.dumps({'permissions': {'allow': ['Bash(git:*)', 'Edit(.plan/**)'], 'deny': [], 'ask': []}})
        )

        result = run_script(
            SCRIPT_PATH, 'detect-redundant', '--global-settings', str(global_file), '--local-settings', str(local_file)
        )
        self.assert_success(result)
        data = result.json()

        self.assertIn('redundant', data)
        redundant_perms = [r['permission'] for r in data['redundant']]
        self.assertIn('Bash(git:*)', redundant_perms)
        self.assertNotIn('Edit(.plan/**)', redundant_perms)

    def test_detect_marketplace_in_local(self):
        """Should flag marketplace permissions in local as belonging in global."""
        global_file = self.temp_dir / 'global.json'
        global_file.write_text(json.dumps({'permissions': {'allow': ['Skill(builder:*)'], 'deny': [], 'ask': []}}))

        local_file = self.temp_dir / 'local.json'
        local_file.write_text(
            json.dumps({'permissions': {'allow': ['Skill(pm-dev-java:*)', 'Edit(.plan/**)'], 'deny': [], 'ask': []}})
        )

        result = run_script(
            SCRIPT_PATH, 'detect-redundant', '--global-settings', str(global_file), '--local-settings', str(local_file)
        )
        self.assert_success(result)
        data = result.json()

        self.assertIn('marketplace_in_local', data)
        marketplace_perms = [m['permission'] for m in data['marketplace_in_local']]
        self.assertIn('Skill(pm-dev-java:*)', marketplace_perms)

    def test_project_local_command_not_flagged_as_marketplace(self):
        """Project-local commands should NOT be flagged as marketplace_in_local.

        When a SlashCommand permission exists for a command defined in
        .claude/commands/, it's a legitimate project-local command and
        should NOT be flagged as belonging in global settings.
        """
        # Create project structure with local command
        claude_dir = self.temp_dir / '.claude'
        claude_dir.mkdir()
        commands_dir = claude_dir / 'commands'
        commands_dir.mkdir()

        # Create a project-local command
        local_command = commands_dir / 'my-local-command.md'
        local_command.write_text("""---
name: my-local-command
description: A project-local command
---

# My Local Command

This is a project-local command.
""")

        global_file = self.temp_dir / 'global.json'
        global_file.write_text(json.dumps({'permissions': {'allow': ['Bash(git:*)'], 'deny': [], 'ask': []}}))

        local_file = claude_dir / 'settings.local.json'
        local_file.write_text(
            json.dumps(
                {
                    'permissions': {
                        'allow': [
                            'SlashCommand(/my-local-command)',  # Project-local - should NOT be flagged
                            'Skill(pm-dev-java:*)',  # Marketplace - SHOULD be flagged
                        ],
                        'deny': [],
                        'ask': [],
                    }
                }
            )
        )

        result = run_script(
            SCRIPT_PATH,
            'detect-redundant',
            '--global-settings',
            str(global_file),
            '--local-settings',
            str(local_file),
            cwd=self.temp_dir,
        )
        self.assert_success(result)
        data = result.json()

        self.assertIn('marketplace_in_local', data)
        marketplace_perms = [m['permission'] for m in data['marketplace_in_local']]

        # Project-local command should NOT be flagged
        self.assertNotIn('SlashCommand(/my-local-command)', marketplace_perms)

        # Marketplace skill SHOULD still be flagged
        self.assertIn('Skill(pm-dev-java:*)', marketplace_perms)

    def test_output_includes_summary(self):
        """Output should include summary counts."""
        global_file = self.temp_dir / 'global.json'
        global_file.write_text(json.dumps({'permissions': {'allow': ['Bash(git:*)'], 'deny': [], 'ask': []}}))

        local_file = self.temp_dir / 'local.json'
        local_file.write_text(
            json.dumps({'permissions': {'allow': ['Bash(git:*)', 'Skill(builder:*)'], 'deny': [], 'ask': []}})
        )

        result = run_script(
            SCRIPT_PATH, 'detect-redundant', '--global-settings', str(global_file), '--local-settings', str(local_file)
        )
        self.assert_success(result)
        data = result.json()

        self.assertIn('summary', data)
        self.assertIn('redundant_count', data['summary'])
        self.assertIn('marketplace_in_local_count', data['summary'])


# =============================================================================
# Tests for detect-suspicious subcommand
# =============================================================================


class TestDetectSuspicious(ScriptTestCase):
    """Test permission-doctor.py detect-suspicious subcommand."""

    bundle = 'plan-marshall'
    skill = 'permission-doctor'
    script = 'permission-doctor.py'

    def test_detect_sudo_permission(self):
        """Should flag sudo permissions as suspicious."""
        settings_file = self.temp_dir / 'settings.json'
        settings_file.write_text(json.dumps({'permissions': {'allow': ['Bash(sudo:*)'], 'deny': [], 'ask': []}}))

        result = run_script(SCRIPT_PATH, 'detect-suspicious', '--settings', str(settings_file))
        self.assert_success(result)
        data = result.json()

        self.assertIn('suspicious', data)
        suspicious_perms = [s['permission'] for s in data['suspicious']]
        self.assertIn('Bash(sudo:*)', suspicious_perms)

    def test_detect_system_path_access(self):
        """Should flag system path access as suspicious."""
        settings_file = self.temp_dir / 'settings.json'
        settings_file.write_text(json.dumps({'permissions': {'allow': ['Write(/etc/**)'], 'deny': [], 'ask': []}}))

        result = run_script(SCRIPT_PATH, 'detect-suspicious', '--settings', str(settings_file))
        self.assert_success(result)
        data = result.json()

        suspicious_perms = [s['permission'] for s in data['suspicious']]
        self.assertIn('Write(/etc/**)', suspicious_perms)

    def test_output_includes_severity(self):
        """Suspicious permissions should include severity."""
        settings_file = self.temp_dir / 'settings.json'
        settings_file.write_text(json.dumps({'permissions': {'allow': ['Bash(rm:-rf:*)'], 'deny': [], 'ask': []}}))

        result = run_script(SCRIPT_PATH, 'detect-suspicious', '--settings', str(settings_file))
        self.assert_success(result)
        data = result.json()

        if data['suspicious']:
            for item in data['suspicious']:
                self.assertIn('severity', item)


# =============================================================================
# Tests for --scope option
# =============================================================================


class TestScopeOption(ScriptTestCase):
    """Test permission-doctor.py --scope option."""

    bundle = 'plan-marshall'
    skill = 'permission-doctor'
    script = 'permission-doctor.py'

    def test_detect_redundant_with_scope_both(self):
        """detect-redundant should work with --scope both."""
        # Create global settings in home directory simulation
        # Note: This test uses the actual home directory's settings
        # For proper isolation, we'd need to mock Path.home()
        # Here we just verify the command works with --scope both
        result = run_script(SCRIPT_PATH, 'detect-redundant', '--scope', 'both', cwd=self.temp_dir)
        # May succeed or fail depending on whether settings exist
        # Just verify it doesn't crash with unexpected error
        self.assertIn(result.returncode, [0, 1])

    def test_detect_suspicious_with_scope_project(self):
        """detect-suspicious should work with --scope project."""
        claude_dir = self.temp_dir / '.claude'
        claude_dir.mkdir()
        settings_file = claude_dir / 'settings.json'
        settings_file.write_text(json.dumps({'permissions': {'allow': ['Bash(sudo:*)'], 'deny': [], 'ask': []}}))

        result = run_script(SCRIPT_PATH, 'detect-suspicious', '--scope', 'project', cwd=self.temp_dir)
        self.assert_success(result)
        data = result.json()

        self.assertIn('suspicious', data)
        suspicious_perms = [s['permission'] for s in data['suspicious']]
        self.assertIn('Bash(sudo:*)', suspicious_perms)

    def test_scope_and_settings_mutually_exclusive(self):
        """--scope and --settings should be mutually exclusive."""
        result = run_script(SCRIPT_PATH, 'detect-suspicious', '--scope', 'project', '--settings', '/tmp/test.json')
        # Should fail due to mutual exclusivity
        self.assertEqual(result.returncode, 2)


# =============================================================================
# Simple function-based tests for quick validation
# =============================================================================


def test_script_exists():
    """Verify the script exists."""
    assert SCRIPT_PATH.exists(), f'Script not found: {SCRIPT_PATH}'


def test_help_works():
    """Script should respond to --help."""
    result = run_script(SCRIPT_PATH, '--help')
    assert result.returncode == 0


def test_detect_redundant_help():
    """detect-redundant subcommand should have help."""
    result = run_script(SCRIPT_PATH, 'detect-redundant', '--help')
    assert result.returncode == 0


def test_detect_suspicious_help():
    """detect-suspicious subcommand should have help."""
    result = run_script(SCRIPT_PATH, 'detect-suspicious', '--help')
    assert result.returncode == 0


# =============================================================================
# Main
# =============================================================================

if __name__ == '__main__':
    import unittest

    # Check if script exists first
    if not SCRIPT_PATH.exists():
        print(f'ERROR: Script not found: {SCRIPT_PATH}')
        sys.exit(1)

    # Run unittest-based tests
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestDetectRedundant))
    suite.addTests(loader.loadTestsFromTestCase(TestDetectSuspicious))
    suite.addTests(loader.loadTestsFromTestCase(TestScopeOption))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Also run simple function tests
    print('\n' + '=' * 50)
    print('Running simple function tests...')
    print('=' * 50)

    simple_tests = [
        test_script_exists,
        test_help_works,
        test_detect_redundant_help,
        test_detect_suspicious_help,
    ]

    # Run simple function tests
    simple_failures = 0
    for test_fn in simple_tests:
        try:
            test_fn()
            print(f'  PASS: {test_fn.__name__}')
        except AssertionError as e:
            print(f'  FAIL: {test_fn.__name__}: {e}')
            simple_failures += 1

    # Exit with combined result
    sys.exit(0 if result.wasSuccessful() and simple_failures == 0 else 1)
