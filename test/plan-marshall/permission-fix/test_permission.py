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
"""

import json
import sys

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import MARKETPLACE_ROOT, ScriptTestCase, run_script

# Script path to permission-fix.py
SCRIPT_PATH = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'permission-fix' / 'scripts' / 'permission-fix.py'


# =============================================================================
# Tests for consolidate subcommand
# =============================================================================

class TestConsolidate(ScriptTestCase):
    """Test permission-fix.py consolidate subcommand."""

    bundle = 'plan-marshall'
    skill = 'permission-fix'
    script = 'permission-fix.py'

    def test_detect_timestamped_build_output(self):
        """Should detect permissions with timestamp patterns."""
        settings_file = self.temp_dir / 'settings.json'
        settings_file.write_text(json.dumps({
            "permissions": {
                "allow": [
                    "Bash(git:*)",
                    "Read(target/build-output-2025-11-20-174411.log)",
                    "Read(target/build-output-2025-11-21-093000.log)",
                    "Read(target/build-output-2025-11-22-120000.log)"
                ],
                "deny": [],
                "ask": []
            }
        }))

        result = run_script(
            SCRIPT_PATH,
            'consolidate',
            '--settings', str(settings_file),
            '--dry-run'
        )
        self.assert_success(result)
        data = result.json()

        self.assertIn('consolidated', data)
        self.assertEqual(data['consolidated'], 3)

    def test_generates_correct_wildcard(self):
        """Should generate correct wildcard pattern."""
        settings_file = self.temp_dir / 'settings.json'
        settings_file.write_text(json.dumps({
            "permissions": {
                "allow": [
                    "Read(target/build-output-2025-11-20-174411.log)",
                    "Read(target/build-output-2025-11-21-093000.log)"
                ],
                "deny": [],
                "ask": []
            }
        }))

        result = run_script(
            SCRIPT_PATH,
            'consolidate',
            '--settings', str(settings_file),
            '--dry-run'
        )
        self.assert_success(result)
        data = result.json()

        self.assertIn('wildcards_added', data)
        self.assertIn('Read(target/build-output-*.log)', data['wildcards_added'])

    def test_dry_run_does_not_modify_file(self):
        """Dry-run should not modify the settings file."""
        original_content = json.dumps({
            "permissions": {
                "allow": ["Read(target/build-output-2025-11-20-174411.log)"],
                "deny": [],
                "ask": []
            }
        })

        settings_file = self.temp_dir / 'settings.json'
        settings_file.write_text(original_content)

        result = run_script(
            SCRIPT_PATH,
            'consolidate',
            '--settings', str(settings_file),
            '--dry-run'
        )
        self.assert_success(result)

        self.assertEqual(settings_file.read_text(), original_content)


# =============================================================================
# Tests for ensure-wildcards subcommand
# =============================================================================

class TestEnsureWildcards(ScriptTestCase):
    """Test permission-fix.py ensure-wildcards subcommand."""

    bundle = 'plan-marshall'
    skill = 'permission-fix'
    script = 'permission-fix.py'

    def test_adds_missing_wildcards(self):
        """Should add missing marketplace wildcards."""
        settings_file = self.temp_dir / 'settings.json'
        settings_file.write_text(json.dumps({
            "permissions": {
                "allow": ["Bash(git:*)"],
                "deny": [],
                "ask": []
            }
        }))

        marketplace_file = self.temp_dir / 'marketplace.json'
        marketplace_file.write_text(json.dumps({
            "bundles": [
                {"path": "bundles/builder"},
                {"path": "bundles/planning"}
            ]
        }))

        result = run_script(
            SCRIPT_PATH,
            'ensure-wildcards',
            '--settings', str(settings_file),
            '--marketplace-json', str(marketplace_file),
            '--dry-run'
        )
        self.assert_success(result)
        data = result.json()

        self.assertIn('added', data)
        # Should suggest adding wildcards for bundles

    def test_reports_already_present(self):
        """Should report wildcards already present."""
        settings_file = self.temp_dir / 'settings.json'
        settings_file.write_text(json.dumps({
            "permissions": {
                "allow": ["Skill(builder:*)", "SlashCommand(/builder:*)"],
                "deny": [],
                "ask": []
            }
        }))

        marketplace_file = self.temp_dir / 'marketplace.json'
        marketplace_file.write_text(json.dumps({
            "bundles": [
                {"path": "bundles/builder"}
            ]
        }))

        result = run_script(
            SCRIPT_PATH,
            'ensure-wildcards',
            '--settings', str(settings_file),
            '--marketplace-json', str(marketplace_file),
            '--dry-run'
        )
        self.assert_success(result)
        data = result.json()

        self.assertIn('already_present', data)

    def test_supports_plugins_key_with_embedded_skills_commands(self):
        """Should support 'plugins' key with embedded skills/commands arrays.

        This tests a format where plugins have skills and commands arrays
        directly in the plugin entry (used by scan-marketplace-inventory output).
        """
        settings_file = self.temp_dir / 'settings.json'
        settings_file.write_text(json.dumps({
            "permissions": {
                "allow": ["Bash(git:*)"],
                "deny": [],
                "ask": []
            }
        }))

        # Use 'plugins' key with embedded skills/commands
        marketplace_file = self.temp_dir / 'marketplace.json'
        marketplace_file.write_text(json.dumps({
            "name": "plan-marshall",
            "plugins": [
                {
                    "name": "pm-workflow",
                    "description": "Workflow management",
                    "source": "./bundles/pm-workflow",
                    "skills": [{"name": "manage-lifecycle"}],
                    "commands": [{"name": "plan-manage"}]
                },
                {
                    "name": "pm-dev-java",
                    "description": "Java development",
                    "source": "./bundles/pm-dev-java",
                    "skills": [{"name": "cui-java-core"}],
                    "commands": [{"name": "java-create"}]
                }
            ]
        }))

        result = run_script(
            SCRIPT_PATH,
            'ensure-wildcards',
            '--settings', str(settings_file),
            '--marketplace-json', str(marketplace_file),
            '--dry-run'
        )
        self.assert_success(result)
        data = result.json()

        # Should generate wildcards for both bundles
        self.assertIn('added', data)
        added = data['added']
        self.assertIn('Skill(pm-workflow:*)', added)
        self.assertIn('SlashCommand(/pm-workflow:*)', added)
        self.assertIn('Skill(pm-dev-java:*)', added)
        self.assertIn('SlashCommand(/pm-dev-java:*)', added)
        self.assertEqual(data['total'], 4)  # 2 bundles × 2 wildcards each

    def test_supports_real_marketplace_json_format(self):
        """Should support REAL marketplace.json format without skills/commands arrays.

        The actual marketplace/.claude-plugin/marketplace.json uses this format:
        {
            "plugins": [
                {
                    "name": "pm-workflow",
                    "description": "...",
                    "source": "./bundles/pm-workflow",
                    "strict": false
                }
            ]
        }

        Note: NO skills or commands arrays in the plugin entries.
        The script should generate wildcards for ALL bundles in this case.
        """
        settings_file = self.temp_dir / 'settings.json'
        settings_file.write_text(json.dumps({
            "permissions": {
                "allow": ["Bash(git:*)"],
                "deny": [],
                "ask": []
            }
        }))

        # Use REAL marketplace.json format - NO skills/commands arrays
        marketplace_file = self.temp_dir / 'marketplace.json'
        marketplace_file.write_text(json.dumps({
            "name": "plan-marshall",
            "plugins": [
                {
                    "name": "pm-workflow",
                    "description": "Workflow management",
                    "source": "./bundles/pm-workflow",
                    "strict": False
                },
                {
                    "name": "pm-dev-java",
                    "description": "Java development",
                    "source": "./bundles/pm-dev-java",
                    "strict": False
                }
            ]
        }))

        result = run_script(
            SCRIPT_PATH,
            'ensure-wildcards',
            '--settings', str(settings_file),
            '--marketplace-json', str(marketplace_file),
            '--dry-run'
        )
        self.assert_success(result)
        data = result.json()

        # Should generate wildcards for ALL bundles (assume both skills and commands)
        self.assertIn('added', data)
        added = data['added']
        self.assertIn('Skill(pm-workflow:*)', added)
        self.assertIn('SlashCommand(/pm-workflow:*)', added)
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
    skill = 'permission-fix'
    script = 'permission-fix.py'

    def test_removes_duplicates(self):
        """Should remove duplicate permissions."""
        settings_file = self.temp_dir / 'settings.json'
        settings_file.write_text(json.dumps({
            "permissions": {
                "allow": ["Bash(git:*)", "Bash(git:*)", "Bash(npm:*)"],
                "deny": [],
                "ask": []
            }
        }))

        result = run_script(
            SCRIPT_PATH,
            'apply-fixes',
            '--settings', str(settings_file),
            '--dry-run'
        )
        self.assert_success(result)
        data = result.json()

        self.assertIn('duplicates_removed', data)
        self.assertEqual(data['duplicates_removed'], 1)

    def test_sorts_permissions(self):
        """Should sort permissions alphabetically."""
        settings_file = self.temp_dir / 'settings.json'
        settings_file.write_text(json.dumps({
            "permissions": {
                "allow": ["Write(**)", "Bash(git:*)", "Edit(**)"],
                "deny": [],
                "ask": []
            }
        }))

        result = run_script(
            SCRIPT_PATH,
            'apply-fixes',
            '--settings', str(settings_file),
            '--dry-run'
        )
        self.assert_success(result)
        data = result.json()

        self.assertIn('sorted', data)
        self.assertTrue(data['sorted'])

    def test_adds_default_permissions(self):
        """Should add default permissions if missing."""
        settings_file = self.temp_dir / 'settings.json'
        settings_file.write_text(json.dumps({
            "permissions": {
                "allow": ["Bash(git:*)"],
                "deny": [],
                "ask": []
            }
        }))

        result = run_script(
            SCRIPT_PATH,
            'apply-fixes',
            '--settings', str(settings_file),
            '--dry-run'
        )
        self.assert_success(result)
        data = result.json()

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
    skill = 'permission-fix'
    script = 'permission-fix.py'

    def test_add_permission(self):
        """Should add a new permission."""
        # Create .claude/settings.json in temp directory
        claude_dir = self.temp_dir / '.claude'
        claude_dir.mkdir()
        settings_file = claude_dir / 'settings.json'
        settings_file.write_text(json.dumps({
            "permissions": {
                "allow": ["Bash(git:*)"],
                "deny": [],
                "ask": []
            }
        }))

        result = run_script(
            SCRIPT_PATH,
            'add',
            '--permission', 'Bash(npm:*)',
            '--target', 'project',
            cwd=self.temp_dir
        )
        self.assert_success(result)

        settings = json.loads(settings_file.read_text())
        self.assertIn('Bash(npm:*)', settings['permissions']['allow'])

    def test_add_permission_already_exists(self):
        """Should report when permission already exists."""
        # Create .claude/settings.json in temp directory
        claude_dir = self.temp_dir / '.claude'
        claude_dir.mkdir()
        settings_file = claude_dir / 'settings.json'
        settings_file.write_text(json.dumps({
            "permissions": {
                "allow": ["Bash(git:*)"],
                "deny": [],
                "ask": []
            }
        }))

        result = run_script(
            SCRIPT_PATH,
            'add',
            '--permission', 'Bash(git:*)',
            '--target', 'project',
            cwd=self.temp_dir
        )
        self.assert_success(result)
        data = result.json()

        # Should indicate already exists
        self.assertEqual(data.get('action'), 'already_exists')


# =============================================================================
# Tests for remove subcommand
# =============================================================================

class TestRemove(ScriptTestCase):
    """Test permission-fix.py remove subcommand."""

    bundle = 'plan-marshall'
    skill = 'permission-fix'
    script = 'permission-fix.py'

    def test_remove_permission(self):
        """Should remove an existing permission."""
        # Create .claude/settings.json in temp directory
        claude_dir = self.temp_dir / '.claude'
        claude_dir.mkdir()
        settings_file = claude_dir / 'settings.json'
        settings_file.write_text(json.dumps({
            "permissions": {
                "allow": ["Bash(git:*)", "Bash(npm:*)"],
                "deny": [],
                "ask": []
            }
        }))

        result = run_script(
            SCRIPT_PATH,
            'remove',
            '--permission', 'Bash(npm:*)',
            '--target', 'project',
            cwd=self.temp_dir
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
        settings_file.write_text(json.dumps({
            "permissions": {
                "allow": ["Bash(git:*)"],
                "deny": [],
                "ask": []
            }
        }))

        result = run_script(
            SCRIPT_PATH,
            'remove',
            '--permission', 'Bash(npm:*)',
            '--target', 'project',
            cwd=self.temp_dir
        )
        self.assert_success(result)
        data = result.json()

        # Should indicate not found
        self.assertEqual(data.get('action'), 'not_found')


# =============================================================================
# Tests for --scope option
# =============================================================================

class TestScopeOption(ScriptTestCase):
    """Test permission-fix.py --scope option for apply-fixes and consolidate."""

    bundle = 'plan-marshall'
    skill = 'permission-fix'
    script = 'permission-fix.py'

    def test_apply_fixes_with_scope_project(self):
        """apply-fixes should work with --scope project."""
        claude_dir = self.temp_dir / '.claude'
        claude_dir.mkdir()
        settings_file = claude_dir / 'settings.json'
        settings_file.write_text(json.dumps({
            "permissions": {
                "allow": ["Bash(git:*)", "Bash(git:*)"],
                "deny": [],
                "ask": []
            }
        }))

        result = run_script(
            SCRIPT_PATH,
            'apply-fixes',
            '--scope', 'project',
            '--dry-run',
            cwd=self.temp_dir
        )
        self.assert_success(result)
        data = result.json()

        self.assertIn('duplicates_removed', data)
        self.assertEqual(data['duplicates_removed'], 1)
        self.assertIn(str(settings_file), data['settings_path'])

    def test_consolidate_with_scope_project(self):
        """consolidate should work with --scope project."""
        claude_dir = self.temp_dir / '.claude'
        claude_dir.mkdir()
        settings_file = claude_dir / 'settings.json'
        settings_file.write_text(json.dumps({
            "permissions": {
                "allow": [
                    "Read(target/build-output-2025-11-20-174411.log)",
                    "Read(target/build-output-2025-11-21-093000.log)"
                ],
                "deny": [],
                "ask": []
            }
        }))

        result = run_script(
            SCRIPT_PATH,
            'consolidate',
            '--scope', 'project',
            '--dry-run',
            cwd=self.temp_dir
        )
        self.assert_success(result)
        data = result.json()

        self.assertIn('consolidated', data)
        self.assertEqual(data['consolidated'], 2)

    def test_scope_and_settings_mutually_exclusive(self):
        """--scope and --settings should be mutually exclusive."""
        result = run_script(
            SCRIPT_PATH,
            'apply-fixes',
            '--scope', 'project',
            '--settings', '/tmp/test.json',
            '--dry-run'
        )
        # Should fail due to mutual exclusivity
        self.assertEqual(result.returncode, 2)


# =============================================================================
# Simple function-based tests for quick validation
# =============================================================================

def test_script_exists():
    """Verify the script exists."""
    assert SCRIPT_PATH.exists(), f"Script not found: {SCRIPT_PATH}"


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


# =============================================================================
# Main
# =============================================================================

if __name__ == '__main__':
    import unittest

    # Check if script exists first
    if not SCRIPT_PATH.exists():
        print(f"ERROR: Script not found: {SCRIPT_PATH}")
        sys.exit(1)

    # Run unittest-based tests
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestConsolidate))
    suite.addTests(loader.loadTestsFromTestCase(TestEnsureWildcards))
    suite.addTests(loader.loadTestsFromTestCase(TestApplyFixes))
    suite.addTests(loader.loadTestsFromTestCase(TestAdd))
    suite.addTests(loader.loadTestsFromTestCase(TestRemove))
    suite.addTests(loader.loadTestsFromTestCase(TestScopeOption))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Also run simple function tests
    print("\n" + "=" * 50)
    print("Running simple function tests...")
    print("=" * 50)

    simple_tests = [
        test_script_exists,
        test_help_works,
        test_consolidate_help,
        test_ensure_wildcards_help,
        test_apply_fixes_help,
        test_add_help,
        test_remove_help,
        test_ensure_help,
    ]

    # Run simple function tests
    simple_failures = 0
    for test_fn in simple_tests:
        try:
            test_fn()
            print(f"  PASS: {test_fn.__name__}")
        except AssertionError as e:
            print(f"  FAIL: {test_fn.__name__}: {e}")
            simple_failures += 1

    # Exit with combined result
    sys.exit(0 if result.wasSuccessful() and simple_failures == 0 else 1)
