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
from conftest import MARKETPLACE_ROOT, ScriptTestCase, run_script

# Script path for remaining subprocess (CLI plumbing) tests
SCRIPT_PATH = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'tools-permission-fix' / 'scripts' / 'permission_fix.py'

# Tier 2 direct imports
from permission_fix import (  # type: ignore[import-not-found]  # noqa: E402
    cmd_apply_fixes,
    cmd_consolidate,
    cmd_ensure_wildcards,
    cmd_generate_wildcards,
)

# =============================================================================
# Tier 2: Tests for consolidate subcommand
# =============================================================================


class TestConsolidate(ScriptTestCase):
    """Test permission_fix.py consolidate subcommand via direct import."""

    bundle = 'plan-marshall'
    skill = 'tools-permission-fix'
    script = 'permission_fix.py'

    def test_detect_timestamped_build_output(self):
        """Should detect permissions with timestamp patterns."""
        settings_file = self.temp_dir / 'settings.json'
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

        self.assertEqual(result['status'], 'success')
        self.assertIn('consolidated', result)
        self.assertEqual(result['consolidated'], 3)

    def test_generates_correct_wildcard(self):
        """Should generate correct wildcard pattern."""
        settings_file = self.temp_dir / 'settings.json'
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

        self.assertEqual(result['status'], 'success')
        self.assertIn('wildcards_added', result)
        self.assertIn('Read(target/build-output-*.log)', result['wildcards_added'])

    def test_dry_run_does_not_modify_file(self):
        """Dry-run should not modify the settings file."""
        original_content = json.dumps(
            {'permissions': {'allow': ['Read(target/build-output-2025-11-20-174411.log)'], 'deny': [], 'ask': []}}
        )

        settings_file = self.temp_dir / 'settings.json'
        settings_file.write_text(original_content)

        cmd_consolidate(Namespace(settings=str(settings_file), scope=None, dry_run=True))

        self.assertEqual(settings_file.read_text(), original_content)


# =============================================================================
# Tier 2: Tests for ensure-wildcards subcommand
# =============================================================================


class TestEnsureWildcards(ScriptTestCase):
    """Test permission_fix.py ensure-wildcards subcommand via direct import."""

    bundle = 'plan-marshall'
    skill = 'tools-permission-fix'
    script = 'permission_fix.py'

    def test_adds_missing_wildcards(self):
        """Should add missing marketplace wildcards."""
        settings_file = self.temp_dir / 'settings.json'
        settings_file.write_text(json.dumps({'permissions': {'allow': ['Bash(git:*)'], 'deny': [], 'ask': []}}))

        marketplace_file = self.temp_dir / 'marketplace.json'
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

        self.assertEqual(result['status'], 'success')
        self.assertIn('added', result)
        added = result['added']
        self.assertIn('Skill(builder:*)', added)
        self.assertIn('SlashCommand(/planning:*)', added)

    def test_reports_already_present(self):
        """Should report wildcards already present."""
        settings_file = self.temp_dir / 'settings.json'
        settings_file.write_text(
            json.dumps(
                {'permissions': {'allow': ['Skill(builder:*)', 'SlashCommand(/builder:*)'], 'deny': [], 'ask': []}}
            )
        )

        marketplace_file = self.temp_dir / 'marketplace.json'
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

        self.assertEqual(result['status'], 'success')
        self.assertIn('already_present', result)
        self.assertEqual(result['already_present'], 2)

    def test_bundles_with_skills_and_commands_arrays(self):
        """Should generate wildcards for bundles with skills/commands arrays."""
        settings_file = self.temp_dir / 'settings.json'
        settings_file.write_text(json.dumps({'permissions': {'allow': ['Bash(git:*)'], 'deny': [], 'ask': []}}))

        marketplace_file = self.temp_dir / 'marketplace.json'
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

        self.assertEqual(result['status'], 'success')
        self.assertIn('added', result)
        added = result['added']
        self.assertIn('Skill(plan-marshall:*)', added)
        self.assertIn('SlashCommand(/plan-marshall:*)', added)
        self.assertIn('Skill(pm-dev-java:*)', added)
        self.assertIn('SlashCommand(/pm-dev-java:*)', added)
        self.assertEqual(result['total'], 4)

    def test_bundles_without_skills_commands_arrays(self):
        """Should assume bundles have both skills and commands when arrays absent."""
        settings_file = self.temp_dir / 'settings.json'
        settings_file.write_text(json.dumps({'permissions': {'allow': ['Bash(git:*)'], 'deny': [], 'ask': []}}))

        marketplace_file = self.temp_dir / 'marketplace.json'
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

        self.assertEqual(result['status'], 'success')
        self.assertIn('added', result)
        added = result['added']
        self.assertIn('Skill(plan-marshall:*)', added)
        self.assertIn('SlashCommand(/plan-marshall:*)', added)
        self.assertIn('Skill(pm-dev-java:*)', added)
        self.assertIn('SlashCommand(/pm-dev-java:*)', added)
        self.assertEqual(result['bundles_analyzed'], 2)
        self.assertEqual(result['total'], 4)


