#!/usr/bin/env python3
"""
Tests for the permission_fix.py script.

Tests subcommands:
- apply-fixes: Apply safe permission fixes (dedup, sort, defaults)
- add: Add a permission to settings
- remove: Remove a permission from settings
- ensure: Ensure multiple permissions exist
- consolidate: Consolidate timestamped build output permissions
- ensure-wildcards: Ensure marketplace wildcards exist in settings
- generate-wildcards: Generate permission wildcards from marketplace inventory
- ensure-executor: Ensure the executor permission exists
- cleanup-scripts: Remove redundant individual script permissions
- migrate-executor: Full migration to executor-only permission pattern

Tier 2 (direct import) for cmd_* functions with explicit file paths.
Tier 3 (subprocess) retained for CLI plumbing, --scope, and --target tests.
"""

import json
from argparse import Namespace

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import MARKETPLACE_ROOT, run_script

# Script path for remaining subprocess (CLI plumbing) tests
SCRIPT_PATH = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'tools-permission-fix' / 'scripts' / 'permission_fix.py'

# Tier 2 direct imports
from permission_fix import (  # type: ignore[import-not-found]  # noqa: E402
    cmd_apply_fixes,
    cmd_apply_project_step_permissions,
    cmd_consolidate,
    cmd_ensure_wildcards,
    cmd_generate_wildcards,
    cmd_remove_redundant,
    scan_marketplace_dir,
)

# =============================================================================
# Tier 2: Tests for consolidate subcommand
# =============================================================================


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

        result = cmd_consolidate(Namespace(settings=str(settings_file), scope=None, dry_run=True))

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

        result = cmd_consolidate(Namespace(settings=str(settings_file), scope=None, dry_run=True))

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

        cmd_consolidate(Namespace(settings=str(settings_file), scope=None, dry_run=True))

        assert settings_file.read_text() == original_content


# =============================================================================
# Tier 2: Tests for ensure-wildcards subcommand
# =============================================================================


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
            Namespace(settings=str(settings_file), marketplace_json=str(marketplace_file), dry_run=True)
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
            Namespace(settings=str(settings_file), marketplace_json=str(marketplace_file), dry_run=True)
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
            Namespace(settings=str(settings_file), marketplace_json=str(marketplace_file), dry_run=True)
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
            Namespace(settings=str(settings_file), marketplace_json=str(marketplace_file), dry_run=True)
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


# =============================================================================
# Tier 2: Tests for apply-fixes subcommand
# =============================================================================


class TestApplyFixes:
    """Test permission_fix.py apply-fixes subcommand via direct import."""

    def test_removes_duplicates(self, tmp_path):
        """Should remove duplicate permissions."""
        settings_file = tmp_path / 'settings.json'
        settings_file.write_text(
            json.dumps({'permissions': {'allow': ['Bash(git:*)', 'Bash(git:*)', 'Bash(npm:*)'], 'deny': [], 'ask': []}})
        )

        result = cmd_apply_fixes(Namespace(settings=str(settings_file), scope=None, dry_run=True))

        assert result['status'] == 'success'
        assert 'duplicates_removed' in result
        assert result['duplicates_removed'] == 1

    def test_sorts_permissions(self, tmp_path):
        """Should sort permissions alphabetically."""
        settings_file = tmp_path / 'settings.json'
        settings_file.write_text(
            json.dumps({'permissions': {'allow': ['Write(**)', 'Bash(git:*)', 'Edit(**)'], 'deny': [], 'ask': []}})
        )

        result = cmd_apply_fixes(Namespace(settings=str(settings_file), scope=None, dry_run=True))

        assert result['status'] == 'success'
        assert 'sorted' in result
        assert result['sorted']

    def test_adds_default_permissions(self, tmp_path):
        """Should add default permissions if missing."""
        settings_file = tmp_path / 'settings.json'
        settings_file.write_text(json.dumps({'permissions': {'allow': ['Bash(git:*)'], 'deny': [], 'ask': []}}))

        result = cmd_apply_fixes(Namespace(settings=str(settings_file), scope=None, dry_run=True))

        assert result['status'] == 'success'
        assert 'defaults_added' in result
        defaults = result['defaults_added']
        assert 'Edit(.plan/**)' in defaults
        assert 'Write(.plan/**)' in defaults
        assert 'Read(~/.claude/plugins/cache/**)' in defaults


