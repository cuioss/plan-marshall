#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Ensure-wildcards + generate-wildcards (carve 2 split)."""

import json
from pathlib import Path

import pytest
from _permission_fix_fixtures import (
    RETIRED_DEFAULT,
    allow_list,
    create_marketplace,
    in_tmp_cwd,
    read_allow,
    read_settings,
    seed_retired,
    write_marshal,
    write_settings,
    write_settings_str,
)

from conftest import MARKETPLACE_ROOT, parse_ns, run_script

SCRIPT_PATH = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'tools-permission-fix' / 'scripts' / 'permission_fix.py'

from permission_fix import (  # noqa: E402
    cmd_apply_fixes,
    cmd_apply_project_step_permissions,
    cmd_consolidate,
    cmd_ensure_wildcards,
    cmd_generate_wildcards,
    cmd_remove_redundant,
    scan_marketplace_dir,
)


class TestEnsureWildcards:
    """Test permission_fix.py ensure-wildcards subcommand via direct import."""

    def test_adds_missing_wildcards(self, tmp_path):
        """Should add missing marketplace wildcards."""
        settings_file = tmp_path / 'settings.json'
        settings_file.write_text(json.dumps({'permissions': {'allow': ['Bash(git:*)'], 'deny': [], 'ask': []}}))

        marketplace_file = tmp_path / 'marketplace.json'
        marketplace_file.write_text(
            json.dumps(
                {
                    'bundles': {
                        'builder': {'path': 'marketplace/bundles/builder', 'skills': ['some-skill']},
                        'planning': {'path': 'marketplace/bundles/planning', 'commands': ['some-cmd']},
                    }
                }
            )
        )

        result = cmd_ensure_wildcards(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'ensure-wildcards',
                '--settings',
                str(settings_file),
                '--marketplace-json',
                str(marketplace_file),
                '--dry-run',
            )
        )

        assert result['status'] == 'success'
        assert 'added' in result
        added = result['added']
        assert 'Skill(builder:*)' in added
        assert 'SlashCommand(/planning:*)' in added

    def test_reports_already_present(self, tmp_path):
        """Should report wildcards already present."""
        settings_file = tmp_path / 'settings.json'
        settings_file.write_text(
            json.dumps(
                {'permissions': {'allow': ['Skill(builder:*)', 'SlashCommand(/builder:*)'], 'deny': [], 'ask': []}}
            )
        )

        marketplace_file = tmp_path / 'marketplace.json'
        marketplace_file.write_text(
            json.dumps(
                {
                    'bundles': {
                        'builder': {'path': 'marketplace/bundles/builder', 'skills': ['skill1'], 'commands': ['cmd1']},
                    }
                }
            )
        )

        result = cmd_ensure_wildcards(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'ensure-wildcards',
                '--settings',
                str(settings_file),
                '--marketplace-json',
                str(marketplace_file),
                '--dry-run',
            )
        )

        assert result['status'] == 'success'
        assert 'already_present' in result
        assert result['already_present'] == 2

    def test_bundles_with_skills_and_commands_arrays(self, tmp_path):
        """Should generate wildcards for bundles with skills/commands arrays."""
        settings_file = tmp_path / 'settings.json'
        settings_file.write_text(json.dumps({'permissions': {'allow': ['Bash(git:*)'], 'deny': [], 'ask': []}}))

        marketplace_file = tmp_path / 'marketplace.json'
        marketplace_file.write_text(
            json.dumps(
                {
                    'bundles': {
                        'plan-marshall': {
                            'path': 'marketplace/bundles/plan-marshall',
                            'skills': ['manage-status', 'plan-manage'],
                            'commands': ['plan-manage'],
                        },
                        'pm-dev-java': {
                            'path': 'marketplace/bundles/pm-dev-java',
                            'skills': ['cui-java-core'],
                            'commands': ['java-core'],
                        },
                    }
                }
            )
        )

        result = cmd_ensure_wildcards(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'ensure-wildcards',
                '--settings',
                str(settings_file),
                '--marketplace-json',
                str(marketplace_file),
                '--dry-run',
            )
        )

        assert result['status'] == 'success'
        assert 'added' in result
        added = result['added']
        assert 'Skill(plan-marshall:*)' in added
        assert 'SlashCommand(/plan-marshall:*)' in added
        assert 'Skill(pm-dev-java:*)' in added
        assert 'SlashCommand(/pm-dev-java:*)' in added
        assert result['total'] == 4

    def test_bundles_without_skills_commands_arrays(self, tmp_path):
        """Should assume bundles have both skills and commands when arrays absent."""
        settings_file = tmp_path / 'settings.json'
        settings_file.write_text(json.dumps({'permissions': {'allow': ['Bash(git:*)'], 'deny': [], 'ask': []}}))

        marketplace_file = tmp_path / 'marketplace.json'
        marketplace_file.write_text(
            json.dumps(
                {
                    'bundles': {
                        'plan-marshall': {'path': 'marketplace/bundles/plan-marshall'},
                        'pm-dev-java': {'path': 'marketplace/bundles/pm-dev-java'},
                    }
                }
            )
        )

        result = cmd_ensure_wildcards(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'ensure-wildcards',
                '--settings',
                str(settings_file),
                '--marketplace-json',
                str(marketplace_file),
                '--dry-run',
            )
        )

        assert result['status'] == 'success'
        assert 'added' in result
        added = result['added']
        assert 'Skill(plan-marshall:*)' in added
        assert 'SlashCommand(/plan-marshall:*)' in added
        assert 'Skill(pm-dev-java:*)' in added
        assert 'SlashCommand(/pm-dev-java:*)' in added
        assert result['bundles_analyzed'] == 2
        assert result['total'] == 4


