#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Consolidate + apply-fixes (carve 2 split)."""

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


class TestConsolidate:
    """Test permission_fix.py consolidate subcommand via direct import."""

    def test_detect_timestamped_build_output(self, tmp_path):
        """Should detect permissions with timestamp patterns."""
        settings_file = tmp_path / 'settings.json'
        settings_file.write_text(
            json.dumps(
                {
                    'permissions': {
                        'allow': [
                            'Bash(git:*)',
                            'Read(target/build-output-2025-11-20-174411.log)',
                            'Read(target/build-output-2025-11-21-093000.log)',
                            'Read(target/build-output-2025-11-22-120000.log)',
                        ],
                        'deny': [],
                        'ask': [],
                    }
                }
            )
        )

        result = cmd_consolidate(
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
        assert 'consolidated' in result
        assert result['consolidated'] == 3

    def test_generates_correct_wildcard(self, tmp_path):
        """Should generate correct wildcard pattern."""
        settings_file = tmp_path / 'settings.json'
        settings_file.write_text(
            json.dumps(
                {
                    'permissions': {
                        'allow': [
                            'Read(target/build-output-2025-11-20-174411.log)',
                            'Read(target/build-output-2025-11-21-093000.log)',
                        ],
                        'deny': [],
                        'ask': [],
                    }
                }
            )
        )

        result = cmd_consolidate(
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
        assert 'wildcards_added' in result
        assert 'Read(target/build-output-*.log)' in result['wildcards_added']

    def test_dry_run_does_not_modify_file(self, tmp_path):
        """Dry-run should not modify the settings file."""
        original_content = json.dumps(
            {'permissions': {'allow': ['Read(target/build-output-2025-11-20-174411.log)'], 'deny': [], 'ask': []}}
        )

        settings_file = tmp_path / 'settings.json'
        settings_file.write_text(original_content)

        cmd_consolidate(
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

        assert settings_file.read_text() == original_content


class TestApplyFixes:
    """Test permission_fix.py apply-fixes subcommand via direct import."""

    def test_removes_duplicates(self, tmp_path):
        """Should remove duplicate permissions."""
        settings_file = tmp_path / 'settings.json'
        settings_file.write_text(
            json.dumps({'permissions': {'allow': ['Bash(git:*)', 'Bash(git:*)', 'Bash(npm:*)'], 'deny': [], 'ask': []}})
        )

        result = cmd_apply_fixes(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'apply-fixes',
                '--settings',
                str(settings_file),
                '--dry-run',
            )
        )

        assert result['status'] == 'success'
        assert 'duplicates_removed' in result
        assert result['duplicates_removed'] == 1

    def test_sorts_permissions(self, tmp_path):
        """Should sort permissions alphabetically."""
        settings_file = tmp_path / 'settings.json'
        settings_file.write_text(
            json.dumps({'permissions': {'allow': ['Write(**)', 'Bash(git:*)', 'Edit(**)'], 'deny': [], 'ask': []}})
        )

        result = cmd_apply_fixes(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'apply-fixes',
                '--settings',
                str(settings_file),
                '--dry-run',
            )
        )

        assert result['status'] == 'success'
        assert 'sorted' in result
        assert result['sorted']

    def test_adds_default_permissions(self, tmp_path):
        """Should report the defaults it added, by semantic id.

        The ids are what the runtime hands back: the permission grammar itself
        is rendered inside the runtime and never reaches this script, so a
        caller cannot come to depend on one target's permission-string format.
        """
        settings_file = tmp_path / 'settings.json'
        settings_file.write_text(json.dumps({'permissions': {'allow': ['Bash(git:*)'], 'deny': [], 'ask': []}}))

        result = cmd_apply_fixes(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'apply-fixes',
                '--settings',
                str(settings_file),
                '--dry-run',
            )
        )

        assert result['status'] == 'success'
        assert result['defaults_added'] == ['plan-dir-edit', 'bundle-cache-read']
        assert result['defaults_added_count'] == 2

    def test_dry_run_writes_nothing(self, tmp_path):
        """--dry-run must leave the settings file byte-identical.

        The write decision lives inside ``ensure_default_permissions`` rather
        than in this script, so nothing here would notice that guard being
        dropped. The seeded file is deliberately un-normalized — duplicated,
        unsorted, and missing every default — so the run has work in each of
        the three fixes and a written file could not coincide with the input.
        """
        settings_file = tmp_path / 'settings.json'
        settings_file.write_text(
            json.dumps({'permissions': {'allow': ['Write(**)', 'Bash(git:*)', 'Bash(git:*)'], 'deny': [], 'ask': []}})
        )
        before = settings_file.read_bytes()

        result = cmd_apply_fixes(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'apply-fixes',
                '--settings',
                str(settings_file),
                '--dry-run',
            )
        )

        assert result['status'] == 'success'
        # The run had all three kinds of work to do — otherwise "unchanged"
        # would be true for a writing implementation too.
        assert result['duplicates_removed'] == 1
        assert result['sorted']
        assert result['defaults_added']
        assert settings_file.read_bytes() == before

    def test_written_default_set_is_the_pinned_two_rules(self, tmp_path):
        """The FILE apply-fixes leaves behind must carry the same two rules.

        What an operator's settings end up containing is the observable
        contract, and it is pinned here against literals rather than against the
        renderer, which would agree with itself whatever it emitted.
        """
        settings_file = tmp_path / 'settings.json'
        settings_file.write_text(json.dumps({'permissions': {'allow': [], 'deny': [], 'ask': []}}))

        result = cmd_apply_fixes(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'apply-fixes',
                '--settings',
                str(settings_file),
            )
        )

        assert result['applied'] is True
        written = json.loads(settings_file.read_text())
        assert written['permissions']['allow'] == sorted(['Edit(.plan/**)', 'Read(~/.claude/plugins/cache/**)'])

    def test_prunes_a_retired_default_at_the_command_layer(self, tmp_path):
        """The retirement must reach an operator through THIS command, not only the runtime.

        The runtime-layer pin lives in
        ``test_permission_rendering_defaults.py``; without this one, deleting
        the ``defaults_removed`` plumbing from ``cmd_apply_fixes`` — the fields
        in the result dict, or the ``was_sorted`` forcing that makes a
        prune-only run count as a change — passes the whole suite while the
        operator-visible half of the fix silently stops working.

        The seed is otherwise default-complete and already sorted, so pruning
        is the ONLY work in the run.
        """
        settings_file = tmp_path / 'settings.json'
        settings_file.write_text(
            json.dumps(
                {
                    'permissions': {
                        'allow': sorted(
                            [
                                'Edit(.plan/**)',
                                'Read(~/.claude/plugins/cache/**)',
                                'Write(.plan/**)',
                            ]
                        ),
                        'deny': [],
                        'ask': [],
                    }
                }
            )
        )

        result = cmd_apply_fixes(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'apply-fixes',
                '--settings',
                str(settings_file),
            )
        )

        assert result['defaults_added'] == []
        assert result['defaults_removed'] == ['plan-dir-write']
        assert result['defaults_removed_count'] == 1
        assert result['changes_made'] is True
        assert result['applied'] is True
        written = json.loads(settings_file.read_text())
        assert written['permissions']['allow'] == sorted(['Edit(.plan/**)', 'Read(~/.claude/plugins/cache/**)'])

    def test_dry_run_prunes_nothing_on_disk_at_the_command_layer(self, tmp_path):
        """--dry-run must report the prune it WOULD do and leave the file alone."""
        settings_file = tmp_path / 'settings.json'
        settings_file.write_text(json.dumps({'permissions': {'allow': ['Write(.plan/**)'], 'deny': [], 'ask': []}}))
        before = settings_file.read_bytes()

        result = cmd_apply_fixes(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'apply-fixes',
                '--settings',
                str(settings_file),
                '--dry-run',
            )
        )

        assert result['defaults_removed'] == ['plan-dir-write']
        assert result['applied'] is False
        assert settings_file.read_bytes() == before

    def test_normalize_only_change_still_writes(self, tmp_path):
        """A run that adds no default must still persist the normalization.

        The runtime writes when it adds a default; when it adds none, the save
        below is the only write, and dropping it would silently discard a
        dedupe/sort.
        """
        settings_file = tmp_path / 'settings.json'
        settings_file.write_text(
            json.dumps(
                {
                    'permissions': {
                        'allow': [
                            'Edit(.plan/**)',
                            'Read(~/.claude/plugins/cache/**)',
                            'Bash(git:*)',
                            'Bash(git:*)',
                        ],
                        'deny': [],
                        'ask': [],
                    }
                }
            )
        )

        result = cmd_apply_fixes(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'apply-fixes',
                '--settings',
                str(settings_file),
            )
        )

        assert result['defaults_added'] == []
        assert result['duplicates_removed'] == 1
        assert result['applied'] is True
        written = json.loads(settings_file.read_text())
        assert written['permissions']['allow'].count('Bash(git:*)') == 1
