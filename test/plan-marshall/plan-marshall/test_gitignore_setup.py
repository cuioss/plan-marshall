#!/usr/bin/env python3
"""
Tests for the gitignore-setup.py script.

Tests .gitignore configuration for the planning system:
- Creates new .gitignore if not present
- Updates existing .gitignore with planning entries
- Reports unchanged when entries already exist
- Supports dry-run mode
"""


# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import MARKETPLACE_ROOT, ScriptTestCase, run_script

# Script path to gitignore-setup.py
SCRIPT_PATH = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'marshall-steward' / 'scripts' / 'gitignore-setup.py'


class TestGitignoreSetupCreate(ScriptTestCase):
    """Test gitignore-setup.py creating new .gitignore."""

    bundle = 'plan-marshall'
    skill = 'marshall-steward'
    script = 'gitignore-setup.py'

    def test_creates_gitignore_when_missing(self):
        """Should create new .gitignore with planning entries."""
        result = run_script(SCRIPT_PATH, '--project-root', str(self.temp_dir))

        self.assert_success(result)
        self.assertIn('status\tcreated', result.stdout)
        self.assertIn('entries_added\t3', result.stdout)  # .plan/*, !marshal.json, !project-structure.json

        # Verify file was created
        gitignore_path = self.temp_dir / '.gitignore'
        self.assertTrue(gitignore_path.exists())

        content = gitignore_path.read_text()
        self.assertIn('.plan/', content)
        self.assertIn('!.plan/marshal.json', content)
        self.assertIn('!.plan/project-architecture/', content)
        self.assertIn('# Planning system', content)


class TestGitignoreSetupUpdate(ScriptTestCase):
    """Test gitignore-setup.py updating existing .gitignore."""

    bundle = 'plan-marshall'
    skill = 'marshall-steward'
    script = 'gitignore-setup.py'

    def test_updates_existing_gitignore(self):
        """Should add planning entries to existing .gitignore."""
        gitignore_path = self.temp_dir / '.gitignore'
        gitignore_path.write_text("# Existing content\nnode_modules/\n*.log\n")

        result = run_script(SCRIPT_PATH, '--project-root', str(self.temp_dir))

        self.assert_success(result)
        self.assertIn('status\tupdated', result.stdout)
        self.assertIn('entries_added\t3', result.stdout)  # .plan/*, !marshal.json, !project-structure.json

        # Verify existing content preserved and new content added
        content = gitignore_path.read_text()
        self.assertIn('node_modules/', content)
        self.assertIn('*.log', content)
        self.assertIn('.plan/', content)
        self.assertIn('!.plan/marshal.json', content)
        self.assertIn('!.plan/project-architecture/', content)

    def test_adds_only_missing_entries(self):
        """Should only add entries that are missing."""
        gitignore_path = self.temp_dir / '.gitignore'
        gitignore_path.write_text(".plan/\n")

        result = run_script(SCRIPT_PATH, '--project-root', str(self.temp_dir))

        self.assert_success(result)
        self.assertIn('status\tupdated', result.stdout)
        self.assertIn('entries_added\t2', result.stdout)  # !marshal.json + !project-structure.json

        content = gitignore_path.read_text()
        self.assertIn('!.plan/marshal.json', content)
        self.assertIn('!.plan/project-architecture/', content)


class TestGitignoreSetupUnchanged(ScriptTestCase):
    """Test gitignore-setup.py when no changes needed."""

    bundle = 'plan-marshall'
    skill = 'marshall-steward'
    script = 'gitignore-setup.py'

    def test_unchanged_when_all_entries_exist(self):
        """Should report unchanged when all entries already present."""
        gitignore_path = self.temp_dir / '.gitignore'
        gitignore_path.write_text(".plan/\n!.plan/marshal.json\n!.plan/project-architecture/\n")

        result = run_script(SCRIPT_PATH, '--project-root', str(self.temp_dir))

        self.assert_success(result)
        self.assertIn('status\tunchanged', result.stdout)
        self.assertIn('entries_added\t0', result.stdout)

    def test_recognizes_alternate_plan_format(self):
        """Should recognize .plan without trailing slash."""
        gitignore_path = self.temp_dir / '.gitignore'
        gitignore_path.write_text(".plan\n!.plan/marshal.json\n!.plan/project-architecture/\n")

        result = run_script(SCRIPT_PATH, '--project-root', str(self.temp_dir))

        self.assert_success(result)
        # .plan (without slash) should be recognized as .plan/
        self.assertIn('entries_added\t0', result.stdout)


class TestGitignoreSetupDryRun(ScriptTestCase):
    """Test gitignore-setup.py dry-run mode."""

    bundle = 'plan-marshall'
    skill = 'marshall-steward'
    script = 'gitignore-setup.py'

    def test_dry_run_does_not_create_file(self):
        """Dry-run should not create .gitignore."""
        result = run_script(SCRIPT_PATH, '--project-root', str(self.temp_dir), '--dry-run')

        self.assert_success(result)
        self.assertIn('status\tcreated', result.stdout)
        self.assertIn('dry_run\ttrue', result.stdout)

        # Verify file was NOT created
        gitignore_path = self.temp_dir / '.gitignore'
        self.assertFalse(gitignore_path.exists())

    def test_dry_run_does_not_modify_file(self):
        """Dry-run should not modify existing .gitignore."""
        gitignore_path = self.temp_dir / '.gitignore'
        original_content = "# Original\nnode_modules/\n"
        gitignore_path.write_text(original_content)

        result = run_script(SCRIPT_PATH, '--project-root', str(self.temp_dir), '--dry-run')

        self.assert_success(result)
        self.assertIn('status\tupdated', result.stdout)
        self.assertIn('dry_run\ttrue', result.stdout)

        # Verify file was NOT modified
        self.assertEqual(gitignore_path.read_text(), original_content)


class TestGitignoreSetupEdgeCases(ScriptTestCase):
    """Test gitignore-setup.py edge cases."""

    bundle = 'plan-marshall'
    skill = 'marshall-steward'
    script = 'gitignore-setup.py'

    def test_nonexistent_project_root_fails(self):
        """Should fail when project root doesn't exist."""
        nonexistent = self.temp_dir / 'nonexistent'

        result = run_script(SCRIPT_PATH, '--project-root', str(nonexistent))

        self.assert_failure(result)
        self.assertIn('project_root_not_found', result.stderr)

    def test_preserves_newline_formatting(self):
        """Should preserve proper newline formatting."""
        gitignore_path = self.temp_dir / '.gitignore'
        gitignore_path.write_text("node_modules/")  # No trailing newline

        result = run_script(SCRIPT_PATH, '--project-root', str(self.temp_dir))

        self.assert_success(result)

        content = gitignore_path.read_text()
        # Should have proper newlines between sections
        self.assertNotIn('node_modules/#', content)  # Should not run together

    def test_toon_output_format(self):
        """Output should be valid TOON format."""
        result = run_script(SCRIPT_PATH, '--project-root', str(self.temp_dir))

        self.assert_success(result)

        lines = result.stdout.strip().split('\n')
        self.assertGreaterEqual(len(lines), 3)

        # Each line should be tab-separated key-value
        for line in lines:
            parts = line.split('\t')
            self.assertEqual(len(parts), 2, f"Line should have exactly 2 parts: {line}")


if __name__ == '__main__':
    import unittest
    unittest.main()