class TestGenerateWildcards:
    """Test permission_fix.py generate-wildcards subcommand via direct import."""

    def test_generates_skill_wildcards(self, tmp_path):
        """Should generate Skill() wildcards from inventory."""
        inventory_file = tmp_path / 'inventory.json'
        inventory_file.write_text(
            json.dumps(
                {
                    'bundles': [
                        {
                            'name': 'builder',
                            'skills': [{'name': 'builder-gradle-rules'}, {'name': 'builder-maven-rules'}],
                            'commands': [],
                        }
                    ]
                }
            )
        )

        result = cmd_generate_wildcards(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'generate-wildcards',
                '--input',
                str(inventory_file),
            )
        )

        assert result['status'] == 'success'
        assert 'permissions' in result
        assert 'skill_wildcards' in result['permissions']
        assert 'Skill(builder:*)' in result['permissions']['skill_wildcards']

    def test_generates_command_wildcards(self, tmp_path):
        """Should generate SlashCommand() wildcards from inventory."""
        inventory_file = tmp_path / 'inventory.json'
        inventory_file.write_text(
            json.dumps(
                {
                    'bundles': [
                        {
                            'name': 'plan-marshall',
                            'skills': [],
                            'commands': [{'name': 'plan-manage'}, {'name': 'task-standalone'}],
                        }
                    ]
                }
            )
        )

        result = cmd_generate_wildcards(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'generate-wildcards',
                '--input',
                str(inventory_file),
            )
        )

        assert result['status'] == 'success'
        assert 'permissions' in result
        assert 'command_bundle_wildcards' in result['permissions']
        assert 'SlashCommand(/plan-marshall:*)' in result['permissions']['command_bundle_wildcards']

    def test_includes_statistics(self, tmp_path):
        """Should include statistics in output."""
        inventory_file = tmp_path / 'inventory.json'
        inventory_file.write_text(
            json.dumps(
                {'bundles': [{'name': 'test-bundle', 'skills': [{'name': 'skill1'}], 'commands': [{'name': 'cmd1'}]}]}
            )
        )

        result = cmd_generate_wildcards(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'generate-wildcards',
                '--input',
                str(inventory_file),
            )
        )

        assert result['status'] == 'success'
        assert 'statistics' in result
        assert 'bundles_scanned' in result['statistics']
