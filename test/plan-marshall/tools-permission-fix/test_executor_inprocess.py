#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Executor in-process + errors (carve 2 split)."""

import ast
import json
from argparse import Namespace
from pathlib import Path

import pytest
from _permission_fix_fixtures import (
    RETIRED_DEFAULT,
    allow_list,
    assert_declines,
    build_project,
    dual_file_project,
    force_opencode,
    force_unsupported_runtime,
    in_tmp_cwd,
    read_allow,
    roster_handlers,
    seam_callers,
    seed_retired,
    setup_project,
    write_marshal,
    write_settings,
    write_settings_str,
)

from conftest import load_script_module, parse_ns

pf = load_script_module('plan-marshall', 'tools-permission-fix', 'permission_fix.py', 'pf_behavior')


class TestExecutorSubcommandsInProcess:
    """Test executor-pattern subcommands against a chdir'd tmp project dir."""

    @pytest.fixture()
    def in_tmp_cwd(self, tmp_path, monkeypatch):
        """Run with the process working directory inside an isolated tmp_path."""
        monkeypatch.chdir(tmp_path)

    def test_ensure_executor_dry_run_would_add(self, tmp_path, in_tmp_cwd):
        """Dry-run reports 'would_add' and leaves the file untouched."""
        settings_file = setup_project(tmp_path, ['Bash(git:*)'])

        result = pf.cmd_ensure_executor(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'ensure-executor',
                '--target',
                'project',
                '--dry-run',
            )
        )

        assert result['action'] == 'would_add'
        assert result['success'] is True
        assert pf.EXECUTOR_PERMISSION not in read_allow(settings_file)

    def test_cleanup_scripts_nothing_to_remove(self, tmp_path, in_tmp_cwd):
        """With no individual script perms, cleanup reports nothing to remove."""
        setup_project(tmp_path, ['Bash(git:*)'])

        result = pf.cmd_cleanup_scripts(
            parse_ns(
                'plan-marshall', 'tools-permission-fix', 'permission_fix.py', 'cleanup-scripts', '--target', 'project'
            )
        )

        assert result['action'] == 'nothing_to_remove'
        assert result['success'] is True

    def test_cleanup_scripts_dry_run_would_remove(self, tmp_path, in_tmp_cwd):
        """Dry-run reports the would-remove count without modifying the file."""
        script_perm = 'Bash(python3 /x/marketplace/bundles/b/skills/s/scripts/run.py:*)'
        settings_file = setup_project(tmp_path, ['Bash(git:*)', script_perm])

        result = pf.cmd_cleanup_scripts(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'cleanup-scripts',
                '--target',
                'project',
                '--dry-run',
            )
        )

        assert result['action'] == 'would_remove'
        assert result['total_would_remove'] == 1
        assert script_perm in read_allow(settings_file)

    def test_cleanup_scripts_removes_broad_python(self, tmp_path, in_tmp_cwd):
        """With --remove-broad-python the overly broad python wildcard is removed."""
        settings_file = setup_project(tmp_path, ['Bash(git:*)', pf.OVERLY_BROAD_PYTHON])

        result = pf.cmd_cleanup_scripts(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'cleanup-scripts',
                '--target',
                'project',
                '--remove-broad-python',
            )
        )

        assert result['success'] is True
        assert result['broad_python_removed'] is True
        assert pf.OVERLY_BROAD_PYTHON not in read_allow(settings_file)

    def test_migrate_executor_dry_run(self, tmp_path, in_tmp_cwd):
        """Dry-run reports planned would-add/would-remove without writing."""
        script_perm = 'Bash(python3 /x/marketplace/bundles/b/skills/s/scripts/run.py:*)'
        settings_file = setup_project(tmp_path, ['Bash(git:*)', script_perm])

        result = pf.cmd_migrate_executor(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'migrate-executor',
                '--target',
                'project',
                '--dry-run',
            )
        )

        assert result['success'] is True
        assert result['executor']['action'] == 'would_add'
        assert result['cleanup']['individual_would_remove'] == 1
        # Dry-run leaves the file unchanged.
        assert pf.EXECUTOR_PERMISSION not in read_allow(settings_file)

    def test_migrate_executor_executor_already_present_removes_broad_python(self, tmp_path, in_tmp_cwd):
        """When the executor perm already exists, migration only cleans up extras."""
        settings_file = setup_project(tmp_path, ['Bash(git:*)', pf.EXECUTOR_PERMISSION, pf.OVERLY_BROAD_PYTHON])

        result = pf.cmd_migrate_executor(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'migrate-executor',
                '--target',
                'project',
                '--remove-broad-python',
            )
        )

        assert result['success'] is True
        assert result['executor']['action'] == 'already_exists'
        allow = read_allow(settings_file)
        assert pf.OVERLY_BROAD_PYTHON not in allow
        assert pf.EXECUTOR_PERMISSION in allow


