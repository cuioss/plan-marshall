#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Behavioral tests for permission_fix.py uncovered branches.

Complements ``test_permission_fix.py`` (which covers the happy-path dry-run and
subprocess plumbing) by exercising the write-applied paths, the error paths, and
the small pure helpers (normalization, wildcard generation, bundle-shape probes,
prefix extraction, inventory scanning) against synthetic ``tmp_path`` settings
files. The module is loaded in-process via ``load_script_module`` so coverage is
attributed; the WRITE-capable subcommands are driven only against tmp settings
copies (explicit ``--settings`` paths, or ``monkeypatch.chdir`` into ``tmp_path``
for the ``--target project`` resolvers) — never the developer's real settings.
"""

import json
from argparse import Namespace

from conftest import load_script_module

# Unique module name so the load is isolated and coverage is attributed to the
# permission_fix.py source file in this session.
pf = load_script_module('plan-marshall', 'tools-permission-fix', 'permission_fix.py', 'pf_behavior')


def _write_settings(path, allow):
    """Write a minimal settings.json with the given allow list."""
    path.write_text(json.dumps({'permissions': {'allow': allow, 'deny': [], 'ask': []}}))


def _read_allow(path):
    """Read back the allow list from a settings file."""
    return json.loads(path.read_text())['permissions']['allow']


# =============================================================================
# normalize_path_perm — pure helper
# =============================================================================


class TestNormalizePathPerm:
    """Test normalize_path_perm path normalization rules."""

    def test_trailing_slash_stripped_and_flagged(self):
        """A directory permission with a trailing slash is normalized and flagged changed."""
        # Arrange / Act
        result, changed = pf.normalize_path_perm('Read(src/)')

        # Assert
        assert result == 'Read(src)'
        assert changed is True

    def test_no_trailing_slash_unchanged(self):
        """A permission without a trailing slash is returned unchanged."""
        result, changed = pf.normalize_path_perm('Read(src)')

        assert result == 'Read(src)'
        assert changed is False

    def test_wildcard_with_trailing_slash_unchanged(self):
        """A wildcard path ending in '*' is left intact even with a trailing slash."""
        # path component ends with '*', so the trailing-slash rewrite is skipped.
        result, changed = pf.normalize_path_perm('Read(src/*/)')

        assert changed is False
        assert result == 'Read(src/*/)'

    def test_non_matching_format_returned_verbatim(self):
        """A string that does not match the permission shape is returned unchanged."""
        result, changed = pf.normalize_path_perm('not-a-permission')

        assert result == 'not-a-permission'
        assert changed is False


# =============================================================================
# apply-fixes — write-applied and error paths
# =============================================================================


class TestApplyFixesApplied:
    """Test cmd_apply_fixes write path and error path."""

    def test_applies_path_fix_and_writes_file(self, tmp_path):
        """Non-dry-run normalizes a trailing-slash path, writes, and reports applied."""
        # Arrange
        settings_file = tmp_path / 'settings.json'
        _write_settings(settings_file, ['Read(src/)', 'Bash(git:*)'])

        # Act
        result = pf.cmd_apply_fixes(Namespace(settings=str(settings_file), scope=None, dry_run=False))

        # Assert
        assert result['status'] == 'success'
        assert result['paths_fixed'] == 1
        assert result['applied'] is True
        allow = _read_allow(settings_file)
        assert 'Read(src)' in allow
        assert 'Read(src/)' not in allow

    def test_error_on_missing_settings_file(self, tmp_path):
        """A non-existent settings path surfaces a structured error."""
        result = pf.cmd_apply_fixes(
            Namespace(settings=str(tmp_path / 'nope.json'), scope=None, dry_run=False)
        )

        assert result['status'] == 'error'
        assert 'not found' in result['error']

    def test_no_changes_reports_not_applied(self, tmp_path):
        """An already-clean, already-sorted, default-complete file makes no changes."""
        settings_file = tmp_path / 'settings.json'
        # Pre-seed with all defaults + a sorted extra so nothing is added/sorted/fixed.
        _write_settings(
            settings_file,
            sorted(['Bash(git:*)', 'Edit(.plan/**)', 'Write(.plan/**)', 'Read(~/.claude/plugins/cache/**)']),
        )

        result = pf.cmd_apply_fixes(Namespace(settings=str(settings_file), scope=None, dry_run=False))

        assert result['status'] == 'success'
        assert result['changes_made'] is False
        assert result['applied'] is False


# =============================================================================
# resolve_settings_arg — fall-through branch
# =============================================================================


def test_resolve_settings_arg_falls_through_to_project(tmp_path, monkeypatch):
    """With neither --settings nor --scope, resolution defaults to the project path."""
    monkeypatch.chdir(tmp_path)

    resolved = pf.resolve_settings_arg(Namespace(settings=None, scope=None))

    assert '.claude' in resolved


# =============================================================================
# consolidate — timestamp/date parsing, wildcard generation, write path
# =============================================================================


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

    def test_empty_group_returns_empty_string(self):
        """An empty parsed group produces no wildcard."""
        assert pf.generate_wildcard([]) == ''

    def test_single_prefix_keeps_path(self):
        """A single shared path prefix is preserved verbatim in the wildcard."""
        group = [
            {'type': 'Read', 'base_name': 'build', 'extension': 'log', 'path_prefix': 'target/'},
            {'type': 'Read', 'base_name': 'build', 'extension': 'log', 'path_prefix': 'target/'},
        ]

        assert pf.generate_wildcard(group) == 'Read(target/build-*.log)'

    def test_multiple_prefixes_collapse_to_double_star(self):
        """Differing path prefixes collapse to a '**/' recursive wildcard."""
        group = [
            {'type': 'Read', 'base_name': 'build', 'extension': 'log', 'path_prefix': 'a/'},
            {'type': 'Read', 'base_name': 'build', 'extension': 'log', 'path_prefix': 'b/'},
        ]

        assert pf.generate_wildcard(group) == 'Read(**/build-*.log)'


class TestConsolidateApplied:
    """Test cmd_consolidate write path, date-only grouping, and error path."""

    def test_applies_consolidation_and_writes(self, tmp_path):
        """Non-dry-run removes timestamped entries, adds the wildcard, and writes the file."""
        # Arrange
        settings_file = tmp_path / 'settings.json'
        _write_settings(
            settings_file,
            [
                'Bash(git:*)',
                'Read(target/build-2025-11-20-174411.log)',
                'Read(target/build-2025-11-21-093000.log)',
            ],
        )

        # Act
        result = pf.cmd_consolidate(Namespace(settings=str(settings_file), scope=None, dry_run=False))

        # Assert
        assert result['status'] == 'success'
        assert result['applied'] is True
        assert result['consolidated'] == 2
        allow = _read_allow(settings_file)
        assert 'Read(target/build-*.log)' in allow
        assert 'Read(target/build-2025-11-20-174411.log)' not in allow
        assert 'Bash(git:*)' in allow

    def test_date_only_group_consolidated(self, tmp_path):
        """Two date-only-suffixed permissions in one group consolidate to a wildcard."""
        settings_file = tmp_path / 'settings.json'
        _write_settings(
            settings_file,
            ['Read(logs/app-2025-11-20.log)', 'Read(logs/app-2025-11-21.log)'],
        )

        result = pf.cmd_consolidate(Namespace(settings=str(settings_file), scope=None, dry_run=True))

        assert result['status'] == 'success'
        assert result['consolidated'] == 2
        assert 'Read(logs/app-*.log)' in result['wildcards_added']

    def test_error_on_missing_settings(self, tmp_path):
        """A non-existent settings path surfaces a structured error."""
        result = pf.cmd_consolidate(
            Namespace(settings=str(tmp_path / 'missing.json'), scope=None, dry_run=False)
        )

        assert result['status'] == 'error'
        assert 'not found' in result['error']


# =============================================================================
# has_skills / has_commands / generate_required_wildcards — bundle-shape probes
# =============================================================================


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


# =============================================================================
# ensure-wildcards — write path and error paths
# =============================================================================


class TestEnsureWildcardsApplied:
    """Test cmd_ensure_wildcards write path and its error branches."""

    def test_applies_and_writes(self, tmp_path):
        """Non-dry-run appends the missing wildcards to the settings file."""
        settings_file = tmp_path / 'settings.json'
        _write_settings(settings_file, ['Bash(git:*)'])
        marketplace_file = tmp_path / 'marketplace.json'
        marketplace_file.write_text(json.dumps({'bundles': {'foo': {'skills': ['s'], 'commands': ['c']}}}))

        result = pf.cmd_ensure_wildcards(
            Namespace(settings=str(settings_file), marketplace_json=str(marketplace_file), dry_run=False)
        )

        assert result['status'] == 'success'
        assert result['applied'] is True
        allow = _read_allow(settings_file)
        assert 'Skill(foo:*)' in allow
        assert 'SlashCommand(/foo:*)' in allow

    def test_error_on_missing_settings(self, tmp_path):
        """A missing settings file surfaces a structured error before reading the marketplace."""
        result = pf.cmd_ensure_wildcards(
            Namespace(settings=str(tmp_path / 'none.json'), marketplace_json=str(tmp_path / 'm.json'), dry_run=True)
        )

        assert result['status'] == 'error'
        assert 'not found' in result['error']

    def test_error_on_missing_marketplace_file(self, tmp_path):
        """A missing marketplace.json surfaces a marketplace-not-found error."""
        settings_file = tmp_path / 'settings.json'
        _write_settings(settings_file, [])

        result = pf.cmd_ensure_wildcards(
            Namespace(settings=str(settings_file), marketplace_json=str(tmp_path / 'missing.json'), dry_run=True)
        )

        assert result['status'] == 'error'
        assert 'Marketplace file not found' in result['error']

    def test_error_on_invalid_marketplace_json(self, tmp_path):
        """Malformed marketplace JSON surfaces an invalid-JSON error."""
        settings_file = tmp_path / 'settings.json'
        _write_settings(settings_file, [])
        marketplace_file = tmp_path / 'marketplace.json'
        marketplace_file.write_text('{not json')

        result = pf.cmd_ensure_wildcards(
            Namespace(settings=str(settings_file), marketplace_json=str(marketplace_file), dry_run=True)
        )

        assert result['status'] == 'error'
        assert 'Invalid JSON' in result['error']


# =============================================================================
# prefix extraction — single-token branch
# =============================================================================


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


# =============================================================================
# scan_marketplace_dir — JSON-error and no-source branches
# =============================================================================


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
        (plugin_dir / 'marketplace.json').write_text(
            json.dumps({'plugins': [{'name': 'b', 'source': './bundles/b'}]})
        )
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
        (bundle_plugin / 'plugin.json').write_text(
            json.dumps({'skills': ['./skills/s.md'], 'commands': []})
        )

        result = pf.scan_marketplace_dir(str(tmp_path))

        bundle = result['bundles'][0]
        assert len(bundle['skills']) == 1


# =============================================================================
# generate-wildcards — empty inventory and input error branches
# =============================================================================


class TestGenerateWildcardsEdges:
    """Test cmd_generate_wildcards empty-inventory and input-error branches."""

    def test_empty_bundles_reports_error_field(self, tmp_path):
        """An inventory with no bundles reports the 'No bundles found' diagnostic."""
        inventory = tmp_path / 'inv.json'
        inventory.write_text(json.dumps({'bundles': []}))

        result = pf.cmd_generate_wildcards(Namespace(input=str(inventory), marketplace_dir=None))

        assert result['status'] == 'success'
        assert result['error'] == 'No bundles found in inventory'
        assert result['statistics']['bundles_scanned'] == 0

    def test_missing_input_file_errors(self, tmp_path):
        """A non-existent input file surfaces an input-not-found error."""
        result = pf.cmd_generate_wildcards(
            Namespace(input=str(tmp_path / 'nope.json'), marketplace_dir=None)
        )

        assert result['status'] == 'error'
        assert 'Input file not found' in result['error']

    def test_invalid_input_json_errors(self, tmp_path):
        """A malformed input file surfaces an invalid-JSON error."""
        inventory = tmp_path / 'inv.json'
        inventory.write_text('{broken json')

        result = pf.cmd_generate_wildcards(Namespace(input=str(inventory), marketplace_dir=None))

        assert result['status'] == 'error'
        assert 'Invalid JSON' in result['error']


# =============================================================================
# ensure-executor / cleanup-scripts / migrate-executor — dry-run + extra branches
# =============================================================================


class TestExecutorSubcommandsInProcess:
    """Test executor-pattern subcommands against a chdir'd tmp project dir."""

    def _setup_project(self, tmp_path, allow):
        """Create tmp_path/.claude/settings.json and return its path."""
        claude_dir = tmp_path / '.claude'
        claude_dir.mkdir()
        settings_file = claude_dir / 'settings.json'
        _write_settings(settings_file, allow)
        return settings_file

    def test_ensure_executor_dry_run_would_add(self, tmp_path, monkeypatch):
        """Dry-run reports 'would_add' and leaves the file untouched."""
        settings_file = self._setup_project(tmp_path, ['Bash(git:*)'])
        monkeypatch.chdir(tmp_path)

        result = pf.cmd_ensure_executor(Namespace(target='project', dry_run=True))

        assert result['action'] == 'would_add'
        assert result['success'] is True
        assert pf.EXECUTOR_PERMISSION not in _read_allow(settings_file)

    def test_cleanup_scripts_nothing_to_remove(self, tmp_path, monkeypatch):
        """With no individual script perms, cleanup reports nothing to remove."""
        self._setup_project(tmp_path, ['Bash(git:*)'])
        monkeypatch.chdir(tmp_path)

        result = pf.cmd_cleanup_scripts(
            Namespace(target='project', remove_broad_python=False, dry_run=False)
        )

        assert result['action'] == 'nothing_to_remove'
        assert result['success'] is True

    def test_cleanup_scripts_dry_run_would_remove(self, tmp_path, monkeypatch):
        """Dry-run reports the would-remove count without modifying the file."""
        script_perm = 'Bash(python3 /x/marketplace/bundles/b/skills/s/scripts/run.py:*)'
        settings_file = self._setup_project(tmp_path, ['Bash(git:*)', script_perm])
        monkeypatch.chdir(tmp_path)

        result = pf.cmd_cleanup_scripts(
            Namespace(target='project', remove_broad_python=False, dry_run=True)
        )

        assert result['action'] == 'would_remove'
        assert result['total_would_remove'] == 1
        assert script_perm in _read_allow(settings_file)

    def test_cleanup_scripts_removes_broad_python(self, tmp_path, monkeypatch):
        """With --remove-broad-python the overly broad python wildcard is removed."""
        settings_file = self._setup_project(tmp_path, ['Bash(git:*)', pf.OVERLY_BROAD_PYTHON])
        monkeypatch.chdir(tmp_path)

        result = pf.cmd_cleanup_scripts(
            Namespace(target='project', remove_broad_python=True, dry_run=False)
        )

        assert result['success'] is True
        assert result['broad_python_removed'] is True
        assert pf.OVERLY_BROAD_PYTHON not in _read_allow(settings_file)

    def test_migrate_executor_dry_run(self, tmp_path, monkeypatch):
        """Dry-run reports planned would-add/would-remove without writing."""
        script_perm = 'Bash(python3 /x/marketplace/bundles/b/skills/s/scripts/run.py:*)'
        settings_file = self._setup_project(tmp_path, ['Bash(git:*)', script_perm])
        monkeypatch.chdir(tmp_path)

        result = pf.cmd_migrate_executor(
            Namespace(target='project', remove_broad_python=False, dry_run=True)
        )

        assert result['success'] is True
        assert result['executor']['action'] == 'would_add'
        assert result['cleanup']['individual_would_remove'] == 1
        # Dry-run leaves the file unchanged.
        assert pf.EXECUTOR_PERMISSION not in _read_allow(settings_file)

    def test_migrate_executor_executor_already_present_removes_broad_python(self, tmp_path, monkeypatch):
        """When the executor perm already exists, migration only cleans up extras."""
        settings_file = self._setup_project(
            tmp_path, ['Bash(git:*)', pf.EXECUTOR_PERMISSION, pf.OVERLY_BROAD_PYTHON]
        )
        monkeypatch.chdir(tmp_path)

        result = pf.cmd_migrate_executor(
            Namespace(target='project', remove_broad_python=True, dry_run=False)
        )

        assert result['success'] is True
        assert result['executor']['action'] == 'already_exists'
        allow = _read_allow(settings_file)
        assert pf.OVERLY_BROAD_PYTHON not in allow
        assert pf.EXECUTOR_PERMISSION in allow


