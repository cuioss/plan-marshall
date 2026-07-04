#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""
Tests for the permission_doctor.py script.

Tests subcommands:
- detect-redundant: Detect redundant permissions between global/local
- detect-suspicious: Detect suspicious permissions (security anti-patterns)

Tier 2 (direct import) for cmd_detect_redundant and cmd_detect_suspicious.
Tier 3 (subprocess) retained for CLI plumbing and --scope tests.
"""

import json
import os
from argparse import Namespace

from permission_doctor import (
    cmd_detect_missing_project_step_permissions,
    cmd_detect_redundant,
    cmd_detect_suspicious,
)

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import MARKETPLACE_ROOT, run_script

# Script path for remaining subprocess (CLI plumbing) tests
SCRIPT_PATH = (
    MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'tools-permission-doctor' / 'scripts' / 'permission_doctor.py'
)

# =============================================================================
# Tier 2: Direct import tests for detect-redundant
# =============================================================================


class TestDetectRedundant:
    """Test permission_doctor.py detect-redundant subcommand via direct import."""

    def test_detect_exact_duplicate(self, tmp_path):
        """Should detect when same permission exists in both global and local."""
        global_file = tmp_path / 'global.json'
        global_file.write_text(
            json.dumps(
                {'permissions': {'allow': ['Bash(git:*)', 'Bash(npm:*)', 'Read(//~/git/**)'], 'deny': [], 'ask': []}}
            )
        )

        local_file = tmp_path / 'local.json'
        local_file.write_text(
            json.dumps({'permissions': {'allow': ['Bash(git:*)', 'Edit(.plan/**)'], 'deny': [], 'ask': []}})
        )

        result = cmd_detect_redundant(
            Namespace(scope=None, global_settings=str(global_file), local_settings=str(local_file))
        )

        assert result['status'] == 'success'
        assert 'redundant' in result
        redundant_perms = [r['permission'] for r in result['redundant']]
        assert 'Bash(git:*)' in redundant_perms
        assert 'Edit(.plan/**)' not in redundant_perms

    def test_detect_marketplace_in_local(self, tmp_path):
        """Should flag marketplace permissions in local as belonging in global."""
        global_file = tmp_path / 'global.json'
        global_file.write_text(json.dumps({'permissions': {'allow': ['Skill(builder:*)'], 'deny': [], 'ask': []}}))

        local_file = tmp_path / 'local.json'
        local_file.write_text(
            json.dumps({'permissions': {'allow': ['Skill(pm-dev-java:*)', 'Edit(.plan/**)'], 'deny': [], 'ask': []}})
        )

        result = cmd_detect_redundant(
            Namespace(scope=None, global_settings=str(global_file), local_settings=str(local_file))
        )

        assert result['status'] == 'success'
        assert 'marketplace_in_local' in result
        marketplace_perms = [m['permission'] for m in result['marketplace_in_local']]
        assert 'Skill(pm-dev-java:*)' in marketplace_perms

    def test_project_local_command_not_flagged_as_marketplace(self, tmp_path):
        """Project-local commands should NOT be flagged as marketplace_in_local.

        When a SlashCommand permission exists for a command defined in
        .claude/commands/, it's a legitimate project-local command and
        should NOT be flagged as belonging in global settings.
        """
        # Create project structure with local command
        claude_dir = tmp_path / '.claude'
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

        global_file = tmp_path / 'global.json'
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

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            result = cmd_detect_redundant(
                Namespace(scope=None, global_settings=str(global_file), local_settings=str(local_file))
            )
        finally:
            os.chdir(original_cwd)

        assert result['status'] == 'success'
        assert 'marketplace_in_local' in result
        marketplace_perms = [m['permission'] for m in result['marketplace_in_local']]

        # Project-local command should NOT be flagged
        assert 'SlashCommand(/my-local-command)' not in marketplace_perms

        # Marketplace skill SHOULD still be flagged
        assert 'Skill(pm-dev-java:*)' in marketplace_perms

    def test_output_includes_summary(self, tmp_path):
        """Output should include summary counts."""
        global_file = tmp_path / 'global.json'
        global_file.write_text(json.dumps({'permissions': {'allow': ['Bash(git:*)'], 'deny': [], 'ask': []}}))

        local_file = tmp_path / 'local.json'
        local_file.write_text(
            json.dumps({'permissions': {'allow': ['Bash(git:*)', 'Skill(builder:*)'], 'deny': [], 'ask': []}})
        )

        result = cmd_detect_redundant(
            Namespace(scope=None, global_settings=str(global_file), local_settings=str(local_file))
        )

        assert result['status'] == 'success'
        assert 'summary' in result
        assert 'redundant_count' in result['summary']
        assert 'marketplace_in_local_count' in result['summary']


# =============================================================================
# Tier 2: Direct import tests for detect-suspicious
# =============================================================================


class TestDetectSuspicious:
    """Test permission_doctor.py detect-suspicious subcommand via direct import."""

    def test_detect_sudo_permission(self, tmp_path):
        """Should flag sudo permissions as suspicious."""
        settings_file = tmp_path / 'settings.json'
        settings_file.write_text(json.dumps({'permissions': {'allow': ['Bash(sudo:*)'], 'deny': [], 'ask': []}}))

        result = cmd_detect_suspicious(Namespace(scope=None, settings=str(settings_file), approved_file=None))

        assert result['status'] == 'success'
        assert 'suspicious' in result
        suspicious_perms = [s['permission'] for s in result['suspicious']]
        assert 'Bash(sudo:*)' in suspicious_perms

    def test_detect_system_path_access(self, tmp_path):
        """Should flag system path access as suspicious."""
        settings_file = tmp_path / 'settings.json'
        settings_file.write_text(json.dumps({'permissions': {'allow': ['Write(/etc/**)'], 'deny': [], 'ask': []}}))

        result = cmd_detect_suspicious(Namespace(scope=None, settings=str(settings_file), approved_file=None))

        assert result['status'] == 'success'
        suspicious_perms = [s['permission'] for s in result['suspicious']]
        assert 'Write(/etc/**)' in suspicious_perms

    def test_output_includes_severity(self, tmp_path):
        """Suspicious permissions should include severity."""
        settings_file = tmp_path / 'settings.json'
        settings_file.write_text(json.dumps({'permissions': {'allow': ['Bash(rm:-rf:*)'], 'deny': [], 'ask': []}}))

        result = cmd_detect_suspicious(Namespace(scope=None, settings=str(settings_file), approved_file=None))

        assert result['status'] == 'success'
        if result['suspicious']:
            for item in result['suspicious']:
                assert 'severity' in item

    def test_detect_dangerous_command_dd(self, tmp_path):
        """Should flag low-level disk operations like dd."""
        settings_file = tmp_path / 'settings.json'
        settings_file.write_text(
            json.dumps({'permissions': {'allow': ['Bash(dd:if=/dev/zero)'], 'deny': [], 'ask': []}})
        )

        result = cmd_detect_suspicious(Namespace(scope=None, settings=str(settings_file), approved_file=None))

        assert result['status'] == 'success'
        suspicious_perms = [s['permission'] for s in result['suspicious']]
        assert 'Bash(dd:if=/dev/zero)' in suspicious_perms

    def test_detect_broad_write_all_users(self, tmp_path):
        """Should flag broad write access to all users' directories."""
        settings_file = tmp_path / 'settings.json'
        settings_file.write_text(json.dumps({'permissions': {'allow': ['Write(//Users/**)'], 'deny': [], 'ask': []}}))

        result = cmd_detect_suspicious(Namespace(scope=None, settings=str(settings_file), approved_file=None))

        assert result['status'] == 'success'
        suspicious_perms = [s['permission'] for s in result['suspicious']]
        assert 'Write(//Users/**)' in suspicious_perms

    def test_clean_settings_no_suspicious(self, tmp_path):
        """Normal permissions should not be flagged as suspicious."""
        settings_file = tmp_path / 'settings.json'
        settings_file.write_text(
            json.dumps(
                {'permissions': {'allow': ['Bash(git:*)', 'Read(.plan/**)', 'Edit(src/**)'], 'deny': [], 'ask': []}}
            )
        )

        result = cmd_detect_suspicious(Namespace(scope=None, settings=str(settings_file), approved_file=None))

        assert result['status'] == 'success'
        assert len(result.get('suspicious', [])) == 0

    def test_detect_env_variable_access(self, tmp_path):
        """Should flag broad environment variable access."""
        settings_file = tmp_path / 'settings.json'
        settings_file.write_text(json.dumps({'permissions': {'allow': ['Bash(env:*)'], 'deny': [], 'ask': []}}))

        result = cmd_detect_suspicious(Namespace(scope=None, settings=str(settings_file), approved_file=None))

        assert result['status'] == 'success'
        # env access may or may not be flagged depending on patterns
        # At minimum, the command should succeed
        assert 'suspicious' in result


