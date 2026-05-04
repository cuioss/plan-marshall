#!/usr/bin/env python3
"""
Tests for the gitignore_setup.py script.

Tier 2 (direct import) tests with 2 subprocess tests for CLI plumbing.

Tests .gitignore configuration for the planning system:
- Creates new .gitignore if not present
- Updates existing .gitignore with planning entries
- Reports unchanged when entries already exist
- Supports dry-run mode
"""

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import MARKETPLACE_ROOT, ScriptTestCase, run_script

# Script path to gitignore_setup.py
SCRIPT_PATH = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'marshall-steward' / 'scripts' / 'gitignore_setup.py'

# Tier 2 direct imports — conftest sets up PYTHONPATH for cross-skill imports
from gitignore_setup import (  # type: ignore[import-not-found]  # noqa: E402
    check_gitignore_status,
    setup_gitignore,
)


class TestGitignoreSetupCreate(ScriptTestCase):
    """Test gitignore_setup.py creating new .gitignore via direct import."""

    bundle = 'plan-marshall'
    skill = 'marshall-steward'
    script = 'gitignore_setup.py'

    def test_creates_gitignore_when_missing(self):
        """Should create new .gitignore with planning entries."""
        result = setup_gitignore(self.temp_dir)
        self.assertEqual(result['status'], 'created')
        # .plan/*, !marshal.json, !project-architecture/, .claude/worktrees/
        self.assertEqual(result['entries_added'], 4)

        # Verify file was created
        gitignore_path = self.temp_dir / '.gitignore'
        self.assertTrue(gitignore_path.exists())

        content = gitignore_path.read_text()
        self.assertIn('.plan/', content)
        self.assertIn('!.plan/marshal.json', content)
        self.assertIn('!.plan/project-architecture/', content)
        self.assertIn('.claude/worktrees/', content)
        self.assertIn('# Planning system', content)


class TestGitignoreSetupUpdate(ScriptTestCase):
    """Test gitignore_setup.py updating existing .gitignore via direct import."""

    bundle = 'plan-marshall'
    skill = 'marshall-steward'
    script = 'gitignore_setup.py'

    def test_updates_existing_gitignore(self):
        """Should add planning entries to existing .gitignore."""
        gitignore_path = self.temp_dir / '.gitignore'
        gitignore_path.write_text('# Existing content\nnode_modules/\n*.log\n')

        result = setup_gitignore(self.temp_dir)
        self.assertEqual(result['status'], 'updated')
        self.assertEqual(result['entries_added'], 4)

        # Verify existing content preserved and new content added
        content = gitignore_path.read_text()
        self.assertIn('node_modules/', content)
        self.assertIn('*.log', content)
        self.assertIn('.plan/', content)
        self.assertIn('!.plan/marshal.json', content)
        self.assertIn('!.plan/project-architecture/', content)
        self.assertIn('.claude/worktrees/', content)

    def test_adds_only_missing_entries(self):
        """Should only add entries that are missing."""
        gitignore_path = self.temp_dir / '.gitignore'
        gitignore_path.write_text('.plan/\n')

        result = setup_gitignore(self.temp_dir)
        self.assertEqual(result['status'], 'updated')
        # !marshal.json + !project-architecture/ + .claude/worktrees/
        self.assertEqual(result['entries_added'], 3)

        content = gitignore_path.read_text()
        self.assertIn('!.plan/marshal.json', content)
        self.assertIn('!.plan/project-architecture/', content)
        self.assertIn('.claude/worktrees/', content)


class TestGitignoreSetupUnchanged(ScriptTestCase):
    """Test gitignore_setup.py when no changes needed via direct import."""

    bundle = 'plan-marshall'
    skill = 'marshall-steward'
    script = 'gitignore_setup.py'

    def test_unchanged_when_all_entries_exist(self):
        """Should report unchanged when all entries already present."""
        gitignore_path = self.temp_dir / '.gitignore'
        gitignore_path.write_text(
            '# Runtime state (plans, run-configuration, lessons-learned, memory, logs '
            '— managed by plan-marshall)\n'
            '.plan/\n!.plan/marshal.json\n!.plan/project-architecture/\n.claude/worktrees/\n'
        )

        result = setup_gitignore(self.temp_dir)
        self.assertEqual(result['status'], 'unchanged')
        self.assertEqual(result['entries_added'], 0)

    def test_recognizes_alternate_plan_format(self):
        """Should recognize .plan without trailing slash."""
        gitignore_path = self.temp_dir / '.gitignore'
        gitignore_path.write_text(
            '# Runtime state (plans, run-configuration, lessons-learned, memory, logs '
            '— managed by plan-marshall)\n'
            '.plan\n!.plan/marshal.json\n!.plan/project-architecture/\n.claude/worktrees/\n'
        )

        result = setup_gitignore(self.temp_dir)
        # .plan (without slash) should be recognized as .plan/
        self.assertEqual(result['entries_added'], 0)

    def test_recognizes_claude_worktrees_without_trailing_slash(self):
        """Should recognize .claude/worktrees without trailing slash."""
        gitignore_path = self.temp_dir / '.gitignore'
        gitignore_path.write_text(
            '# Runtime state (plans, run-configuration, lessons-learned, memory, logs '
            '— managed by plan-marshall)\n'
            '.plan/\n!.plan/marshal.json\n!.plan/project-architecture/\n.claude/worktrees\n'
        )

        result = setup_gitignore(self.temp_dir)
        self.assertEqual(result['entries_added'], 0)

    def test_adds_claude_worktrees_when_missing(self):
        """Should add .claude/worktrees/ entry when only planning entries exist."""
        gitignore_path = self.temp_dir / '.gitignore'
        gitignore_path.write_text('.plan/*\n!.plan/marshal.json\n!.plan/project-architecture/\n')

        result = setup_gitignore(self.temp_dir)
        self.assertEqual(result['status'], 'updated')
        self.assertEqual(result['entries_added'], 1)

        content = gitignore_path.read_text()
        self.assertIn('.claude/worktrees/', content)


