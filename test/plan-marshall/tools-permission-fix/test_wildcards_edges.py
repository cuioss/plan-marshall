#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Wildcards edges (carve 2 split)."""

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


class TestEnsureWildcardsApplied:
    """Test cmd_ensure_wildcards write path and its error branches."""

    def test_applies_and_writes(self, tmp_path):
        """Non-dry-run appends the missing wildcards to the settings file."""
        settings_file = tmp_path / 'settings.json'
        write_settings(settings_file, ['Bash(git:*)'])
        marketplace_file = tmp_path / 'marketplace.json'
        marketplace_file.write_text(json.dumps({'bundles': {'foo': {'skills': ['s'], 'commands': ['c']}}}))

        result = pf.cmd_ensure_wildcards(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'ensure-wildcards',
                '--settings',
                str(settings_file),
                '--marketplace-json',
                str(marketplace_file),
            )
        )

        assert result['status'] == 'success'
        assert result['applied'] is True
        allow = read_allow(settings_file)
        assert 'Skill(foo:*)' in allow
        assert 'SlashCommand(/foo:*)' in allow

    def test_error_on_missing_settings(self, tmp_path):
        """A missing settings file surfaces a structured error before reading the marketplace."""
        result = pf.cmd_ensure_wildcards(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'ensure-wildcards',
                '--settings',
                str(tmp_path / 'none.json'),
                '--marketplace-json',
                str(tmp_path / 'm.json'),
                '--dry-run',
            )
        )

        assert result['status'] == 'error'
        assert 'not found' in result['error']

    def test_error_on_missing_marketplace_file(self, tmp_path):
        """A missing marketplace.json surfaces a marketplace-not-found error."""
        settings_file = tmp_path / 'settings.json'
        write_settings(settings_file, [])

        result = pf.cmd_ensure_wildcards(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'ensure-wildcards',
                '--settings',
                str(settings_file),
                '--marketplace-json',
                str(tmp_path / 'missing.json'),
                '--dry-run',
            )
        )

        assert result['status'] == 'error'
        assert 'Marketplace file not found' in result['error']

    def test_error_on_invalid_marketplace_json(self, tmp_path):
        """Malformed marketplace JSON surfaces an invalid-JSON error."""
        settings_file = tmp_path / 'settings.json'
        write_settings(settings_file, [])
        marketplace_file = tmp_path / 'marketplace.json'
        marketplace_file.write_text('{not json')

        result = pf.cmd_ensure_wildcards(
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

        assert result['status'] == 'error'
        assert 'Invalid JSON' in result['error']

    def test_scope_project_resolves_settings_via_ops(self, tmp_path, monkeypatch):
        """ensure-wildcards accepts --scope, resolves through the permission ops, and
        WRITES through the resolved path — a --scope call must never fall back to a
        None settings path for the save.

        The single-file arm: only ``.claude/settings.json`` exists, so the read
        preference falls back to it. The dual-file arm — where the preference is
        actually observable — is ``TestSharedSeamCallSites``; keeping this one
        single-file is what makes the pair discriminate a preference from a
        hard-wired filename.
        """
        claude = tmp_path / '.claude'
        claude.mkdir(parents=True, exist_ok=True)
        settings_file = claude / 'settings.json'
        write_settings(settings_file, [])
        marketplace_file = tmp_path / 'marketplace.json'
        marketplace_file.write_text(json.dumps({'bundles': {'foo': {'skills': ['s'], 'commands': ['c']}}}))
        monkeypatch.chdir(tmp_path)

        result = pf.cmd_ensure_wildcards(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'ensure-wildcards',
                '--scope',
                'project',
                '--marketplace-json',
                str(marketplace_file),
            )
        )

        assert result['status'] == 'success'
        assert result['applied'] is True
        assert result['settings_path'] == str(settings_file)
        allow = read_allow(settings_file)
        assert 'Skill(foo:*)' in allow


