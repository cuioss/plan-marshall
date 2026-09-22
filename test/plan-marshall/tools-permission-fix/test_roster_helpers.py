#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Roster + parse helpers (carve 2 split)."""

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


class TestParseTimestampedPermission:
    """Test parse_timestamped_permission across its three branches."""

    def test_full_timestamp_parsed(self):
        """A YYYY-MM-DD-HHMMSS suffix parses via the timestamp pattern."""
        parsed = pf.parse_timestamped_permission('Read(target/build-2025-11-20-174411.log)')

        assert parsed is not None
        assert parsed['base_name'] == 'build'
        assert parsed['extension'] == 'log'
        assert parsed['path_prefix'] == 'target/'

    def test_date_only_parsed(self):
        """A date-only YYYY-MM-DD suffix parses via the date pattern."""
        parsed = pf.parse_timestamped_permission('Read(logs/app-2025-11-20.log)')

        assert parsed is not None
        assert parsed['base_name'] == 'app'
        assert parsed['timestamp'] == '2025-11-20'

    def test_non_timestamped_returns_none(self):
        """A plain permission with no timestamp returns None."""
        assert pf.parse_timestamped_permission('Bash(git:*)') is None


class TestGenerateWildcard:
    """Test generate_wildcard prefix collapsing."""

    @pytest.mark.parametrize(
        ('group', 'expected'),
        [
            ([], ''),
            (
                [
                    {'type': 'Read', 'base_name': 'build', 'extension': 'log', 'path_prefix': 'target/'},
                    {'type': 'Read', 'base_name': 'build', 'extension': 'log', 'path_prefix': 'target/'},
                ],
                'Read(target/build-*.log)',
            ),
            (
                [
                    {'type': 'Read', 'base_name': 'build', 'extension': 'log', 'path_prefix': 'a/'},
                    {'type': 'Read', 'base_name': 'build', 'extension': 'log', 'path_prefix': 'b/'},
                ],
                'Read(**/build-*.log)',
            ),
        ],
        ids=[
            'an-empty-group-produces-no-wildcard',
            'one-shared-prefix-is-preserved-verbatim',
            'differing-prefixes-collapse-to-a-recursive-double-star',
        ],
    )
    def test_generate_wildcard(self, group, expected):
        """How many distinct path prefixes the group carries decides the emitted path."""
        assert pf.generate_wildcard(group) == expected


class TestConsolidateApplied:
    """Test cmd_consolidate write path, date-only grouping, and error path."""

    def test_applies_consolidation_and_writes(self, tmp_path):
        """Non-dry-run removes timestamped entries, adds the wildcard, and writes the file."""
        # Arrange
        settings_file = tmp_path / 'settings.json'
        write_settings(
            settings_file,
            [
                'Bash(git:*)',
                'Read(target/build-2025-11-20-174411.log)',
                'Read(target/build-2025-11-21-093000.log)',
            ],
        )

        # Act
        result = pf.cmd_consolidate(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'consolidate',
                '--settings',
                str(settings_file),
            )
        )

        # Assert
        assert result['status'] == 'success'
        assert result['applied'] is True
        assert result['consolidated'] == 2
        allow = read_allow(settings_file)
        assert 'Read(target/build-*.log)' in allow
        assert 'Read(target/build-2025-11-20-174411.log)' not in allow
        assert 'Bash(git:*)' in allow

    def test_date_only_group_consolidated(self, tmp_path):
        """Two date-only-suffixed permissions in one group consolidate to a wildcard."""
        settings_file = tmp_path / 'settings.json'
        write_settings(
            settings_file,
            ['Read(logs/app-2025-11-20.log)', 'Read(logs/app-2025-11-21.log)'],
        )

        result = pf.cmd_consolidate(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'consolidate',
                '--settings',
                str(settings_file),
                '--dry-run',
            )
        )

        assert result['status'] == 'success'
        assert result['consolidated'] == 2
        assert 'Read(logs/app-*.log)' in result['wildcards_added']

    def test_error_on_missing_settings(self, tmp_path):
        """A non-existent settings path surfaces a structured error."""
        result = pf.cmd_consolidate(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'consolidate',
                '--settings',
                str(tmp_path / 'missing.json'),
            )
        )

        assert result['status'] == 'error'
        assert 'not found' in result['error']


class TestBundleShapeProbes:
    """Test the marketplace bundle-shape predicate helpers."""

    def test_has_skills_empty_list_is_false(self):
        """An explicit empty skills list means the bundle has no skills."""
        assert pf.has_skills({'skills': []}) is False

    def test_has_skills_none_with_commands_present_is_false(self):
        """Skills absent but commands present means skills are genuinely absent."""
        assert pf.has_skills({'commands': ['c']}) is False

    def test_has_skills_both_absent_assumes_present(self):
        """When neither key exists, the real marketplace.json shape assumes skills."""
        assert pf.has_skills({}) is True

    def test_has_commands_empty_list_is_false(self):
        """An explicit empty commands list means the bundle has no commands."""
        assert pf.has_commands({'commands': []}) is False

    def test_has_commands_none_with_skills_present_is_false(self):
        """Commands absent but skills present means commands are genuinely absent."""
        assert pf.has_commands({'skills': ['s']}) is False

    def test_generate_required_wildcards_skips_blank_bundle_name(self):
        """A blank bundle name is skipped while real bundles still produce wildcards."""
        marketplace = {'bundles': {'': {'skills': ['s']}, 'foo': {'skills': ['s'], 'commands': ['c']}}}

        wildcards = pf.generate_required_wildcards(marketplace)

        assert 'Skill(foo:*)' in wildcards
        assert 'SlashCommand(/foo:*)' in wildcards
        assert not any(w.startswith('Skill(:') for w in wildcards)