class TestAddRemoveInProcess:
    """Test cmd_add / cmd_remove write and idempotent branches in-process."""

    @pytest.fixture()
    def in_tmp_cwd(self, tmp_path, monkeypatch):
        """Run with the process working directory inside an isolated tmp_path."""
        monkeypatch.chdir(tmp_path)

    def test_add_writes_new_permission(self, tmp_path, in_tmp_cwd):
        """Adding a new permission writes it and reports 'added'."""
        settings_file = setup_project(tmp_path, ['Bash(git:*)'])

        result = pf.cmd_add(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'add',
                '--permission',
                'Bash(npm:*)',
                '--target',
                'project',
            )
        )

        assert result['action'] == 'added'
        assert result['success'] is True
        assert 'Bash(npm:*)' in read_allow(settings_file)

    def test_add_existing_is_noop(self, tmp_path, in_tmp_cwd):
        """Adding an existing permission reports 'already_exists'."""
        setup_project(tmp_path, ['Bash(git:*)'])

        result = pf.cmd_add(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'add',
                '--permission',
                'Bash(git:*)',
                '--target',
                'project',
            )
        )

        assert result['action'] == 'already_exists'

    def test_remove_deletes_permission(self, tmp_path, in_tmp_cwd):
        """Removing an existing permission deletes it and reports 'removed'."""
        settings_file = setup_project(tmp_path, ['Bash(git:*)', 'Bash(npm:*)'])

        result = pf.cmd_remove(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'remove',
                '--permission',
                'Bash(npm:*)',
                '--target',
                'project',
            )
        )

        assert result['action'] == 'removed'
        assert 'Bash(npm:*)' not in read_allow(settings_file)

    def test_remove_absent_is_noop(self, tmp_path, in_tmp_cwd):
        """Removing a missing permission reports 'not_found'."""
        setup_project(tmp_path, ['Bash(git:*)'])

        result = pf.cmd_remove(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'remove',
                '--permission',
                'Bash(absent:*)',
                '--target',
                'project',
            )
        )

        assert result['action'] == 'not_found'


class TestRemoveRedundantErrors:
    """Test cmd_remove_redundant error branches that the happy-path suite omits."""

    def test_global_load_error(self, tmp_path):
        """A missing global settings file surfaces a structured error."""
        local_file = tmp_path / 'local.json'
        write_settings(local_file, ['Bash(git:*)'])

        result = pf.cmd_remove_redundant(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'remove-redundant',
                '--global-settings',
                str(tmp_path / 'missing-global.json'),
                '--local-settings',
                str(local_file),
            )
        )

        assert result['status'] == 'error'
        assert 'not found' in result['error']

    def test_local_load_error(self, tmp_path):
        """A missing local settings file surfaces a structured error."""
        global_file = tmp_path / 'global.json'
        write_settings(global_file, ['Bash(git:*)'])

        result = pf.cmd_remove_redundant(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'remove-redundant',
                '--global-settings',
                str(global_file),
                '--local-settings',
                str(tmp_path / 'missing-local.json'),
            )
        )

        assert result['status'] == 'error'


class TestApplyProjectStepPermissionsErrors:
    """Test cmd_apply_project_step_permissions error branches."""

    def test_marshal_load_error(self, tmp_path):
        """A missing marshal.json surfaces a structured error."""
        settings_file = tmp_path / 'settings.json'
        write_settings(settings_file, [])

        result = pf.cmd_apply_project_step_permissions(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'apply-project-step-permissions',
                '--marshal',
                str(tmp_path / 'missing.json'),
                '--settings',
                str(settings_file),
                '--dry-run',
            )
        )

        assert result['status'] == 'error'

    def test_settings_load_error(self, tmp_path):
        """A missing settings file surfaces a structured error after marshal loads."""
        marshal_file = tmp_path / 'marshal.json'
        marshal_file.write_text(json.dumps({'plan': {'phase-6-finalize': {'steps': []}}}))

        result = pf.cmd_apply_project_step_permissions(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'apply-project-step-permissions',
                '--marshal',
                str(marshal_file),
                '--settings',
                str(tmp_path / 'missing.json'),
                '--dry-run',
            )
        )

        assert result['status'] == 'error'