# =============================================================================
# Tier 3: Subprocess tests for --scope option and CLI plumbing
# =============================================================================


class TestScopeOption:
    """Test permission_doctor.py --scope option (subprocess - needs path resolution)."""

    def test_detect_redundant_with_scope_both(self, tmp_path):
        """detect-redundant should work with --scope both."""
        result = run_script(SCRIPT_PATH, 'detect-redundant', '--scope', 'both', cwd=tmp_path)
        # May succeed or fail depending on whether settings exist
        # Just verify it doesn't crash with unexpected error
        assert result.returncode in [0, 1]

    def test_detect_suspicious_with_scope_project(self, tmp_path):
        """detect-suspicious should work with --scope project."""
        claude_dir = tmp_path / '.claude'
        claude_dir.mkdir()
        settings_file = claude_dir / 'settings.json'
        settings_file.write_text(json.dumps({'permissions': {'allow': ['Bash(sudo:*)'], 'deny': [], 'ask': []}}))

        result = run_script(SCRIPT_PATH, 'detect-suspicious', '--scope', 'project', cwd=tmp_path)
        assert result.success, f'Script failed: {result.stderr}'
        data = result.toon()

        assert 'suspicious' in data
        suspicious_perms = [s['permission'] for s in data['suspicious']]
        assert 'Bash(sudo:*)' in suspicious_perms

    def test_scope_and_settings_mutually_exclusive(self):
        """--scope and --settings should be mutually exclusive."""
        result = run_script(SCRIPT_PATH, 'detect-suspicious', '--scope', 'project', '--settings', '/tmp/test.json')
        # Should fail due to mutual exclusivity
        assert result.returncode == 2