# =============================================================================
# Tier 2: Tests for remove-redundant subcommand
# =============================================================================


class TestRemoveRedundant:
    """Test permission_fix.py remove-redundant subcommand via direct import."""

    def _write_settings(self, path, allow: list[str]) -> None:
        path.write_text(json.dumps({'permissions': {'allow': allow, 'deny': [], 'ask': []}}))

    def _read_allow(self, path) -> list[str]:
        return json.loads(path.read_text())['permissions']['allow']

    def test_dry_run_removes_nothing(self, tmp_path):
        """Dry-run should not modify any settings file."""
        global_file = tmp_path / 'global_settings.json'
        local_file = tmp_path / 'local_settings.json'
        self._write_settings(global_file, ['Bash(git:*)', 'Bash(npm:*)'])
        self._write_settings(local_file, ['Bash(git:*)', 'Bash(npm:*)'])

        result = cmd_remove_redundant(
            Namespace(
                scope=None,
                global_settings=str(global_file),
                local_settings=str(local_file),
                move_marketplace=True,
                dry_run=True,
            )
        )

        assert result['status'] == 'success'
        assert result['dry_run']
        assert not result['applied']
        # Files should be unchanged
        assert self._read_allow(local_file) == ['Bash(git:*)', 'Bash(npm:*)']

    def test_removes_exact_duplicates_from_local(self, tmp_path):
        """Should remove permissions from local that are exact duplicates in global."""
        global_file = tmp_path / 'global_settings.json'
        local_file = tmp_path / 'local_settings.json'
        self._write_settings(global_file, ['Bash(git:*)', 'Bash(npm:*)'])
        self._write_settings(local_file, ['Bash(git:*)', 'Edit(.plan/**)'])

        result = cmd_remove_redundant(
            Namespace(
                scope=None,
                global_settings=str(global_file),
                local_settings=str(local_file),
                move_marketplace=False,
                dry_run=False,
            )
        )

        assert result['status'] == 'success'
        assert result['applied']
        assert 'Bash(git:*)' in result['removed_redundant']
        local_allow = self._read_allow(local_file)
        assert 'Bash(git:*)' not in local_allow
        assert 'Edit(.plan/**)' in local_allow

    def test_moves_marketplace_permissions_to_global(self, tmp_path):
        """Should move Skill() and SlashCommand() perms from local to global."""
        global_file = tmp_path / 'global_settings.json'
        local_file = tmp_path / 'local_settings.json'
        self._write_settings(global_file, ['Bash(git:*)'])
        self._write_settings(local_file, ['Bash(git:*)', 'Skill(pm-dev-java:*)', 'Edit(.plan/**)'])

        result = cmd_remove_redundant(
            Namespace(
                scope=None,
                global_settings=str(global_file),
                local_settings=str(local_file),
                move_marketplace=True,
                dry_run=False,
            )
        )

        assert result['status'] == 'success'
        assert result['applied']
        # Exact duplicate removed from local
        assert 'Bash(git:*)' in result['removed_redundant']
        # Marketplace perm moved to global
        assert 'Skill(pm-dev-java:*)' in result['moved_to_global']
        local_allow = self._read_allow(local_file)
        assert 'Skill(pm-dev-java:*)' not in local_allow
        global_allow = self._read_allow(global_file)
        assert 'Skill(pm-dev-java:*)' in global_allow

    def test_no_move_marketplace_skips_marketplace_perms(self, tmp_path):
        """--no-move-marketplace should leave marketplace permissions in local."""
        global_file = tmp_path / 'global_settings.json'
        local_file = tmp_path / 'local_settings.json'
        self._write_settings(global_file, ['Bash(git:*)'])
        self._write_settings(local_file, ['Bash(git:*)', 'Skill(pm-dev-java:*)'])

        result = cmd_remove_redundant(
            Namespace(
                scope=None,
                global_settings=str(global_file),
                local_settings=str(local_file),
                move_marketplace=False,
                dry_run=False,
            )
        )

        assert result['status'] == 'success'
        assert result['moved_to_global'] == []
        local_allow = self._read_allow(local_file)
        assert 'Skill(pm-dev-java:*)' in local_allow

    def test_already_in_global_removes_from_local_without_duplicate(self, tmp_path):
        """Marketplace perm already in global: remove from local, not re-added to global."""
        global_file = tmp_path / 'global_settings.json'
        local_file = tmp_path / 'local_settings.json'
        self._write_settings(global_file, ['Bash(git:*)', 'Skill(pm-dev-java:*)'])
        self._write_settings(local_file, ['Skill(pm-dev-java:*)'])

        result = cmd_remove_redundant(
            Namespace(
                scope=None,
                global_settings=str(global_file),
                local_settings=str(local_file),
                move_marketplace=True,
                dry_run=False,
            )
        )

        assert result['status'] == 'success'
        local_allow = self._read_allow(local_file)
        assert 'Skill(pm-dev-java:*)' not in local_allow
        # Not duplicated in global
        global_allow = self._read_allow(global_file)
        assert global_allow.count('Skill(pm-dev-java:*)') == 1

    def test_no_changes_when_already_clean(self, tmp_path):
        """Should report no changes when local has no redundancies."""
        global_file = tmp_path / 'global_settings.json'
        local_file = tmp_path / 'local_settings.json'
        self._write_settings(global_file, ['Bash(git:*)'])
        self._write_settings(local_file, ['Edit(.plan/**)', 'Write(.plan/**)'])

        result = cmd_remove_redundant(
            Namespace(
                scope=None,
                global_settings=str(global_file),
                local_settings=str(local_file),
                move_marketplace=True,
                dry_run=False,
            )
        )

        assert result['status'] == 'success'
        assert not result['changes_made']
        assert not result['applied']