# =============================================================================
# Tier 2: Tests for apply-fixes subcommand
# =============================================================================


class TestApplyFixes(ScriptTestCase):
    """Test permission_fix.py apply-fixes subcommand via direct import."""

    bundle = 'plan-marshall'
    skill = 'tools-permission-fix'
    script = 'permission_fix.py'

    def test_removes_duplicates(self):
        """Should remove duplicate permissions."""
        settings_file = self.temp_dir / 'settings.json'
        settings_file.write_text(
            json.dumps({'permissions': {'allow': ['Bash(git:*)', 'Bash(git:*)', 'Bash(npm:*)'], 'deny': [], 'ask': []}})
        )

        result = cmd_apply_fixes(Namespace(settings=str(settings_file), scope=None, dry_run=True))

        self.assertEqual(result['status'], 'success')
        self.assertIn('duplicates_removed', result)
        self.assertEqual(result['duplicates_removed'], 1)

    def test_sorts_permissions(self):
        """Should sort permissions alphabetically."""
        settings_file = self.temp_dir / 'settings.json'
        settings_file.write_text(
            json.dumps({'permissions': {'allow': ['Write(**)', 'Bash(git:*)', 'Edit(**)'], 'deny': [], 'ask': []}})
        )

        result = cmd_apply_fixes(Namespace(settings=str(settings_file), scope=None, dry_run=True))

        self.assertEqual(result['status'], 'success')
        self.assertIn('sorted', result)
        self.assertTrue(result['sorted'])

    def test_adds_default_permissions(self):
        """Should add default permissions if missing."""
        settings_file = self.temp_dir / 'settings.json'
        settings_file.write_text(json.dumps({'permissions': {'allow': ['Bash(git:*)'], 'deny': [], 'ask': []}}))

        result = cmd_apply_fixes(Namespace(settings=str(settings_file), scope=None, dry_run=True))

        self.assertEqual(result['status'], 'success')
        self.assertIn('defaults_added', result)
        defaults = result['defaults_added']
        self.assertIn('Edit(.plan/**)', defaults)
        self.assertIn('Write(.plan/**)', defaults)
        self.assertIn('Read(~/.claude/plugins/cache/**)', defaults)


# =============================================================================
# Tier 2: Tests for generate-wildcards subcommand
# =============================================================================


class TestGenerateWildcards(ScriptTestCase):
    """Test permission_fix.py generate-wildcards subcommand via direct import."""

    bundle = 'plan-marshall'
    skill = 'tools-permission-fix'
    script = 'permission_fix.py'

    def test_generates_skill_wildcards(self):
        """Should generate Skill() wildcards from inventory."""
        inventory_file = self.temp_dir / 'inventory.json'
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

        result = cmd_generate_wildcards(Namespace(input=str(inventory_file)))

        self.assertEqual(result['status'], 'success')
        self.assertIn('permissions', result)
        self.assertIn('skill_wildcards', result['permissions'])
        self.assertIn('Skill(builder:*)', result['permissions']['skill_wildcards'])

    def test_generates_command_wildcards(self):
        """Should generate SlashCommand() wildcards from inventory."""
        inventory_file = self.temp_dir / 'inventory.json'
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

        result = cmd_generate_wildcards(Namespace(input=str(inventory_file)))

        self.assertEqual(result['status'], 'success')
        self.assertIn('permissions', result)
        self.assertIn('command_bundle_wildcards', result['permissions'])
        self.assertIn('SlashCommand(/plan-marshall:*)', result['permissions']['command_bundle_wildcards'])

    def test_includes_statistics(self):
        """Should include statistics in output."""
        inventory_file = self.temp_dir / 'inventory.json'
        inventory_file.write_text(
            json.dumps(
                {
                    'bundles': [{'name': 'test-bundle', 'skills': [{'name': 'skill1'}], 'commands': [{'name': 'cmd1'}]}]
                }
            )
        )

        result = cmd_generate_wildcards(Namespace(input=str(inventory_file)))

        self.assertEqual(result['status'], 'success')
        self.assertIn('statistics', result)
        self.assertIn('bundles_scanned', result['statistics'])


# =============================================================================
# Tier 3: Subprocess tests for add/remove/ensure (need --target path resolution)
# =============================================================================


