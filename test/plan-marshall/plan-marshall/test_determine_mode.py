#!/usr/bin/env python3
"""
Tests for the determine_mode.py script.

Tier 2 (direct import) tests with 2 subprocess tests for CLI plumbing.

Tests both subcommands:
- mode: Determine wizard vs menu mode based on existing files
- check-docs: Check if project docs need required documentation content
"""

from argparse import Namespace

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import MARKETPLACE_ROOT, ScriptTestCase, run_script

# Script path to determine_mode.py
SCRIPT_PATH = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'marshall-steward' / 'scripts' / 'determine_mode.py'

# Tier 2 direct imports — conftest sets up PYTHONPATH for cross-skill imports
from determine_mode import (  # type: ignore[import-not-found]  # noqa: E402
    check_docs,
    cmd_check_docs,
    cmd_mode,
    determine_mode,
)


class TestModeSubcommand(ScriptTestCase):
    """Test the 'mode' subcommand via direct import."""

    bundle = 'plan-marshall'
    skill = 'marshall-steward'
    script = 'determine_mode.py'

    def test_wizard_mode_when_executor_missing(self):
        """Should return wizard mode when executor is missing."""
        plan_dir = self.temp_dir / '.plan'
        plan_dir.mkdir(parents=True)
        (plan_dir / 'marshal.json').write_text('{}')

        result = cmd_mode(Namespace(plan_dir=str(plan_dir)))
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['mode'], 'wizard')
        self.assertEqual(result['reason'], 'executor_missing')

    def test_wizard_mode_when_marshal_missing(self):
        """Should return wizard mode when marshal.json is missing."""
        plan_dir = self.temp_dir / '.plan'
        plan_dir.mkdir(parents=True)
        (plan_dir / 'execute-script.py').write_text('# executor script')

        result = cmd_mode(Namespace(plan_dir=str(plan_dir)))
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['mode'], 'wizard')
        self.assertEqual(result['reason'], 'marshal_missing')

    def test_wizard_mode_when_both_missing(self):
        """Should return wizard mode when both are missing."""
        plan_dir = self.temp_dir / '.plan'
        plan_dir.mkdir(parents=True)

        result = cmd_mode(Namespace(plan_dir=str(plan_dir)))
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['mode'], 'wizard')
        self.assertEqual(result['reason'], 'executor_missing')

    def test_menu_mode_when_both_exist(self):
        """Should return menu mode when both exist."""
        plan_dir = self.temp_dir / '.plan'
        plan_dir.mkdir(parents=True)
        (plan_dir / 'execute-script.py').write_text('# executor script')
        (plan_dir / 'marshal.json').write_text('{}')

        result = cmd_mode(Namespace(plan_dir=str(plan_dir)))
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['mode'], 'menu')
        self.assertEqual(result['reason'], 'both_exist')

    def test_nonexistent_plan_dir(self):
        """Should return wizard mode for non-existent plan directory."""
        nonexistent_dir = self.temp_dir / 'nonexistent'

        result = cmd_mode(Namespace(plan_dir=str(nonexistent_dir)))
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['mode'], 'wizard')
        self.assertEqual(result['reason'], 'executor_missing')

    def test_determine_mode_function_directly(self):
        """Test the raw determine_mode function."""
        plan_dir = self.temp_dir / '.plan'
        plan_dir.mkdir(parents=True)
        mode, reason = determine_mode(plan_dir)
        self.assertEqual(mode, 'wizard')
        self.assertEqual(reason, 'executor_missing')