# =============================================================================
# Tier 2: Tests for generate-wildcards subcommand
# =============================================================================


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

        result = cmd_generate_wildcards(Namespace(input=str(inventory_file), marketplace_dir=None))

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

        result = cmd_generate_wildcards(Namespace(input=str(inventory_file), marketplace_dir=None))

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

        result = cmd_generate_wildcards(Namespace(input=str(inventory_file), marketplace_dir=None))

        assert result['status'] == 'success'
        assert 'statistics' in result
        assert 'bundles_scanned' in result['statistics']


# =============================================================================
# Tier 2: Tests for scan_marketplace_dir and generate-wildcards --marketplace-dir
# =============================================================================


class TestScanMarketplaceDir:
    """Test scan_marketplace_dir function and generate-wildcards --marketplace-dir."""

    def _create_marketplace(self, tmp_path, bundles: dict[str, dict]) -> str:
        """Create a marketplace directory structure for testing.

        Args:
            tmp_path: Pytest tmp_path fixture
            bundles: dict of bundle_name -> {skills: [...], commands: [...]}

        Returns:
            Path to marketplace directory.
        """
        marketplace_dir = tmp_path / 'marketplace'
        plugin_dir = marketplace_dir / '.claude-plugin'
        plugin_dir.mkdir(parents=True)

        plugins = []
        for name, data in bundles.items():
            bundle_dir = marketplace_dir / 'bundles' / name
            bundle_plugin_dir = bundle_dir / '.claude-plugin'
            bundle_plugin_dir.mkdir(parents=True)

            plugin_json = {
                'name': name,
                'skills': data.get('skills', []),
                'commands': data.get('commands', []),
            }
            (bundle_plugin_dir / 'plugin.json').write_text(json.dumps(plugin_json))
            plugins.append({'name': name, 'source': f'./bundles/{name}'})

        marketplace_json = {'plugins': plugins}
        (plugin_dir / 'marketplace.json').write_text(json.dumps(marketplace_json))
        return str(marketplace_dir)

    def test_scans_bundles_with_skills_and_commands(self, tmp_path):
        """Should discover skills and commands from plugin.json files."""
        mkt_dir = self._create_marketplace(
            tmp_path,
            {
                'my-bundle': {
                    'skills': ['./skills/skill-a', './skills/skill-b'],
                    'commands': ['./commands/cmd-x.md'],
                },
            },
        )

        result = scan_marketplace_dir(mkt_dir)

        assert len(result['bundles']) == 1
        bundle = result['bundles'][0]
        assert bundle['name'] == 'my-bundle'
        assert len(bundle['skills']) == 2
        assert len(bundle['commands']) == 1

    def test_returns_error_for_missing_marketplace_json(self, tmp_path):
        """Should return error when marketplace.json is missing."""
        result = scan_marketplace_dir(str(tmp_path / 'nonexistent'))

        assert result['status'] == 'error'
        assert 'marketplace.json not found' in result['error']

    def test_handles_bundle_without_plugin_json(self, tmp_path):
        """Should return empty skills/commands for bundles missing plugin.json."""
        marketplace_dir = tmp_path / 'marketplace'
        plugin_dir = marketplace_dir / '.claude-plugin'
        plugin_dir.mkdir(parents=True)

        # Bundle dir exists but no plugin.json
        bundle_dir = marketplace_dir / 'bundles' / 'empty-bundle'
        bundle_dir.mkdir(parents=True)

        marketplace_json = {'plugins': [{'name': 'empty-bundle', 'source': './bundles/empty-bundle'}]}
        (plugin_dir / 'marketplace.json').write_text(json.dumps(marketplace_json))

        result = scan_marketplace_dir(str(marketplace_dir))

        assert len(result['bundles']) == 1
        bundle = result['bundles'][0]
        assert bundle['skills'] == []
        assert bundle['commands'] == []

    def test_statistics_counts(self, tmp_path):
        """Should compute correct statistics from scanned bundles."""
        mkt_dir = self._create_marketplace(
            tmp_path,
            {
                'bundle-a': {
                    'skills': ['./skills/s1', './skills/s2'],
                    'commands': ['./commands/c1.md'],
                },
                'bundle-b': {
                    'skills': ['./skills/s3'],
                    'commands': [],
                },
            },
        )

        result = scan_marketplace_dir(mkt_dir)

        stats = result['statistics']
        assert stats['total_bundles'] == 2
        assert stats['total_skills'] == 3
        assert stats['total_commands'] == 1

    def test_generate_wildcards_from_marketplace_dir(self, tmp_path):
        """generate-wildcards --marketplace-dir should produce wildcards."""
        mkt_dir = self._create_marketplace(
            tmp_path,
            {
                'plan-marshall': {
                    'skills': ['./skills/manage-status'],
                    'commands': ['./commands/plan-manage.md'],
                },
                'pm-dev-java': {
                    'skills': ['./skills/java-core'],
                    'commands': [],
                },
            },
        )

        result = cmd_generate_wildcards(Namespace(marketplace_dir=mkt_dir, input=None))

        assert result['status'] == 'success'
        skill_wildcards = result['permissions']['skill_wildcards']
        cmd_wildcards = result['permissions']['command_bundle_wildcards']
        assert 'Skill(plan-marshall:*)' in skill_wildcards
        assert 'Skill(pm-dev-java:*)' in cmd_wildcards + skill_wildcards
        assert 'SlashCommand(/plan-marshall:*)' in cmd_wildcards

    def test_generate_wildcards_marketplace_dir_error(self):
        """generate-wildcards --marketplace-dir with bad path should return error."""
        result = cmd_generate_wildcards(Namespace(marketplace_dir='/nonexistent/path', input=None))

        assert result['status'] == 'error'
        assert 'marketplace.json not found' in result['error']


