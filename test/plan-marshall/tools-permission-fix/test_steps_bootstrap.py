#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Apply-project-step-permissions + bootstrap (carve 2 split)."""

import json

import pytest
from _permission_fix_fixtures import (
    read_settings,
    write_marshal,
    write_settings_str,
)

from conftest import MARKETPLACE_ROOT, parse_ns, run_script

SCRIPT_PATH = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'tools-permission-fix' / 'scripts' / 'permission_fix.py'

from permission_fix import (  # noqa: E402
    cmd_add,
    cmd_apply_fixes,
    cmd_apply_project_step_permissions,
    cmd_cleanup_scripts,
    cmd_consolidate,
    cmd_ensure,
    cmd_ensure_executor,
    cmd_ensure_wildcards,
    cmd_generate_wildcards,
    cmd_migrate_executor,
    cmd_remove,
    cmd_remove_redundant,
    scan_marketplace_dir,
)


class TestApplyProjectStepPermissions:
    """Test permission_fix.py apply-project-step-permissions subcommand."""

    def test_dry_run_does_not_mutate_settings(self, tmp_path):
        """--dry-run must not touch the settings file."""
        marshal = write_marshal(tmp_path, {'phase-6-finalize': ['project:finalize-step-plugin-doctor']})
        settings = write_settings_str(tmp_path, ['Edit(.plan/**)'])
        original = read_settings(settings)

        result = cmd_apply_project_step_permissions(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'apply-project-step-permissions',
                '--marshal',
                str(marshal),
                '--settings',
                str(settings),
                '--dry-run',
            )
        )

        assert result['status'] == 'success'
        assert result['added'] == ['Skill(finalize-step-plugin-doctor)']
        assert not result['applied']
        assert read_settings(settings) == original

    def test_default_run_appends_missing_rules(self, tmp_path):
        """Default run appends missing Skill() rules and sorts the allow list."""
        marshal = write_marshal(tmp_path, {'phase-6-finalize': ['project:finalize-step-plugin-doctor']})
        settings = write_settings_str(tmp_path, ['Edit(.plan/**)', 'Bash(git:*)'])

        result = cmd_apply_project_step_permissions(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'apply-project-step-permissions',
                '--marshal',
                str(marshal),
                '--settings',
                str(settings),
            )
        )

        assert result['status'] == 'success'
        assert result['applied']
        allow = read_settings(settings)['permissions']['allow']
        assert 'Skill(finalize-step-plugin-doctor)' in allow
        assert allow == sorted(allow)

    def test_idempotent_re_run(self, tmp_path):
        """Running twice must not create duplicates."""
        marshal = write_marshal(tmp_path, {'phase-6-finalize': ['project:finalize-step-plugin-doctor']})
        settings = write_settings_str(tmp_path, [])

        cmd_apply_project_step_permissions(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'apply-project-step-permissions',
                '--marshal',
                str(marshal),
                '--settings',
                str(settings),
            )
        )
        result = cmd_apply_project_step_permissions(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'apply-project-step-permissions',
                '--marshal',
                str(marshal),
                '--settings',
                str(settings),
            )
        )

        assert result['status'] == 'success'
        assert result['added'] == []
        assert result['summary']['already_present_count'] == 1
        allow = read_settings(settings)['permissions']['allow']
        assert allow.count('Skill(finalize-step-plugin-doctor)') == 1

    def test_wildcard_coverage_short_circuits_add(self, tmp_path):
        """Covering wildcard Skill({skill}:*) prevents adding bare Skill({skill})."""
        marshal = write_marshal(tmp_path, {'phase-5-execute': ['project:example-step']})
        settings = write_settings_str(tmp_path, ['Skill(example-step:*)'])

        result = cmd_apply_project_step_permissions(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'apply-project-step-permissions',
                '--marshal',
                str(marshal),
                '--settings',
                str(settings),
            )
        )

        assert result['status'] == 'success'
        assert result['added'] == []
        allow = read_settings(settings)['permissions']['allow']
        assert 'Skill(example-step)' not in allow


def test_permission_fix_imports_without_executor_pythonpath():
    """permission_fix.py must resolve its own imports without executor PYTHONPATH.

    This script is called directly during wizard Step 3 (before executor exists)
    to ensure the executor permission. It must self-resolve its dependencies.
    """
    import os
    import subprocess
    import sys

    env = os.environ.copy()
    env.pop('PYTHONPATH', None)
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), '--help'],
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )
    assert result.returncode == 0, f'permission_fix.py failed without PYTHONPATH:\n{result.stderr}'