class TestAdd(ScriptTestCase):
    """Test permission_fix.py add subcommand (subprocess - needs --target resolution)."""

    bundle = 'plan-marshall'
    skill = 'tools-permission-fix'
    script = 'permission_fix.py'

    def test_add_permission(self):
        """Should add a new permission."""
        claude_dir = self.temp_dir / '.claude'
        claude_dir.mkdir()
        settings_file = claude_dir / 'settings.json'
        settings_file.write_text(json.dumps({'permissions': {'allow': ['Bash(git:*)'], 'deny': [], 'ask': []}}))

        result = run_script(SCRIPT_PATH, 'add', '--permission', 'Bash(npm:*)', '--target', 'project', cwd=self.temp_dir)
        self.assert_success(result)

        settings = json.loads(settings_file.read_text())
        self.assertIn('Bash(npm:*)', settings['permissions']['allow'])

    def test_add_permission_already_exists(self):
        """Should report when permission already exists."""
        claude_dir = self.temp_dir / '.claude'
        claude_dir.mkdir()
        settings_file = claude_dir / 'settings.json'
        settings_file.write_text(json.dumps({'permissions': {'allow': ['Bash(git:*)'], 'deny': [], 'ask': []}}))

        result = run_script(SCRIPT_PATH, 'add', '--permission', 'Bash(git:*)', '--target', 'project', cwd=self.temp_dir)
        self.assert_success(result)
        data = result.toon()

        self.assertEqual(data.get('action'), 'already_exists')


class TestRemove(ScriptTestCase):
    """Test permission_fix.py remove subcommand (subprocess - needs --target resolution)."""

    bundle = 'plan-marshall'
    skill = 'tools-permission-fix'
    script = 'permission_fix.py'

    def test_remove_permission(self):
        """Should remove an existing permission."""
        claude_dir = self.temp_dir / '.claude'
        claude_dir.mkdir()
        settings_file = claude_dir / 'settings.json'
        settings_file.write_text(
            json.dumps({'permissions': {'allow': ['Bash(git:*)', 'Bash(npm:*)'], 'deny': [], 'ask': []}})
        )

        result = run_script(
            SCRIPT_PATH, 'remove', '--permission', 'Bash(npm:*)', '--target', 'project', cwd=self.temp_dir
        )
        self.assert_success(result)

        settings = json.loads(settings_file.read_text())
        self.assertNotIn('Bash(npm:*)', settings['permissions']['allow'])
        self.assertIn('Bash(git:*)', settings['permissions']['allow'])

    def test_remove_nonexistent_permission(self):
        """Should report when permission doesn't exist."""
        claude_dir = self.temp_dir / '.claude'
        claude_dir.mkdir()
        settings_file = claude_dir / 'settings.json'
        settings_file.write_text(json.dumps({'permissions': {'allow': ['Bash(git:*)'], 'deny': [], 'ask': []}}))

        result = run_script(
            SCRIPT_PATH, 'remove', '--permission', 'Bash(npm:*)', '--target', 'project', cwd=self.temp_dir
        )
        self.assert_success(result)
        data = result.toon()

        self.assertEqual(data.get('action'), 'not_found')


class TestEnsure(ScriptTestCase):
    """Test permission_fix.py ensure subcommand (subprocess - needs --target resolution)."""

    bundle = 'plan-marshall'
    skill = 'tools-permission-fix'
    script = 'permission_fix.py'

    def test_ensure_adds_missing(self):
        """Should add permissions that are missing."""
        claude_dir = self.temp_dir / '.claude'
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
            cwd=self.temp_dir,
        )
        self.assert_success(result)
        data = result.toon()

        self.assertIn('added', data)
        self.assertIn('Bash(npm:*)', data['added'])
        self.assertIn('Bash(docker:*)', data['added'])
        self.assertIn('already_exists', data)
        self.assertIn('Bash(git:*)', data['already_exists'])

    def test_ensure_all_exist(self):
        """Should report all as existing when none are missing."""
        claude_dir = self.temp_dir / '.claude'
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
            cwd=self.temp_dir,
        )
        self.assert_success(result)
        data = result.toon()

        self.assertEqual(data.get('added_count', 0), 0)

    def test_ensure_writes_to_file(self):
        """Ensure should actually modify the settings file."""
        claude_dir = self.temp_dir / '.claude'
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
            cwd=self.temp_dir,
        )

        settings = json.loads(settings_file.read_text())
        self.assertIn('Bash(npm:*)', settings['permissions']['allow'])


# =============================================================================
# Tier 3: Subprocess tests for --scope option
# =============================================================================