# =============================================================================
# Tier 3: Subprocess tests for add/remove/ensure (need --target path resolution)
# =============================================================================


class TestAdd:
    """Test permission_fix.py add subcommand (subprocess - needs --target resolution)."""

    def test_add_permission(self, tmp_path):
        """Should add a new permission."""
        claude_dir = tmp_path / '.claude'
        claude_dir.mkdir()
        settings_file = claude_dir / 'settings.json'
        settings_file.write_text(json.dumps({'permissions': {'allow': ['Bash(git:*)'], 'deny': [], 'ask': []}}))

        result = run_script(SCRIPT_PATH, 'add', '--permission', 'Bash(npm:*)', '--target', 'project', cwd=tmp_path)
        assert result.success, f'Script failed: {result.stderr}'

        settings = json.loads(settings_file.read_text())
        assert 'Bash(npm:*)' in settings['permissions']['allow']

    def test_add_permission_already_exists(self, tmp_path):
        """Should report when permission already exists."""
        claude_dir = tmp_path / '.claude'
        claude_dir.mkdir()
        settings_file = claude_dir / 'settings.json'
        settings_file.write_text(json.dumps({'permissions': {'allow': ['Bash(git:*)'], 'deny': [], 'ask': []}}))

        result = run_script(SCRIPT_PATH, 'add', '--permission', 'Bash(git:*)', '--target', 'project', cwd=tmp_path)
        assert result.success, f'Script failed: {result.stderr}'
        data = result.toon()

        assert data.get('action') == 'already_exists'