class TestPrefixExtraction:
    """Test extract_command_prefix / extract_skill_prefix edge behavior."""

    def test_command_prefix_hyphenated(self):
        """A hyphenated command name yields its first segment."""
        assert pf.extract_command_prefix('plan-manage') == 'plan'

    def test_command_prefix_single_token(self):
        """A single-token command name is returned whole."""
        assert pf.extract_command_prefix('verify') == 'verify'

    def test_skill_prefix_single_token(self):
        """A single-token skill name is returned whole."""
        assert pf.extract_skill_prefix('planning') == 'planning'


class TestScanMarketplaceDirEdges:
    """Test scan_marketplace_dir error and fallback branches."""

    def test_invalid_marketplace_json(self, tmp_path):
        """A malformed marketplace.json surfaces an invalid-JSON error."""
        plugin_dir = tmp_path / '.claude-plugin'
        plugin_dir.mkdir(parents=True)
        (plugin_dir / 'marketplace.json').write_text('{broken')

        result = pf.scan_marketplace_dir(str(tmp_path))

        assert result['status'] == 'error'
        assert 'Invalid JSON' in result['error']

    def test_invalid_plugin_json_yields_empty_lists(self, tmp_path):
        """A bundle with malformed plugin.json contributes empty skills/commands."""
        plugin_dir = tmp_path / '.claude-plugin'
        plugin_dir.mkdir(parents=True)
        (plugin_dir / 'marketplace.json').write_text(json.dumps({'plugins': [{'name': 'b', 'source': './bundles/b'}]}))
        bundle_plugin = tmp_path / 'bundles' / 'b' / '.claude-plugin'
        bundle_plugin.mkdir(parents=True)
        (bundle_plugin / 'plugin.json').write_text('{not valid')

        result = pf.scan_marketplace_dir(str(tmp_path))

        bundle = result['bundles'][0]
        assert bundle['skills'] == []
        assert bundle['commands'] == []

    def test_bundle_without_source_resolves_default_path(self, tmp_path):
        """A plugin entry lacking 'source' resolves under bundles/<name>."""
        plugin_dir = tmp_path / '.claude-plugin'
        plugin_dir.mkdir(parents=True)
        (plugin_dir / 'marketplace.json').write_text(json.dumps({'plugins': [{'name': 'b'}]}))
        bundle_plugin = tmp_path / 'bundles' / 'b' / '.claude-plugin'
        bundle_plugin.mkdir(parents=True)
        (bundle_plugin / 'plugin.json').write_text(json.dumps({'skills': ['./skills/s.md'], 'commands': []}))

        result = pf.scan_marketplace_dir(str(tmp_path))

        bundle = result['bundles'][0]
        assert len(bundle['skills']) == 1


class TestGenerateWildcardsEdges:
    """Test cmd_generate_wildcards empty-inventory and input-error branches."""

    def test_empty_bundles_reports_error_field(self, tmp_path):
        """An inventory with no bundles reports the 'No bundles found' diagnostic."""
        inventory = tmp_path / 'inv.json'
        inventory.write_text(json.dumps({'bundles': []}))

        result = pf.cmd_generate_wildcards(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'generate-wildcards',
                '--input',
                str(inventory),
            )
        )

        assert result['status'] == 'success'
        assert result['error'] == 'No bundles found in inventory'
        assert result['statistics']['bundles_scanned'] == 0

    def test_missing_input_file_errors(self, tmp_path):
        """A non-existent input file surfaces an input-not-found error."""
        result = pf.cmd_generate_wildcards(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'generate-wildcards',
                '--input',
                str(tmp_path / 'nope.json'),
            )
        )

        assert result['status'] == 'error'
        assert 'Input file not found' in result['error']

    def test_invalid_input_json_errors(self, tmp_path):
        """A malformed input file surfaces an invalid-JSON error."""
        inventory = tmp_path / 'inv.json'
        inventory.write_text('{broken json')

        result = pf.cmd_generate_wildcards(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'generate-wildcards',
                '--input',
                str(inventory),
            )
        )

        assert result['status'] == 'error'
        assert 'Invalid JSON' in result['error']