class TestExecutorPattern:
    """Test permission_fix.py executor pattern subcommands."""

    def test_ensure_executor_adds_permission(self, tmp_path):
        """Should add executor permission when missing."""
        claude_dir = tmp_path / '.claude'
        claude_dir.mkdir()
        settings_file = claude_dir / 'settings.json'
        settings_file.write_text(json.dumps({'permissions': {'allow': ['Bash(git:*)'], 'deny': [], 'ask': []}}))

        result = run_script(SCRIPT_PATH, 'ensure-executor', '--target', 'project', cwd=tmp_path)
        assert result.success, f'Script failed: {result.stderr}'
        data = result.toon()

        assert data.get('success')
        assert data.get('action') == 'added'

        settings = json.loads(settings_file.read_text())
        assert 'Bash(python3 .plan/execute-script.py *)' in settings['permissions']['allow']

    def test_ensure_executor_already_exists(self, tmp_path):
        """Should report when executor permission already exists."""
        claude_dir = tmp_path / '.claude'
        claude_dir.mkdir()
        settings_file = claude_dir / 'settings.json'
        settings_file.write_text(
            json.dumps({'permissions': {'allow': ['Bash(python3 .plan/execute-script.py *)'], 'deny': [], 'ask': []}})
        )

        result = run_script(SCRIPT_PATH, 'ensure-executor', '--target', 'project', cwd=tmp_path)
        assert result.success, f'Script failed: {result.stderr}'
        data = result.toon()

        assert data.get('success')
        assert data.get('action') == 'already_exists'

    def test_cleanup_scripts_removes_individual_permissions(self, tmp_path):
        """Should remove individual script permissions."""
        claude_dir = tmp_path / '.claude'
        claude_dir.mkdir()
        settings_file = claude_dir / 'settings.json'
        settings_file.write_text(
            json.dumps(
                {
                    'permissions': {
                        'allow': [
                            'Bash(git:*)',
                            'Bash(python3 /path/to/marketplace/bundles/test/skills/foo/scripts/*:*)',
                            'Bash(python3 /path/to/marketplace/bundles/test/skills/bar/scripts/*:*)',
                        ],
                        'deny': [],
                        'ask': [],
                    }
                }
            )
        )

        result = run_script(SCRIPT_PATH, 'cleanup-scripts', '--target', 'project', cwd=tmp_path)
        assert result.success, f'Script failed: {result.stderr}'
        data = result.toon()

        assert data.get('success')
        assert data.get('individual_count') == 2

        settings = json.loads(settings_file.read_text())
        assert len(settings['permissions']['allow']) == 1
        assert 'Bash(git:*)' in settings['permissions']['allow']

    def test_migrate_executor_full_migration(self, tmp_path):
        """Should add executor and remove individual permissions."""
        claude_dir = tmp_path / '.claude'
        claude_dir.mkdir()
        settings_file = claude_dir / 'settings.json'
        settings_file.write_text(
            json.dumps(
                {
                    'permissions': {
                        'allow': [
                            'Bash(git:*)',
                            'Bash(python3 /path/to/marketplace/bundles/test/skills/foo/scripts/*:*)',
                        ],
                        'deny': [],
                        'ask': [],
                    }
                }
            )
        )

        result = run_script(SCRIPT_PATH, 'migrate-executor', '--target', 'project', cwd=tmp_path)
        assert result.success, f'Script failed: {result.stderr}'
        data = result.toon()

        assert data.get('success')
        assert 'executor' in data
        assert 'cleanup' in data

        settings = json.loads(settings_file.read_text())
        assert 'Bash(python3 .plan/execute-script.py *)' in settings['permissions']['allow']
        assert 'Bash(git:*)' in settings['permissions']['allow']
        assert len(settings['permissions']['allow']) == 2


def test_script_exists():
    """Verify the script exists."""
    assert SCRIPT_PATH.exists(), f'Script not found: {SCRIPT_PATH}'


#: Every subcommand the script declares, plus the empty prefix for the top-level
#: parser. Kept as its own constant so the roster reads as the enumeration it is.
_HELP_TARGETS: tuple[tuple[str, ...], ...] = (
    (),
    ('consolidate',),
    ('ensure-wildcards',),
    ('apply-fixes',),
    ('add',),
    ('remove',),
    ('ensure',),
    ('generate-wildcards',),
    ('ensure-executor',),
    ('cleanup-scripts',),
    ('migrate-executor',),
    ('apply-project-step-permissions',),
    ('remove-redundant',),
)


@pytest.mark.parametrize(
    'verb',
    _HELP_TARGETS,
    ids=[('top-level' if not verb else verb[0]) for verb in _HELP_TARGETS],
)
def test_help_exits_zero(verb):
    """Help is reachable at the top level and on every declared subcommand."""
    assert run_script(SCRIPT_PATH, *verb, '--help').returncode == 0