class TestRemove:
    """Test permission_fix.py remove subcommand (subprocess - needs --target resolution)."""

    def test_remove_permission(self, tmp_path):
        """Should remove an existing permission."""
        claude_dir = tmp_path / '.claude'
        claude_dir.mkdir()
        settings_file = claude_dir / 'settings.json'
        settings_file.write_text(
            json.dumps({'permissions': {'allow': ['Bash(git:*)', 'Bash(npm:*)'], 'deny': [], 'ask': []}})
        )

        result = run_script(
            SCRIPT_PATH, 'remove', '--permission', 'Bash(npm:*)', '--target', 'project', cwd=tmp_path
        )
        assert result.success, f'Script failed: {result.stderr}'

        settings = json.loads(settings_file.read_text())
        assert 'Bash(npm:*)' not in settings['permissions']['allow']
        assert 'Bash(git:*)' in settings['permissions']['allow']

    def test_remove_nonexistent_permission(self, tmp_path):
        """Should report when permission doesn't exist."""
        claude_dir = tmp_path / '.claude'
        claude_dir.mkdir()
        settings_file = claude_dir / 'settings.json'
        settings_file.write_text(json.dumps({'permissions': {'allow': ['Bash(git:*)'], 'deny': [], 'ask': []}}))

        result = run_script(
            SCRIPT_PATH, 'remove', '--permission', 'Bash(npm:*)', '--target', 'project', cwd=tmp_path
        )
        assert result.success, f'Script failed: {result.stderr}'
        data = result.toon()

        assert data.get('action') == 'not_found'


class TestEnsure:
    """Test permission_fix.py ensure subcommand (subprocess - needs --target resolution)."""

    def test_ensure_adds_missing(self, tmp_path):
        """Should add permissions that are missing."""
        claude_dir = tmp_path / '.claude'
        claude_dir.mkdir()
        settings_file = claude_dir / 'settings.json'
        settings_file.write_text(json.dumps({'permissions': {'allow': ['Bash(git:*)'], 'deny': [], 'ask': []}}))

        result = run_script(
            SCRIPT_PATH,
            'ensure',
            '--permissions',
            'Bash(git:*),Bash(npm:*),Bash(docker:*)',
            '--target',
            'project',
            cwd=tmp_path,
        )
        assert result.success, f'Script failed: {result.stderr}'
        data = result.toon()

        assert 'added' in data
        assert 'Bash(npm:*)' in data['added']
        assert 'Bash(docker:*)' in data['added']
        assert 'already_exists' in data
        assert 'Bash(git:*)' in data['already_exists']

    def test_ensure_all_exist(self, tmp_path):
        """Should report all as existing when none are missing."""
        claude_dir = tmp_path / '.claude'
        claude_dir.mkdir()
        settings_file = claude_dir / 'settings.json'
        settings_file.write_text(
            json.dumps({'permissions': {'allow': ['Bash(git:*)', 'Bash(npm:*)'], 'deny': [], 'ask': []}})
        )

        result = run_script(
            SCRIPT_PATH,
            'ensure',
            '--permissions',
            'Bash(git:*),Bash(npm:*)',
            '--target',
            'project',
            cwd=tmp_path,
        )
        assert result.success, f'Script failed: {result.stderr}'
        data = result.toon()

        assert data.get('added_count', 0) == 0

    def test_ensure_writes_to_file(self, tmp_path):
        """Ensure should actually modify the settings file."""
        claude_dir = tmp_path / '.claude'
        claude_dir.mkdir()
        settings_file = claude_dir / 'settings.json'
        settings_file.write_text(json.dumps({'permissions': {'allow': [], 'deny': [], 'ask': []}}))

        run_script(
            SCRIPT_PATH,
            'ensure',
            '--permissions',
            'Bash(npm:*)',
            '--target',
            'project',
            cwd=tmp_path,
        )

        settings = json.loads(settings_file.read_text())
        assert 'Bash(npm:*)' in settings['permissions']['allow']