class TestScopeOption(ScriptTestCase):
    """Test permission_fix.py --scope option for apply-fixes and consolidate."""

    bundle = 'plan-marshall'
    skill = 'tools-permission-fix'
    script = 'permission_fix.py'

    def test_apply_fixes_with_scope_project(self):
        """apply-fixes should work with --scope project."""
        claude_dir = self.temp_dir / '.claude'
        claude_dir.mkdir()
        settings_file = claude_dir / 'settings.json'
        settings_file.write_text(
            json.dumps({'permissions': {'allow': ['Bash(git:*)', 'Bash(git:*)'], 'deny': [], 'ask': []}})
        )

        result = run_script(SCRIPT_PATH, 'apply-fixes', '--scope', 'project', '--dry-run', cwd=self.temp_dir)
        self.assert_success(result)
        data = result.toon()

        self.assertIn('duplicates_removed', data)
        self.assertEqual(data['duplicates_removed'], 1)
        self.assertIn(str(settings_file), data['settings_path'])

    def test_consolidate_with_scope_project(self):
        """consolidate should work with --scope project."""
        claude_dir = self.temp_dir / '.claude'
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

        result = run_script(SCRIPT_PATH, 'consolidate', '--scope', 'project', '--dry-run', cwd=self.temp_dir)
        self.assert_success(result)
        data = result.toon()

        self.assertIn('consolidated', data)
        self.assertEqual(data['consolidated'], 2)

    def test_scope_and_settings_mutually_exclusive(self):
        """--scope and --settings should be mutually exclusive."""
        result = run_script(
            SCRIPT_PATH, 'apply-fixes', '--scope', 'project', '--settings', '/tmp/test.json', '--dry-run'
        )
        self.assertEqual(result.returncode, 2)


# =============================================================================
# Tier 3: Subprocess tests for executor pattern (need --target path resolution)
# =============================================================================


class TestExecutorPattern(ScriptTestCase):
    """Test permission_fix.py executor pattern subcommands."""

    bundle = 'plan-marshall'
    skill = 'tools-permission-fix'
    script = 'permission_fix.py'

    def test_ensure_executor_adds_permission(self):
        """Should add executor permission when missing."""
        claude_dir = self.temp_dir / '.claude'
        claude_dir.mkdir()
        settings_file = claude_dir / 'settings.json'
        settings_file.write_text(json.dumps({'permissions': {'allow': ['Bash(git:*)'], 'deny': [], 'ask': []}}))

        result = run_script(SCRIPT_PATH, 'ensure-executor', '--target', 'project', cwd=self.temp_dir)
        self.assert_success(result)
        data = result.toon()

        self.assertTrue(data.get('success'))
        self.assertEqual(data.get('action'), 'added')

        settings = json.loads(settings_file.read_text())
        self.assertIn('Bash(python3 .plan/execute-script.py *)', settings['permissions']['allow'])

    def test_ensure_executor_already_exists(self):
        """Should report when executor permission already exists."""
        claude_dir = self.temp_dir / '.claude'
        claude_dir.mkdir()
        settings_file = claude_dir / 'settings.json'
        settings_file.write_text(
            json.dumps({'permissions': {'allow': ['Bash(python3 .plan/execute-script.py *)'], 'deny': [], 'ask': []}})
        )

        result = run_script(SCRIPT_PATH, 'ensure-executor', '--target', 'project', cwd=self.temp_dir)
        self.assert_success(result)
        data = result.toon()

        self.assertTrue(data.get('success'))
        self.assertEqual(data.get('action'), 'already_exists')

    def test_cleanup_scripts_removes_individual_permissions(self):
        """Should remove individual script permissions."""
        claude_dir = self.temp_dir / '.claude'
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

        result = run_script(SCRIPT_PATH, 'cleanup-scripts', '--target', 'project', cwd=self.temp_dir)
        self.assert_success(result)
        data = result.toon()

        self.assertTrue(data.get('success'))
        self.assertEqual(data.get('individual_count'), 2)

        settings = json.loads(settings_file.read_text())
        self.assertEqual(len(settings['permissions']['allow']), 1)
        self.assertIn('Bash(git:*)', settings['permissions']['allow'])

    def test_migrate_executor_full_migration(self):
        """Should add executor and remove individual permissions."""
        claude_dir = self.temp_dir / '.claude'
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

        result = run_script(SCRIPT_PATH, 'migrate-executor', '--target', 'project', cwd=self.temp_dir)
        self.assert_success(result)
        data = result.toon()

        self.assertTrue(data.get('success'))
        self.assertIn('executor', data)
        self.assertIn('cleanup', data)

        settings = json.loads(settings_file.read_text())
        self.assertIn('Bash(python3 .plan/execute-script.py *)', settings['permissions']['allow'])
        self.assertIn('Bash(git:*)', settings['permissions']['allow'])
        self.assertEqual(len(settings['permissions']['allow']), 2)


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
        capture_output=True, text=True, env=env, timeout=30,
    )
    assert result.returncode == 0, (
        f'permission_fix.py failed without PYTHONPATH:\n{result.stderr}'
    )
