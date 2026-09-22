#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Marketplace scan + add/remove/ensure/scope (carve 2 split)."""

import json

from _permission_fix_fixtures import (
    create_marketplace,
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


class TestScanMarketplaceDir:
    """Test scan_marketplace_dir function and generate-wildcards --marketplace-dir."""

    def test_scans_bundles_with_skills_and_commands(self, tmp_path):
        """Should discover skills and commands from plugin.json files."""
        mkt_dir = create_marketplace(
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
        mkt_dir = create_marketplace(
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
        mkt_dir = create_marketplace(
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

        result = cmd_generate_wildcards(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'generate-wildcards',
                '--marketplace-dir',
                str(mkt_dir),
            )
        )

        assert result['status'] == 'success'
        skill_wildcards = result['permissions']['skill_wildcards']
        cmd_wildcards = result['permissions']['command_bundle_wildcards']
        assert 'Skill(plan-marshall:*)' in skill_wildcards
        assert 'Skill(pm-dev-java:*)' in cmd_wildcards + skill_wildcards
        assert 'SlashCommand(/plan-marshall:*)' in cmd_wildcards

    def test_generate_wildcards_marketplace_dir_error(self):
        """generate-wildcards --marketplace-dir with bad path should return error."""
        result = cmd_generate_wildcards(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'generate-wildcards',
                '--marketplace-dir',
                '/nonexistent/path',
            )
        )

        assert result['status'] == 'error'
        assert 'marketplace.json not found' in result['error']


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

        result = run_script(SCRIPT_PATH, 'remove', '--permission', 'Bash(npm:*)', '--target', 'project', cwd=tmp_path)
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

        result = run_script(SCRIPT_PATH, 'remove', '--permission', 'Bash(npm:*)', '--target', 'project', cwd=tmp_path)
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
