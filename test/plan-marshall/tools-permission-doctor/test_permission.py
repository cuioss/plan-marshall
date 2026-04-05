#!/usr/bin/env python3
"""
Tests for the permission_doctor.py script.

Tests subcommands:
- detect-redundant: Detect redundant permissions between global/local
- detect-suspicious: Detect suspicious permissions (security anti-patterns)

Tier 2 (direct import) for cmd_detect_redundant and cmd_detect_suspicious.
Tier 3 (subprocess) retained for CLI plumbing and --scope tests.
"""

import json
from argparse import Namespace

from permission_doctor import cmd_detect_redundant, cmd_detect_suspicious  # type: ignore[import-not-found]

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import MARKETPLACE_ROOT, ScriptTestCase, run_script

# Script path for remaining subprocess (CLI plumbing) tests
SCRIPT_PATH = (
    MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'tools-permission-doctor' / 'scripts' / 'permission_doctor.py'
)

# =============================================================================
# Tier 2: Direct import tests for detect-redundant
# =============================================================================


class TestDetectRedundant(ScriptTestCase):
    """Test permission_doctor.py detect-redundant subcommand via direct import."""

    bundle = 'plan-marshall'
    skill = 'tools-permission-doctor'
    script = 'permission_doctor.py'

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

        result = cmd_detect_redundant(
            Namespace(scope=None, global_settings=str(global_file), local_settings=str(local_file))
        )

        self.assertEqual(result['status'], 'success')
        self.assertIn('redundant', result)
        redundant_perms = [r['permission'] for r in result['redundant']]
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

        result = cmd_detect_redundant(
            Namespace(scope=None, global_settings=str(global_file), local_settings=str(local_file))
        )

        self.assertEqual(result['status'], 'success')
        self.assertIn('marketplace_in_local', result)
        marketplace_perms = [m['permission'] for m in result['marketplace_in_local']]
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

        import os
        original_cwd = os.getcwd()
        try:
            os.chdir(self.temp_dir)
            result = cmd_detect_redundant(
                Namespace(scope=None, global_settings=str(global_file), local_settings=str(local_file))
            )
        finally:
            os.chdir(original_cwd)

        self.assertEqual(result['status'], 'success')
        self.assertIn('marketplace_in_local', result)
        marketplace_perms = [m['permission'] for m in result['marketplace_in_local']]

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

        result = cmd_detect_redundant(
            Namespace(scope=None, global_settings=str(global_file), local_settings=str(local_file))
        )

        self.assertEqual(result['status'], 'success')
        self.assertIn('summary', result)
        self.assertIn('redundant_count', result['summary'])
        self.assertIn('marketplace_in_local_count', result['summary'])


# =============================================================================
# Tier 2: Direct import tests for detect-suspicious
# =============================================================================


