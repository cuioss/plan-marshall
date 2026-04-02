#!/usr/bin/env python3
"""
Tests for the permission-fix.py script.

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
"""

import json
import sys

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import MARKETPLACE_ROOT, ScriptTestCase, run_script

# Script path to permission-fix.py
SCRIPT_PATH = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'tools-permission-fix' / 'scripts' / 'permission-fix.py'


# =============================================================================
# Tests for consolidate subcommand
# =============================================================================


class TestConsolidate(ScriptTestCase):
    """Test permission-fix.py consolidate subcommand."""

    bundle = 'plan-marshall'
    skill = 'tools-permission-fix'
    script = 'permission-fix.py'

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

        result = run_script(SCRIPT_PATH, 'consolidate', '--settings', str(settings_file), '--dry-run')
        self.assert_success(result)
        data = result.toon()

        self.assertIn('consolidated', data)
        self.assertEqual(data['consolidated'], 3)

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

        result = run_script(SCRIPT_PATH, 'consolidate', '--settings', str(settings_file), '--dry-run')
        self.assert_success(result)
        data = result.toon()

        self.assertIn('wildcards_added', data)
        self.assertIn('Read(target/build-output-*.log)', data['wildcards_added'])

    def test_dry_run_does_not_modify_file(self):
        """Dry-run should not modify the settings file."""
        original_content = json.dumps(
            {'permissions': {'allow': ['Read(target/build-output-2025-11-20-174411.log)'], 'deny': [], 'ask': []}}
        )

        settings_file = self.temp_dir / 'settings.json'
        settings_file.write_text(original_content)

        result = run_script(SCRIPT_PATH, 'consolidate', '--settings', str(settings_file), '--dry-run')
        self.assert_success(result)

        self.assertEqual(settings_file.read_text(), original_content)


# =============================================================================
# Tests for ensure-wildcards subcommand
# =============================================================================