# =============================================================================
# add / remove — in-process write paths against a chdir'd tmp project dir
# =============================================================================


class TestAddRemoveInProcess:
    """Test cmd_add / cmd_remove write and idempotent branches in-process."""

    def _setup_project(self, tmp_path, allow):
        claude_dir = tmp_path / '.claude'
        claude_dir.mkdir()
        settings_file = claude_dir / 'settings.json'
        _write_settings(settings_file, allow)
        return settings_file

    def test_add_writes_new_permission(self, tmp_path, monkeypatch):
        """Adding a new permission writes it and reports 'added'."""
        settings_file = self._setup_project(tmp_path, ['Bash(git:*)'])
        monkeypatch.chdir(tmp_path)

        result = pf.cmd_add(Namespace(permission='Bash(npm:*)', target='project'))

        assert result['action'] == 'added'
        assert result['success'] is True
        assert 'Bash(npm:*)' in _read_allow(settings_file)

    def test_add_existing_is_noop(self, tmp_path, monkeypatch):
        """Adding an existing permission reports 'already_exists'."""
        self._setup_project(tmp_path, ['Bash(git:*)'])
        monkeypatch.chdir(tmp_path)

        result = pf.cmd_add(Namespace(permission='Bash(git:*)', target='project'))

        assert result['action'] == 'already_exists'

    def test_remove_deletes_permission(self, tmp_path, monkeypatch):
        """Removing an existing permission deletes it and reports 'removed'."""
        settings_file = self._setup_project(tmp_path, ['Bash(git:*)', 'Bash(npm:*)'])
        monkeypatch.chdir(tmp_path)

        result = pf.cmd_remove(Namespace(permission='Bash(npm:*)', target='project'))

        assert result['action'] == 'removed'
        assert 'Bash(npm:*)' not in _read_allow(settings_file)

    def test_remove_absent_is_noop(self, tmp_path, monkeypatch):
        """Removing a missing permission reports 'not_found'."""
        self._setup_project(tmp_path, ['Bash(git:*)'])
        monkeypatch.chdir(tmp_path)

        result = pf.cmd_remove(Namespace(permission='Bash(absent:*)', target='project'))

        assert result['action'] == 'not_found'