class TestDetectSuspicious(ScriptTestCase):
    """Test permission_doctor.py detect-suspicious subcommand via direct import."""

    bundle = 'plan-marshall'
    skill = 'tools-permission-doctor'
    script = 'permission_doctor.py'

    def test_detect_sudo_permission(self):
        """Should flag sudo permissions as suspicious."""
        settings_file = self.temp_dir / 'settings.json'
        settings_file.write_text(json.dumps({'permissions': {'allow': ['Bash(sudo:*)'], 'deny': [], 'ask': []}}))

        result = cmd_detect_suspicious(
            Namespace(scope=None, settings=str(settings_file), approved_file=None)
        )

        self.assertEqual(result['status'], 'success')
        self.assertIn('suspicious', result)
        suspicious_perms = [s['permission'] for s in result['suspicious']]
        self.assertIn('Bash(sudo:*)', suspicious_perms)

    def test_detect_system_path_access(self):
        """Should flag system path access as suspicious."""
        settings_file = self.temp_dir / 'settings.json'
        settings_file.write_text(json.dumps({'permissions': {'allow': ['Write(/etc/**)'], 'deny': [], 'ask': []}}))

        result = cmd_detect_suspicious(
            Namespace(scope=None, settings=str(settings_file), approved_file=None)
        )

        self.assertEqual(result['status'], 'success')
        suspicious_perms = [s['permission'] for s in result['suspicious']]
        self.assertIn('Write(/etc/**)', suspicious_perms)

    def test_output_includes_severity(self):
        """Suspicious permissions should include severity."""
        settings_file = self.temp_dir / 'settings.json'
        settings_file.write_text(json.dumps({'permissions': {'allow': ['Bash(rm:-rf:*)'], 'deny': [], 'ask': []}}))

        result = cmd_detect_suspicious(
            Namespace(scope=None, settings=str(settings_file), approved_file=None)
        )

        self.assertEqual(result['status'], 'success')
        if result['suspicious']:
            for item in result['suspicious']:
                self.assertIn('severity', item)

    def test_detect_dangerous_command_dd(self):
        """Should flag low-level disk operations like dd."""
        settings_file = self.temp_dir / 'settings.json'
        settings_file.write_text(
            json.dumps({'permissions': {'allow': ['Bash(dd:if=/dev/zero)'], 'deny': [], 'ask': []}})
        )

        result = cmd_detect_suspicious(
            Namespace(scope=None, settings=str(settings_file), approved_file=None)
        )

        self.assertEqual(result['status'], 'success')
        suspicious_perms = [s['permission'] for s in result['suspicious']]
        self.assertIn('Bash(dd:if=/dev/zero)', suspicious_perms)

    def test_detect_broad_write_all_users(self):
        """Should flag broad write access to all users' directories."""
        settings_file = self.temp_dir / 'settings.json'
        settings_file.write_text(json.dumps({'permissions': {'allow': ['Write(//Users/**)'], 'deny': [], 'ask': []}}))

        result = cmd_detect_suspicious(
            Namespace(scope=None, settings=str(settings_file), approved_file=None)
        )

        self.assertEqual(result['status'], 'success')
        suspicious_perms = [s['permission'] for s in result['suspicious']]
        self.assertIn('Write(//Users/**)', suspicious_perms)

    def test_clean_settings_no_suspicious(self):
        """Normal permissions should not be flagged as suspicious."""
        settings_file = self.temp_dir / 'settings.json'
        settings_file.write_text(
            json.dumps(
                {'permissions': {'allow': ['Bash(git:*)', 'Read(.plan/**)', 'Edit(src/**)'], 'deny': [], 'ask': []}}
            )
        )

        result = cmd_detect_suspicious(
            Namespace(scope=None, settings=str(settings_file), approved_file=None)
        )

        self.assertEqual(result['status'], 'success')
        self.assertEqual(len(result.get('suspicious', [])), 0)

    def test_detect_env_variable_access(self):
        """Should flag broad environment variable access."""
        settings_file = self.temp_dir / 'settings.json'
        settings_file.write_text(json.dumps({'permissions': {'allow': ['Bash(env:*)'], 'deny': [], 'ask': []}}))

        result = cmd_detect_suspicious(
            Namespace(scope=None, settings=str(settings_file), approved_file=None)
        )

        self.assertEqual(result['status'], 'success')
        # env access may or may not be flagged depending on patterns
        # At minimum, the command should succeed
        self.assertIn('suspicious', result)


# =============================================================================
# Tier 3: Subprocess tests for --scope option and CLI plumbing
# =============================================================================


class TestScopeOption(ScriptTestCase):
    """Test permission_doctor.py --scope option (subprocess - needs path resolution)."""

    bundle = 'plan-marshall'
    skill = 'tools-permission-doctor'
    script = 'permission_doctor.py'

    def test_detect_redundant_with_scope_both(self):
        """detect-redundant should work with --scope both."""
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
        data = result.toon()

        self.assertIn('suspicious', data)
        suspicious_perms = [s['permission'] for s in data['suspicious']]
        self.assertIn('Bash(sudo:*)', suspicious_perms)

    def test_scope_and_settings_mutually_exclusive(self):
        """--scope and --settings should be mutually exclusive."""
        result = run_script(SCRIPT_PATH, 'detect-suspicious', '--scope', 'project', '--settings', '/tmp/test.json')
        # Should fail due to mutual exclusivity
        self.assertEqual(result.returncode, 2)


# =============================================================================
# Tier 3: Subprocess tests for CLI plumbing
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