# =============================================================================
# Tier 3: Subprocess tests for --scope option
# =============================================================================


class TestScopeOption:
    """Test permission_fix.py --scope option for apply-fixes and consolidate."""

    def test_apply_fixes_with_scope_project(self, tmp_path):
        """apply-fixes should work with --scope project."""
        claude_dir = tmp_path / '.claude'
        claude_dir.mkdir()
        settings_file = claude_dir / 'settings.json'
        settings_file.write_text(
            json.dumps({'permissions': {'allow': ['Bash(git:*)', 'Bash(git:*)'], 'deny': [], 'ask': []}})
        )

        result = run_script(SCRIPT_PATH, 'apply-fixes', '--scope', 'project', '--dry-run', cwd=tmp_path)
        assert result.success, f'Script failed: {result.stderr}'
        data = result.toon()

        assert 'duplicates_removed' in data
        assert data['duplicates_removed'] == 1
        assert str(settings_file) in data['settings_path']

    def test_consolidate_with_scope_project(self, tmp_path):
        """consolidate should work with --scope project."""
        claude_dir = tmp_path / '.claude'
        claude_dir.mkdir()
        settings_file = claude_dir / 'settings.json'
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

        result = run_script(SCRIPT_PATH, 'consolidate', '--scope', 'project', '--dry-run', cwd=tmp_path)
        assert result.success, f'Script failed: {result.stderr}'
        data = result.toon()

        assert 'consolidated' in data
        assert data['consolidated'] == 2

    def test_scope_and_settings_mutually_exclusive(self):
        """--scope and --settings should be mutually exclusive."""
        result = run_script(
            SCRIPT_PATH, 'apply-fixes', '--scope', 'project', '--settings', '/tmp/test.json', '--dry-run'
        )
        assert result.returncode == 2


# =============================================================================
# Tier 3: Subprocess tests for executor pattern (need --target path resolution)
# =============================================================================


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


def test_consolidate_help():
    """consolidate subcommand should have help."""
    result = run_script(SCRIPT_PATH, 'consolidate', '--help')
    assert result.returncode == 0


def test_ensure_wildcards_help():
    """ensure-wildcards subcommand should have help."""
    result = run_script(SCRIPT_PATH, 'ensure-wildcards', '--help')
    assert result.returncode == 0


def test_apply_fixes_help():
    """apply-fixes subcommand should have help."""
    result = run_script(SCRIPT_PATH, 'apply-fixes', '--help')
    assert result.returncode == 0


def test_add_help():
    """add subcommand should have help."""
    result = run_script(SCRIPT_PATH, 'add', '--help')
    assert result.returncode == 0


def test_remove_help():
    """remove subcommand should have help."""
    result = run_script(SCRIPT_PATH, 'remove', '--help')
    assert result.returncode == 0


def test_ensure_help():
    """ensure subcommand should have help."""
    result = run_script(SCRIPT_PATH, 'ensure', '--help')
    assert result.returncode == 0


def test_generate_wildcards_help():
    """generate-wildcards subcommand should have help."""
    result = run_script(SCRIPT_PATH, 'generate-wildcards', '--help')
    assert result.returncode == 0


def test_ensure_executor_help():
    """ensure-executor subcommand should have help."""
    result = run_script(SCRIPT_PATH, 'ensure-executor', '--help')
    assert result.returncode == 0


def test_cleanup_scripts_help():
    """cleanup-scripts subcommand should have help."""
    result = run_script(SCRIPT_PATH, 'cleanup-scripts', '--help')
    assert result.returncode == 0


def test_migrate_executor_help():
    """migrate-executor subcommand should have help."""
    result = run_script(SCRIPT_PATH, 'migrate-executor', '--help')
    assert result.returncode == 0