class TestGitignoreSetupDryRun(ScriptTestCase):
    """Test gitignore_setup.py dry-run mode via direct import."""

    bundle = 'plan-marshall'
    skill = 'marshall-steward'
    script = 'gitignore_setup.py'

    def test_dry_run_does_not_create_file(self):
        """Dry-run should not create .gitignore."""
        result = setup_gitignore(self.temp_dir, dry_run=True)
        self.assertEqual(result['status'], 'created')
        self.assertTrue(result['dry_run'])

        # Verify file was NOT created
        gitignore_path = self.temp_dir / '.gitignore'
        self.assertFalse(gitignore_path.exists())

    def test_dry_run_does_not_modify_file(self):
        """Dry-run should not modify existing .gitignore."""
        gitignore_path = self.temp_dir / '.gitignore'
        original_content = '# Original\nnode_modules/\n'
        gitignore_path.write_text(original_content)

        result = setup_gitignore(self.temp_dir, dry_run=True)
        self.assertEqual(result['status'], 'updated')
        self.assertTrue(result['dry_run'])

        # Verify file was NOT modified
        self.assertEqual(gitignore_path.read_text(), original_content)


class TestGitignoreSetupEdgeCases(ScriptTestCase):
    """Test gitignore_setup.py edge cases via direct import."""

    bundle = 'plan-marshall'
    skill = 'marshall-steward'
    script = 'gitignore_setup.py'

    def test_preserves_newline_formatting(self):
        """Should preserve proper newline formatting."""
        gitignore_path = self.temp_dir / '.gitignore'
        gitignore_path.write_text('node_modules/')  # No trailing newline

        result = setup_gitignore(self.temp_dir)
        self.assertEqual(result['status'], 'updated')

        content = gitignore_path.read_text()
        # Should have proper newlines between sections
        self.assertNotIn('node_modules/#', content)  # Should not run together

    def test_check_gitignore_status_function(self):
        """Test the raw check_gitignore_status function."""
        gitignore_path = self.temp_dir / '.gitignore'
        gitignore_path.write_text('.plan/*\n!.plan/marshal.json\n')

        status = check_gitignore_status(gitignore_path)
        self.assertTrue(status['exists'])
        self.assertTrue(status['has_plan_dir'])
        self.assertTrue(status['has_marshal_exception'])
        self.assertFalse(status['has_architecture_exception'])
        self.assertFalse(status['has_claude_worktrees'])


# =============================================================================
# Subprocess (Tier 3) tests -- CLI plumbing only
# =============================================================================


class TestGitignoreSetupCLI(ScriptTestCase):
    """Test CLI plumbing for gitignore_setup.py."""

    bundle = 'plan-marshall'
    skill = 'marshall-steward'
    script = 'gitignore_setup.py'

    def _isolated_env(self) -> dict[str, str]:
        """Env overrides that redirect run-configuration + credential paths.

        Subprocess-invoking tests cannot use pytest's ``monkeypatch`` fixture
        (this is a ``unittest.TestCase`` subclass), so we redirect
        ``PLAN_BASE_DIR`` and ``HOME`` via ``run_script(env_overrides=...)``
        instead. The subprocess reads both at import time, so this pins
        every path-resolving computation to ``self.temp_dir`` — no leaks
        into the real ``.plan/local/run-configuration.json`` or
        ``~/.plan-marshall-credentials/``.
        """
        return {
            'PLAN_BASE_DIR': str(self.temp_dir / '.plan'),
            'HOME': str(self.temp_dir),
        }

    def test_nonexistent_project_root_fails(self):
        """Should fail when project root doesn't exist."""
        nonexistent = self.temp_dir / 'nonexistent'

        result = run_script(
            SCRIPT_PATH,
            '--project-root',
            str(nonexistent),
            env_overrides=self._isolated_env(),
        )
        self.assert_success(result)
        self.assertIn('project_root_not_found', result.stdout)

    def test_toon_output_format(self):
        """Output should be valid TOON format."""
        result = run_script(
            SCRIPT_PATH,
            '--project-root',
            str(self.temp_dir),
            env_overrides=self._isolated_env(),
        )
        self.assert_success(result)

        lines = result.stdout.strip().split('\n')
        self.assertGreaterEqual(len(lines), 3)
        for line in lines:
            self.assertIn(': ', line, f'Line should contain colon-space separator: {line}')


if __name__ == '__main__':
    import unittest

    unittest.main()