# =============================================================================
# remove-redundant — scope resolution and error branches
# =============================================================================


class TestRemoveRedundantErrors:
    """Test cmd_remove_redundant error branches that the happy-path suite omits."""

    def test_global_load_error(self, tmp_path):
        """A missing global settings file surfaces a structured error."""
        local_file = tmp_path / 'local.json'
        _write_settings(local_file, ['Bash(git:*)'])

        result = pf.cmd_remove_redundant(
            Namespace(
                scope=None,
                global_settings=str(tmp_path / 'missing-global.json'),
                local_settings=str(local_file),
                move_marketplace=True,
                dry_run=False,
            )
        )

        assert result['status'] == 'error'
        assert 'not found' in result['error']

    def test_local_load_error(self, tmp_path):
        """A missing local settings file surfaces a structured error."""
        global_file = tmp_path / 'global.json'
        _write_settings(global_file, ['Bash(git:*)'])

        result = pf.cmd_remove_redundant(
            Namespace(
                scope=None,
                global_settings=str(global_file),
                local_settings=str(tmp_path / 'missing-local.json'),
                move_marketplace=True,
                dry_run=False,
            )
        )

        assert result['status'] == 'error'


# =============================================================================
# apply-project-step-permissions — error branches
# =============================================================================


class TestApplyProjectStepPermissionsErrors:
    """Test cmd_apply_project_step_permissions error branches."""

    def test_marshal_load_error(self, tmp_path):
        """A missing marshal.json surfaces a structured error."""
        settings_file = tmp_path / 'settings.json'
        _write_settings(settings_file, [])

        result = pf.cmd_apply_project_step_permissions(
            Namespace(marshal=str(tmp_path / 'missing.json'), settings=str(settings_file), dry_run=True)
        )

        assert result['status'] == 'error'

    def test_settings_load_error(self, tmp_path):
        """A missing settings file surfaces a structured error after marshal loads."""
        marshal_file = tmp_path / 'marshal.json'
        marshal_file.write_text(json.dumps({'plan': {'phase-6-finalize': {'steps': []}}}))

        result = pf.cmd_apply_project_step_permissions(
            Namespace(marshal=str(marshal_file), settings=str(tmp_path / 'missing.json'), dry_run=True)
        )

        assert result['status'] == 'error'
