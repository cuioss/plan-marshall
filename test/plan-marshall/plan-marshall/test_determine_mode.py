#!/usr/bin/env python3
"""
Tests for the determine-mode.py script.

Tests both subcommands:
- mode: Determine wizard vs menu mode based on existing files
- check-docs: Check if project docs need required documentation content
"""

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import MARKETPLACE_ROOT, ScriptTestCase, run_script

# Script path to determine-mode.py
SCRIPT_PATH = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'marshall-steward' / 'scripts' / 'determine-mode.py'


class TestModeSubcommand(ScriptTestCase):
    """Test the 'mode' subcommand for operational mode detection."""

    bundle = 'plan-marshall'
    skill = 'marshall-steward'
    script = 'determine-mode.py'

    def test_wizard_mode_when_executor_missing(self):
        """Should return wizard mode when executor is missing."""
        plan_dir = self.temp_dir / '.plan'
        plan_dir.mkdir(parents=True)

        # Create marshal.json but not executor
        (plan_dir / 'marshal.json').write_text('{}')

        result = run_script(SCRIPT_PATH, 'mode', cwd=self.temp_dir)

        self.assert_success(result)
        self.assertIn('mode\twizard', result.stdout)
        self.assertIn('reason\texecutor_missing', result.stdout)

    def test_wizard_mode_when_marshal_missing(self):
        """Should return wizard mode when marshal.json is missing."""
        plan_dir = self.temp_dir / '.plan'
        plan_dir.mkdir(parents=True)

        # Create executor but not marshal.json
        (plan_dir / 'execute-script.py').write_text('# executor script')

        result = run_script(SCRIPT_PATH, 'mode', cwd=self.temp_dir)

        self.assert_success(result)
        self.assertIn('mode\twizard', result.stdout)
        self.assertIn('reason\tmarshal_missing', result.stdout)

    def test_wizard_mode_when_both_missing(self):
        """Should return wizard mode when both are missing."""
        plan_dir = self.temp_dir / '.plan'
        plan_dir.mkdir(parents=True)

        # Neither executor nor marshal.json exists

        result = run_script(SCRIPT_PATH, 'mode', cwd=self.temp_dir)

        self.assert_success(result)
        self.assertIn('mode\twizard', result.stdout)
        self.assertIn('reason\texecutor_missing', result.stdout)

    def test_menu_mode_when_both_exist(self):
        """Should return menu mode when both exist."""
        plan_dir = self.temp_dir / '.plan'
        plan_dir.mkdir(parents=True)

        # Create both executor and marshal.json
        (plan_dir / 'execute-script.py').write_text('# executor script')
        (plan_dir / 'marshal.json').write_text('{}')

        result = run_script(SCRIPT_PATH, 'mode', cwd=self.temp_dir)

        self.assert_success(result)
        self.assertIn('mode\tmenu', result.stdout)
        self.assertIn('reason\tboth_exist', result.stdout)

    def test_default_plan_dir(self):
        """Should use .plan as default directory."""
        # Run from temp dir where .plan doesn't exist
        result = run_script(SCRIPT_PATH, 'mode', cwd=self.temp_dir)

        self.assert_success(result)
        self.assertIn('mode\twizard', result.stdout)

    def test_nonexistent_plan_dir(self):
        """Should return wizard mode for non-existent plan directory."""
        nonexistent_dir = self.temp_dir / 'nonexistent'

        result = run_script(SCRIPT_PATH, 'mode', '--plan-dir', str(nonexistent_dir))

        self.assert_success(result)
        self.assertIn('mode\twizard', result.stdout)
        self.assertIn('reason\texecutor_missing', result.stdout)

    def test_toon_output_format(self):
        """Output should be valid TOON format (tab-separated key-value pairs)."""
        plan_dir = self.temp_dir / '.plan'
        plan_dir.mkdir(parents=True)

        result = run_script(SCRIPT_PATH, 'mode', cwd=self.temp_dir)

        self.assert_success(result)

        lines = result.stdout.strip().split('\n')
        self.assertEqual(len(lines), 2)

        # Each line should be tab-separated key-value
        for line in lines:
            parts = line.split('\t')
            self.assertEqual(len(parts), 2, f'Line should have exactly 2 parts: {line}')