class TestCheckDocsSubcommand(ScriptTestCase):
    """Test the 'check-docs' subcommand via direct import."""

    bundle = 'plan-marshall'
    skill = 'marshall-steward'
    script = 'determine_mode.py'

    def test_ok_when_no_docs_exist(self):
        """Should return ok when no documentation files exist."""
        result = cmd_check_docs(Namespace(project_root=str(self.temp_dir)))
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['check_status'], 'ok')
        self.assertEqual(result['missing_count'], 0)

    def test_ok_when_docs_have_all_patterns(self):
        """Should return ok when docs have all required content."""
        claude_md = self.temp_dir / 'CLAUDE.md'
        claude_md.write_text(
            '# Project\n\nUse `.plan/temp/` for temporary files.\n\nFor file operations use Glob, Read, Grep tools.\n\n### Workflow Discipline (Hard Rules)\n'
        )

        result = cmd_check_docs(Namespace(project_root=str(self.temp_dir)))
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['check_status'], 'ok')
        self.assertEqual(result['missing_count'], 0)

    def test_needs_update_when_claude_md_missing_plan_temp(self):
        """Should detect missing plan_temp pattern in CLAUDE.md."""
        claude_md = self.temp_dir / 'CLAUDE.md'
        claude_md.write_text('# Project\n\nFor file operations use Glob, Read, Grep tools.\n')

        result = cmd_check_docs(Namespace(project_root=str(self.temp_dir)))
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['check_status'], 'needs_update')
        self.assertIn('CLAUDE.md', result.get('plan_temp', ''))

    def test_needs_update_when_claude_md_missing_file_ops(self):
        """Should detect missing file_ops pattern in CLAUDE.md."""
        claude_md = self.temp_dir / 'CLAUDE.md'
        claude_md.write_text('# Project\n\nUse .plan/temp for files.\n')

        result = cmd_check_docs(Namespace(project_root=str(self.temp_dir)))
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['check_status'], 'needs_update')
        self.assertIn('CLAUDE.md', result.get('file_ops', ''))

    def test_needs_update_when_agents_md_missing_plan_temp(self):
        """Should detect missing plan_temp in agents.md."""
        agents_md = self.temp_dir / 'agents.md'
        agents_md.write_text('# Agents\n\nSome other content.\n')

        result = cmd_check_docs(Namespace(project_root=str(self.temp_dir)))
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['check_status'], 'needs_update')
        self.assertIn('agents.md', result.get('plan_temp', ''))

    def test_needs_update_when_both_missing_all(self):
        """Should list all missing checks across both files."""
        (self.temp_dir / 'CLAUDE.md').write_text('# Project\n')
        (self.temp_dir / 'agents.md').write_text('# Agents\n')

        result = cmd_check_docs(Namespace(project_root=str(self.temp_dir)))
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['check_status'], 'needs_update')
        # plan_temp missing from both files
        self.assertIn('CLAUDE.md', result.get('plan_temp', ''))
        self.assertIn('agents.md', result.get('plan_temp', ''))
        # file_ops missing from CLAUDE.md
        self.assertIn('CLAUDE.md', result.get('file_ops', ''))

    def test_file_ops_not_checked_for_agents_md(self):
        """file_ops should only be checked for CLAUDE.md, not agents.md."""
        (self.temp_dir / 'agents.md').write_text('Use .plan/temp for files.\n')

        result = cmd_check_docs(Namespace(project_root=str(self.temp_dir)))
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['check_status'], 'ok')

    def test_mixed_files_one_ok_one_missing(self):
        """Should only list files that need updating."""
        (self.temp_dir / 'CLAUDE.md').write_text(
            'Use .plan/temp for temp files\nFor file operations use Glob, Read, Grep tools\n### Workflow Discipline\n'
        )
        (self.temp_dir / 'agents.md').write_text('# Agents\n')

        result = cmd_check_docs(Namespace(project_root=str(self.temp_dir)))
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['check_status'], 'needs_update')
        self.assertEqual(result['missing_count'], 1)
        self.assertIn('agents.md', result.get('plan_temp', ''))

    def test_missing_count_reflects_total_entries(self):
        """missing_count should reflect total number of missing check entries."""
        # CLAUDE.md missing all 3 checks, agents.md missing plan_temp = 4 entries
        (self.temp_dir / 'CLAUDE.md').write_text('# Project\n')
        (self.temp_dir / 'agents.md').write_text('# Agents\n')

        result = cmd_check_docs(Namespace(project_root=str(self.temp_dir)))
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['missing_count'], 4)

    def test_check_docs_function_directly(self):
        """Test the raw check_docs function."""
        status, missing = check_docs(self.temp_dir)
        self.assertEqual(status, 'ok')
        self.assertEqual(missing, [])


# =============================================================================
# Subprocess (Tier 3) tests �� CLI plumbing only
# =============================================================================


class TestSubcommandRequired(ScriptTestCase):
    """Test that subcommand is required (CLI plumbing)."""

    bundle = 'plan-marshall'
    skill = 'marshall-steward'
    script = 'determine_mode.py'

    def test_error_without_subcommand(self):
        """Should error when no subcommand is provided."""
        result = run_script(SCRIPT_PATH)
        self.assertNotEqual(result.returncode, 0)

    def test_toon_output_format(self):
        """Output should be valid TOON format (colon-space key-value pairs)."""
        plan_dir = self.temp_dir / '.plan'
        plan_dir.mkdir(parents=True)

        result = run_script(SCRIPT_PATH, 'mode', cwd=self.temp_dir)
        self.assert_success(result)

        lines = result.stdout.strip().split('\n')
        # status, mode, reason = 3 lines
        self.assertEqual(len(lines), 3)
        for line in lines:
            self.assertIn(': ', line, f'Line should contain colon-space separator: {line}')


if __name__ == '__main__':
    import unittest

    unittest.main()