def test_apply_project_step_permissions_help():
    """apply-project-step-permissions subcommand should have help."""
    result = run_script(SCRIPT_PATH, 'apply-project-step-permissions', '--help')
    assert result.returncode == 0


def test_remove_redundant_help():
    """remove-redundant subcommand should have help."""
    result = run_script(SCRIPT_PATH, 'remove-redundant', '--help')
    assert result.returncode == 0


# =============================================================================
# Tier 2: Tests for apply-project-step-permissions subcommand
# =============================================================================


class TestApplyProjectStepPermissions:
    """Test permission_fix.py apply-project-step-permissions subcommand."""

    def _write_marshal(self, tmp_path, phase_steps: dict[str, list[str]]) -> str:
        marshal = {'plan': {phase: {'steps': steps} for phase, steps in phase_steps.items()}}
        marshal_file = tmp_path / 'marshal.json'
        marshal_file.write_text(json.dumps(marshal))
        return str(marshal_file)

    def _write_settings(self, tmp_path, allow: list[str]) -> str:
        settings = {'permissions': {'allow': allow, 'deny': [], 'ask': []}}
        settings_file = tmp_path / 'settings.json'
        settings_file.write_text(json.dumps(settings))
        return str(settings_file)

    def _read_settings(self, path: str) -> dict:
        with open(path) as f:
            return json.load(f)

    def test_dry_run_does_not_mutate_settings(self, tmp_path):
        """--dry-run must not touch the settings file."""
        marshal = self._write_marshal(tmp_path, {'phase-6-finalize': ['project:finalize-step-plugin-doctor']})
        settings = self._write_settings(tmp_path, ['Edit(.plan/**)'])
        original = self._read_settings(settings)

        result = cmd_apply_project_step_permissions(Namespace(marshal=marshal, settings=settings, dry_run=True))

        assert result['status'] == 'success'
        assert result['added'] == ['Skill(finalize-step-plugin-doctor)']
        assert not result['applied']
        assert self._read_settings(settings) == original

    def test_default_run_appends_missing_rules(self, tmp_path):
        """Default run appends missing Skill() rules and sorts the allow list."""
        marshal = self._write_marshal(tmp_path, {'phase-6-finalize': ['project:finalize-step-plugin-doctor']})
        settings = self._write_settings(tmp_path, ['Edit(.plan/**)', 'Bash(git:*)'])

        result = cmd_apply_project_step_permissions(Namespace(marshal=marshal, settings=settings, dry_run=False))

        assert result['status'] == 'success'
        assert result['applied']
        allow = self._read_settings(settings)['permissions']['allow']
        assert 'Skill(finalize-step-plugin-doctor)' in allow
        assert allow == sorted(allow)

    def test_idempotent_re_run(self, tmp_path):
        """Running twice must not create duplicates."""
        marshal = self._write_marshal(tmp_path, {'phase-6-finalize': ['project:finalize-step-plugin-doctor']})
        settings = self._write_settings(tmp_path, [])

        cmd_apply_project_step_permissions(Namespace(marshal=marshal, settings=settings, dry_run=False))
        result = cmd_apply_project_step_permissions(Namespace(marshal=marshal, settings=settings, dry_run=False))

        assert result['status'] == 'success'
        assert result['added'] == []
        assert result['summary']['already_present_count'] == 1
        allow = self._read_settings(settings)['permissions']['allow']
        assert allow.count('Skill(finalize-step-plugin-doctor)') == 1

    def test_wildcard_coverage_short_circuits_add(self, tmp_path):
        """Covering wildcard Skill({skill}:*) prevents adding bare Skill({skill})."""
        marshal = self._write_marshal(tmp_path, {'phase-5-execute': ['project:verify-workflow']})
        settings = self._write_settings(tmp_path, ['Skill(verify-workflow:*)'])

        result = cmd_apply_project_step_permissions(Namespace(marshal=marshal, settings=settings, dry_run=False))

        assert result['status'] == 'success'
        assert result['added'] == []
        allow = self._read_settings(settings)['permissions']['allow']
        assert 'Skill(verify-workflow)' not in allow


# =============================================================================
# Bootstrap isolation test -- verify script works WITHOUT executor PYTHONPATH
# =============================================================================


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