class TestCheckDocsSubcommand(ScriptTestCase):
    """Test the 'check-docs' subcommand for documentation checks."""

    bundle = 'plan-marshall'
    skill = 'marshall-steward'
    script = 'determine-mode.py'

    def test_ok_when_no_docs_exist(self):
        """Should return ok when no documentation files exist."""
        result = run_script(SCRIPT_PATH, 'check-docs', cwd=self.temp_dir)

        self.assert_success(result)
        self.assertIn('status\tok', result.stdout)
        self.assertIn('missing_count\t0', result.stdout)

    def test_ok_when_docs_have_all_patterns(self):
        """Should return ok when docs have all required content."""
        claude_md = self.temp_dir / 'CLAUDE.md'
        claude_md.write_text(
            '# Project\n\nUse `.plan/temp/` for temporary files.\n\nFor file operations use Glob, Read, Grep tools.\n'
        )

        result = run_script(SCRIPT_PATH, 'check-docs', cwd=self.temp_dir)

        self.assert_success(result)
        self.assertIn('status\tok', result.stdout)
        self.assertIn('missing_count\t0', result.stdout)

    def test_needs_update_when_claude_md_missing_plan_temp(self):
        """Should detect missing plan_temp pattern in CLAUDE.md."""
        claude_md = self.temp_dir / 'CLAUDE.md'
        claude_md.write_text('# Project\n\nFor file operations use Glob, Read, Grep tools.\n')

        result = run_script(SCRIPT_PATH, 'check-docs', cwd=self.temp_dir)

        self.assert_success(result)
        self.assertIn('status\tneeds_update', result.stdout)
        self.assertIn('plan_temp\tCLAUDE.md', result.stdout)

    def test_needs_update_when_claude_md_missing_file_ops(self):
        """Should detect missing file_ops pattern in CLAUDE.md."""
        claude_md = self.temp_dir / 'CLAUDE.md'
        claude_md.write_text('# Project\n\nUse .plan/temp for files.\n')

        result = run_script(SCRIPT_PATH, 'check-docs', cwd=self.temp_dir)

        self.assert_success(result)
        self.assertIn('status\tneeds_update', result.stdout)
        self.assertIn('file_ops\tCLAUDE.md', result.stdout)

    def test_needs_update_when_agents_md_missing_plan_temp(self):
        """Should detect missing plan_temp in agents.md."""
        agents_md = self.temp_dir / 'agents.md'
        agents_md.write_text('# Agents\n\nSome other content.\n')

        result = run_script(SCRIPT_PATH, 'check-docs', cwd=self.temp_dir)

        self.assert_success(result)
        self.assertIn('status\tneeds_update', result.stdout)
        self.assertIn('plan_temp\tagents.md', result.stdout)

    def test_needs_update_when_both_missing_all(self):
        """Should list all missing checks across both files."""
        (self.temp_dir / 'CLAUDE.md').write_text('# Project\n')
        (self.temp_dir / 'agents.md').write_text('# Agents\n')

        result = run_script(SCRIPT_PATH, 'check-docs', cwd=self.temp_dir)

        self.assert_success(result)
        self.assertIn('status\tneeds_update', result.stdout)
        # plan_temp missing from both files
        self.assertIn('plan_temp\tCLAUDE.md,agents.md', result.stdout)
        # file_ops missing from CLAUDE.md
        self.assertIn('file_ops\tCLAUDE.md', result.stdout)

    def test_file_ops_not_checked_for_agents_md(self):
        """file_ops should only be checked for CLAUDE.md, not agents.md."""
        # agents.md exists but has no use Glob, Read, Grep — should NOT trigger file_ops
        (self.temp_dir / 'agents.md').write_text('Use .plan/temp for files.\n')

        result = run_script(SCRIPT_PATH, 'check-docs', cwd=self.temp_dir)

        self.assert_success(result)
        # agents.md passes (has plan_temp), and file_ops only checks CLAUDE.md
        self.assertIn('status\tok', result.stdout)

    def test_mixed_files_one_ok_one_missing(self):
        """Should only list files that need updating."""
        # CLAUDE.md has both patterns, agents.md missing plan_temp
        (self.temp_dir / 'CLAUDE.md').write_text(
            'Use .plan/temp for temp files\nFor file operations use Glob, Read, Grep tools\n'
        )
        (self.temp_dir / 'agents.md').write_text('# Agents\n')

        result = run_script(SCRIPT_PATH, 'check-docs', cwd=self.temp_dir)

        self.assert_success(result)
        self.assertIn('status\tneeds_update', result.stdout)
        self.assertIn('missing_count\t1', result.stdout)
        self.assertIn('plan_temp\tagents.md', result.stdout)

    def test_default_project_root(self):
        """Should use current directory as default project root."""
        result = run_script(SCRIPT_PATH, 'check-docs', cwd=self.temp_dir)

        self.assert_success(result)
        self.assertIn('status\tok', result.stdout)

    def test_toon_output_format(self):
        """Output should be valid TOON format."""
        result = run_script(SCRIPT_PATH, 'check-docs', cwd=self.temp_dir)

        self.assert_success(result)

        lines = result.stdout.strip().split('\n')
        self.assertGreaterEqual(len(lines), 2)

        # Each line should be tab-separated key-value
        for line in lines:
            parts = line.split('\t')
            self.assertEqual(len(parts), 2, f'Line should have exactly 2 parts: {line}')

    def test_missing_count_reflects_total_entries(self):
        """missing_count should reflect total number of missing check entries."""
        # CLAUDE.md missing both checks, agents.md missing plan_temp = 3 entries
        (self.temp_dir / 'CLAUDE.md').write_text('# Project\n')
        (self.temp_dir / 'agents.md').write_text('# Agents\n')

        result = run_script(SCRIPT_PATH, 'check-docs', cwd=self.temp_dir)

        self.assert_success(result)
        self.assertIn('missing_count\t3', result.stdout)


class TestSubcommandRequired(ScriptTestCase):
    """Test that subcommand is required."""

    bundle = 'plan-marshall'
    skill = 'marshall-steward'
    script = 'determine-mode.py'

    def test_error_without_subcommand(self):
        """Should error when no subcommand is provided."""
        result = run_script(SCRIPT_PATH)

        self.assertNotEqual(result.returncode, 0)


if __name__ == '__main__':
    import unittest

    unittest.main()