class TestEnsureWildcards(ScriptTestCase):
    """Test permission-fix.py ensure-wildcards subcommand."""

    bundle = 'plan-marshall'
    skill = 'tools-permission-fix'
    script = 'permission-fix.py'

    def test_adds_missing_wildcards(self):
        """Should add missing marketplace wildcards."""
        settings_file = self.temp_dir / 'settings.json'
        settings_file.write_text(json.dumps({'permissions': {'allow': ['Bash(git:*)'], 'deny': [], 'ask': []}}))

        # Use new dict format: bundles are keys, not list items
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

        result = run_script(
            SCRIPT_PATH,
            'ensure-wildcards',
            '--settings',
            str(settings_file),
            '--marketplace-json',
            str(marketplace_file),
            '--dry-run',
        )
        self.assert_success(result)
        data = result.toon()

        self.assertIn('added', data)
        # Should suggest adding wildcards for bundles
        added = data['added']
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

        # Use new dict format: bundles are keys
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

        result = run_script(
            SCRIPT_PATH,
            'ensure-wildcards',
            '--settings',
            str(settings_file),
            '--marketplace-json',
            str(marketplace_file),
            '--dry-run',
        )
        self.assert_success(result)
        data = result.toon()

        self.assertIn('already_present', data)
        self.assertEqual(data['already_present'], 2)  # Both Skill and SlashCommand already exist

    def test_bundles_with_skills_and_commands_arrays(self):
        """Should generate wildcards for bundles with skills/commands arrays.

        Tests the scan-marketplace-inventory JSON output format where bundles
        are dict keys and values contain skills/commands arrays.
        """
        settings_file = self.temp_dir / 'settings.json'
        settings_file.write_text(json.dumps({'permissions': {'allow': ['Bash(git:*)'], 'deny': [], 'ask': []}}))

        # Use new dict format with skills/commands arrays
        marketplace_file = self.temp_dir / 'marketplace.json'
        marketplace_file.write_text(
            json.dumps(
                {
                    'bundles': {
                        'plan-marshall': {
                            'path': 'marketplace/bundles/plan-marshall',
                            'skills': ['manage-lifecycle', 'plan-manage'],
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

        result = run_script(
            SCRIPT_PATH,
            'ensure-wildcards',
            '--settings',
            str(settings_file),
            '--marketplace-json',
            str(marketplace_file),
            '--dry-run',
        )
        self.assert_success(result)
        data = result.toon()

        # Should generate wildcards for both bundles
        self.assertIn('added', data)
        added = data['added']
        self.assertIn('Skill(plan-marshall:*)', added)
        self.assertIn('SlashCommand(/plan-marshall:*)', added)
        self.assertIn('Skill(pm-dev-java:*)', added)
        self.assertIn('SlashCommand(/pm-dev-java:*)', added)
        self.assertEqual(data['total'], 4)  # 2 bundles × 2 wildcards each

    def test_bundles_without_skills_commands_arrays(self):
        """Should assume bundles have both skills and commands when arrays absent.

        When bundles dict entries don't have explicit skills/commands arrays,
        the script should assume the bundle has both and generate wildcards for each.
        """
        settings_file = self.temp_dir / 'settings.json'
        settings_file.write_text(json.dumps({'permissions': {'allow': ['Bash(git:*)'], 'deny': [], 'ask': []}}))

        # Bundles without skills/commands arrays
        marketplace_file = self.temp_dir / 'marketplace.json'
        marketplace_file.write_text(
            json.dumps(
                {
                    'bundles': {
                        'plan-marshall': {
                            'path': 'marketplace/bundles/plan-marshall',
                        },
                        'pm-dev-java': {
                            'path': 'marketplace/bundles/pm-dev-java',
                        },
                    }
                }
            )
        )

        result = run_script(
            SCRIPT_PATH,
            'ensure-wildcards',
            '--settings',
            str(settings_file),
            '--marketplace-json',
            str(marketplace_file),
            '--dry-run',
        )
        self.assert_success(result)
        data = result.toon()

        # Should generate wildcards for ALL bundles (assume both skills and commands)
        self.assertIn('added', data)
        added = data['added']
        self.assertIn('Skill(plan-marshall:*)', added)
        self.assertIn('SlashCommand(/plan-marshall:*)', added)
        self.assertIn('Skill(pm-dev-java:*)', added)
        self.assertIn('SlashCommand(/pm-dev-java:*)', added)
        self.assertEqual(data['bundles_analyzed'], 2)
        self.assertEqual(data['total'], 4)  # 2 bundles × 2 wildcards each


# =============================================================================
# Tests for apply-fixes subcommand
# =============================================================================


class TestApplyFixes(ScriptTestCase):
    """Test permission-fix.py apply-fixes subcommand."""

    bundle = 'plan-marshall'
    skill = 'tools-permission-fix'
    script = 'permission-fix.py'

    def test_removes_duplicates(self):
        """Should remove duplicate permissions."""
        settings_file = self.temp_dir / 'settings.json'
        settings_file.write_text(
            json.dumps({'permissions': {'allow': ['Bash(git:*)', 'Bash(git:*)', 'Bash(npm:*)'], 'deny': [], 'ask': []}})
        )

        result = run_script(SCRIPT_PATH, 'apply-fixes', '--settings', str(settings_file), '--dry-run')
        self.assert_success(result)
        data = result.toon()

        self.assertIn('duplicates_removed', data)
        self.assertEqual(data['duplicates_removed'], 1)

    def test_sorts_permissions(self):
        """Should sort permissions alphabetically."""
        settings_file = self.temp_dir / 'settings.json'
        settings_file.write_text(
            json.dumps({'permissions': {'allow': ['Write(**)', 'Bash(git:*)', 'Edit(**)'], 'deny': [], 'ask': []}})
        )

        result = run_script(SCRIPT_PATH, 'apply-fixes', '--settings', str(settings_file), '--dry-run')
        self.assert_success(result)
        data = result.toon()

        self.assertIn('sorted', data)
        self.assertTrue(data['sorted'])

    def test_adds_default_permissions(self):
        """Should add default permissions if missing."""
        settings_file = self.temp_dir / 'settings.json'
        settings_file.write_text(json.dumps({'permissions': {'allow': ['Bash(git:*)'], 'deny': [], 'ask': []}}))

        result = run_script(SCRIPT_PATH, 'apply-fixes', '--settings', str(settings_file), '--dry-run')
        self.assert_success(result)
        data = result.toon()

        self.assertIn('defaults_added', data)
        defaults = data['defaults_added']
        self.assertIn('Edit(.plan/**)', defaults)
        self.assertIn('Write(.plan/**)', defaults)
        self.assertIn('Read(~/.claude/plugins/cache/**)', defaults)


# =============================================================================
# Tests for add subcommand
# =============================================================================


class TestAdd(ScriptTestCase):
    """Test permission-fix.py add subcommand."""

    bundle = 'plan-marshall'
    skill = 'tools-permission-fix'
    script = 'permission-fix.py'

    def test_add_permission(self):
        """Should add a new permission."""
        # Create .claude/settings.json in temp directory
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
        # Create .claude/settings.json in temp directory
        claude_dir = self.temp_dir / '.claude'
        claude_dir.mkdir()
        settings_file = claude_dir / 'settings.json'
        settings_file.write_text(json.dumps({'permissions': {'allow': ['Bash(git:*)'], 'deny': [], 'ask': []}}))

        result = run_script(SCRIPT_PATH, 'add', '--permission', 'Bash(git:*)', '--target', 'project', cwd=self.temp_dir)
        self.assert_success(result)
        data = result.toon()

        # Should indicate already exists
        self.assertEqual(data.get('action'), 'already_exists')


# =============================================================================
# Tests for remove subcommand
# =============================================================================


class TestRemove(ScriptTestCase):
    """Test permission-fix.py remove subcommand."""

    bundle = 'plan-marshall'
    skill = 'tools-permission-fix'
    script = 'permission-fix.py'

    def test_remove_permission(self):
        """Should remove an existing permission."""
        # Create .claude/settings.json in temp directory
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
        # Create .claude/settings.json in temp directory
        claude_dir = self.temp_dir / '.claude'
        claude_dir.mkdir()
        settings_file = claude_dir / 'settings.json'
        settings_file.write_text(json.dumps({'permissions': {'allow': ['Bash(git:*)'], 'deny': [], 'ask': []}}))

        result = run_script(
            SCRIPT_PATH, 'remove', '--permission', 'Bash(npm:*)', '--target', 'project', cwd=self.temp_dir
        )
        self.assert_success(result)
        data = result.toon()

        # Should indicate not found
        self.assertEqual(data.get('action'), 'not_found')


# =============================================================================
# Tests for ensure subcommand
# =============================================================================


class TestEnsure(ScriptTestCase):
    """Test permission-fix.py ensure subcommand."""

    bundle = 'plan-marshall'
    skill = 'tools-permission-fix'
    script = 'permission-fix.py'

    def test_ensure_adds_missing(self):
        """Should add permissions that are missing."""
        claude_dir = self.temp_dir / '.claude'
        claude_dir.mkdir()
        settings_file = claude_dir / 'settings.json'
        settings_file.write_text(json.dumps({'permissions': {'allow': ['Bash(git:*)'], 'deny': [], 'ask': []}}))

        result = run_script(
            SCRIPT_PATH, 'ensure',
            '--permissions', 'Bash(git:*),Bash(npm:*),Bash(docker:*)',
            '--target', 'project',
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
            SCRIPT_PATH, 'ensure',
            '--permissions', 'Bash(git:*),Bash(npm:*)',
            '--target', 'project',
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
            SCRIPT_PATH, 'ensure',
            '--permissions', 'Bash(npm:*)',
            '--target', 'project',
            cwd=self.temp_dir,
        )

        settings = json.loads(settings_file.read_text())
        self.assertIn('Bash(npm:*)', settings['permissions']['allow'])


# =============================================================================
# Tests for --scope option
# =============================================================================


class TestScopeOption(ScriptTestCase):
    """Test permission-fix.py --scope option for apply-fixes and consolidate."""

    bundle = 'plan-marshall'
    skill = 'tools-permission-fix'
    script = 'permission-fix.py'

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
        # Should fail due to mutual exclusivity
        self.assertEqual(result.returncode, 2)


# =============================================================================
# Tests for generate-wildcards subcommand
# =============================================================================


class TestGenerateWildcards(ScriptTestCase):
    """Test permission-fix.py generate-wildcards subcommand."""

    bundle = 'plan-marshall'
    skill = 'tools-permission-fix'
    script = 'permission-fix.py'

    def test_generates_skill_wildcards(self):
        """Should generate Skill() wildcards from inventory."""
        inventory = {
            'bundles': [
                {
                    'name': 'builder',
                    'skills': [{'name': 'builder-gradle-rules'}, {'name': 'builder-maven-rules'}],
                    'commands': [],
                }
            ]
        }

        result = run_script(SCRIPT_PATH, 'generate-wildcards', input_data=json.dumps(inventory))
        self.assert_success(result)
        data = result.toon()

        self.assertIn('permissions', data)
        self.assertIn('skill_wildcards', data['permissions'])
        self.assertIn('Skill(builder:*)', data['permissions']['skill_wildcards'])

    def test_generates_command_wildcards(self):
        """Should generate SlashCommand() wildcards from inventory."""
        inventory = {
            'bundles': [
                {'name': 'plan-marshall', 'skills': [], 'commands': [{'name': 'plan-manage'}, {'name': 'task-standalone'}]}
            ]
        }

        result = run_script(SCRIPT_PATH, 'generate-wildcards', input_data=json.dumps(inventory))
        self.assert_success(result)
        data = result.toon()

        self.assertIn('permissions', data)
        self.assertIn('command_bundle_wildcards', data['permissions'])
        self.assertIn('SlashCommand(/plan-marshall:*)', data['permissions']['command_bundle_wildcards'])

    def test_includes_statistics(self):
        """Should include statistics in output."""
        inventory = {
            'bundles': [{'name': 'test-bundle', 'skills': [{'name': 'skill1'}], 'commands': [{'name': 'cmd1'}]}]
        }

        result = run_script(SCRIPT_PATH, 'generate-wildcards', input_data=json.dumps(inventory))
        self.assert_success(result)
        data = result.toon()

        self.assertIn('statistics', data)
        self.assertIn('bundles_scanned', data['statistics'])


# =============================================================================
# Tests for executor pattern subcommands
# =============================================================================


class TestExecutorPattern(ScriptTestCase):
    """Test permission-fix.py executor pattern subcommands."""

    bundle = 'plan-marshall'
    skill = 'tools-permission-fix'
    script = 'permission-fix.py'

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
        # Individual script permission should be removed
        self.assertEqual(len(settings['permissions']['allow']), 2)


# =============================================================================
# Simple function-based tests for quick validation
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
# Main
# =============================================================================

if __name__ == '__main__':
    import unittest

    # Check if script exists first
    if not SCRIPT_PATH.exists():
        print(f'ERROR: Script not found: {SCRIPT_PATH}')
        sys.exit(1)

    # Run unittest-based tests
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestConsolidate))
    suite.addTests(loader.loadTestsFromTestCase(TestEnsureWildcards))
    suite.addTests(loader.loadTestsFromTestCase(TestApplyFixes))
    suite.addTests(loader.loadTestsFromTestCase(TestAdd))
    suite.addTests(loader.loadTestsFromTestCase(TestRemove))
    suite.addTests(loader.loadTestsFromTestCase(TestEnsure))
    suite.addTests(loader.loadTestsFromTestCase(TestScopeOption))
    suite.addTests(loader.loadTestsFromTestCase(TestGenerateWildcards))
    suite.addTests(loader.loadTestsFromTestCase(TestExecutorPattern))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Also run simple function tests
    print('\n' + '=' * 50)
    print('Running simple function tests...')
    print('=' * 50)

    simple_tests = [
        test_script_exists,
        test_help_works,
        test_consolidate_help,
        test_ensure_wildcards_help,
        test_apply_fixes_help,
        test_add_help,
        test_remove_help,
        test_ensure_help,
        test_generate_wildcards_help,
        test_ensure_executor_help,
        test_cleanup_scripts_help,
        test_migrate_executor_help,
    ]

    # Run simple function tests
    simple_failures = 0
    for test_fn in simple_tests:
        try:
            test_fn()
            print(f'  PASS: {test_fn.__name__}')
        except AssertionError as e:
            print(f'  FAIL: {test_fn.__name__}: {e}')
            simple_failures += 1

    # Exit with combined result
    sys.exit(0 if result.wasSuccessful() and simple_failures == 0 else 1)