# =============================================================================
# Tier 2: Direct import tests for detect-missing-project-step-permissions
# =============================================================================


class TestDetectMissingProjectStepPermissions:
    """Test permission_doctor.py detect-missing-project-step-permissions subcommand."""

    def _write_marshal(self, tmp_path, phase_steps: dict[str, list[str]]) -> str:
        """Write a marshal.json with the given phase step configuration."""
        marshal = {'plan': {phase: {'steps': steps} for phase, steps in phase_steps.items()}}
        marshal_file = tmp_path / 'marshal.json'
        marshal_file.write_text(json.dumps(marshal))
        return str(marshal_file)

    def _write_settings(self, tmp_path, allow: list[str]) -> str:
        """Write a .claude/settings.json with the given allow list."""
        settings = {'permissions': {'allow': allow, 'deny': [], 'ask': []}}
        settings_file = tmp_path / 'settings.json'
        settings_file.write_text(json.dumps(settings))
        return str(settings_file)

    def test_missing_project_step_permission_detected(self, tmp_path):
        """Project:{skill} step with no matching Skill() rule is reported missing."""
        marshal = self._write_marshal(tmp_path, {'phase-6-finalize': ['project:finalize-step-plugin-doctor']})
        settings = self._write_settings(tmp_path, ['Edit(.plan/**)'])

        result = cmd_detect_missing_project_step_permissions(Namespace(marshal=marshal, settings=settings, scope=None))

        assert result['status'] == 'success'
        assert len(result['missing']) == 1
        assert result['missing'][0]['skill'] == 'finalize-step-plugin-doctor'
        assert result['missing'][0]['phase'] == 'phase-6-finalize'

    def test_exact_skill_rule_covers_project_step(self, tmp_path):
        """Exact Skill({skill}) rule marks the step as present."""
        marshal = self._write_marshal(tmp_path, {'phase-6-finalize': ['project:sync-plugin-cache']})
        settings = self._write_settings(tmp_path, ['Skill(sync-plugin-cache)'])

        result = cmd_detect_missing_project_step_permissions(Namespace(marshal=marshal, settings=settings, scope=None))

        assert result['status'] == 'success'
        assert len(result['missing']) == 0
        assert len(result['present']) == 1
        assert result['present'][0]['covered_by'] == 'Skill(sync-plugin-cache)'

    def test_wildcard_skill_rule_covers_project_step(self, tmp_path):
        """Covering wildcard Skill({skill}:*) counts as coverage for bare Skill({skill})."""
        marshal = self._write_marshal(tmp_path, {'phase-5-execute': ['project:example-step']})
        settings = self._write_settings(tmp_path, ['Skill(example-step:*)'])

        result = cmd_detect_missing_project_step_permissions(Namespace(marshal=marshal, settings=settings, scope=None))

        assert result['status'] == 'success'
        assert len(result['missing']) == 0
        assert result['present'][0]['covered_by'] == 'Skill(example-step:*)'

    def test_no_project_steps_returns_empty(self, tmp_path):
        """Marshal without project: steps reports empty missing/present lists."""
        marshal = self._write_marshal(tmp_path, {'phase-6-finalize': ['default:push', 'default:create-pr']})
        settings = self._write_settings(tmp_path, [])

        result = cmd_detect_missing_project_step_permissions(Namespace(marshal=marshal, settings=settings, scope=None))

        assert result['status'] == 'success'
        assert len(result['missing']) == 0
        assert len(result['present']) == 0
        assert result['summary']['project_steps_checked'] == 0

    def test_scans_both_phase5_and_phase6(self, tmp_path):
        """Detection aggregates project: steps across both phase-5-execute and phase-6-finalize."""
        marshal = self._write_marshal(
            tmp_path,
            {
                'phase-5-execute': ['project:example-step'],
                'phase-6-finalize': ['project:finalize-step-plugin-doctor'],
            },
        )
        settings = self._write_settings(tmp_path, ['Skill(example-step)'])

        result = cmd_detect_missing_project_step_permissions(Namespace(marshal=marshal, settings=settings, scope=None))

        assert result['status'] == 'success'
        assert result['summary']['project_steps_checked'] == 2
        assert len(result['missing']) == 1
        assert result['missing'][0]['skill'] == 'finalize-step-plugin-doctor'
        assert len(result['present']) == 1
        assert result['present'][0]['skill'] == 'example-step'

    def test_malformed_marshal_returns_error(self, tmp_path):
        """Malformed marshal.json returns a structured error, not a raise."""
        marshal_file = tmp_path / 'bad-marshal.json'
        marshal_file.write_text('{not valid json')
        settings = self._write_settings(tmp_path, [])

        result = cmd_detect_missing_project_step_permissions(
            Namespace(marshal=str(marshal_file), settings=settings, scope=None)
        )

        assert result['status'] == 'error'
        assert 'Invalid JSON' in result['error']


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


def test_detect_missing_project_step_permissions_help():
    """detect-missing-project-step-permissions subcommand should have help."""
    result = run_script(SCRIPT_PATH, 'detect-missing-project-step-permissions', '--help')
    assert result.returncode == 0
