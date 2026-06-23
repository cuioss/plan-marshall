#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""
Tests for the determine_mode.py script.

Tier 2 (direct import) tests with 2 subprocess tests for CLI plumbing.

Tests both subcommands:
- mode: Determine wizard vs menu mode based on existing files
- check-docs: Check if project docs need required documentation content
"""

import copy
import json
from argparse import Namespace

from conftest import MARKETPLACE_ROOT, run_script

SCRIPT_PATH = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'marshall-steward' / 'scripts' / 'determine_mode.py'

from _config_defaults import DEFAULT_PROJECT  # type: ignore[import-not-found]  # noqa: E402
from determine_mode import (  # type: ignore[import-not-found]  # noqa: E402
    check_docs,
    cmd_check_docs,
    cmd_check_working_prefixes,
    cmd_fix_docs,
    cmd_mode,
    detect_working_prefixes_drift,
    determine_mode,
    fix_docs,
)

_DEFAULT_WORKING_PREFIXES = DEFAULT_PROJECT['working_prefixes']


class TestModeSubcommand:
    """Test the 'mode' subcommand via direct import."""

    def test_wizard_mode_when_executor_missing(self, tmp_path):
        """Should return wizard mode when executor is missing."""
        plan_dir = tmp_path / '.plan'
        plan_dir.mkdir(parents=True)
        (plan_dir / 'marshal.json').write_text('{}')

        result = cmd_mode(Namespace(plan_dir=str(plan_dir)))
        assert result['status'] == 'success'
        assert result['mode'] == 'wizard'
        assert result['reason'] == 'executor_missing'

    def test_wizard_mode_when_marshal_missing(self, tmp_path):
        """Should return wizard mode when marshal.json is missing."""
        plan_dir = tmp_path / '.plan'
        plan_dir.mkdir(parents=True)
        (plan_dir / 'execute-script.py').write_text('# executor script')

        result = cmd_mode(Namespace(plan_dir=str(plan_dir)))
        assert result['status'] == 'success'
        assert result['mode'] == 'wizard'
        assert result['reason'] == 'marshal_missing'

    def test_wizard_mode_when_both_missing(self, tmp_path):
        """Should return wizard mode when both are missing."""
        plan_dir = tmp_path / '.plan'
        plan_dir.mkdir(parents=True)

        result = cmd_mode(Namespace(plan_dir=str(plan_dir)))
        assert result['status'] == 'success'
        assert result['mode'] == 'wizard'
        assert result['reason'] == 'executor_missing'

    def test_menu_mode_when_both_exist(self, tmp_path):
        """Should return menu mode when both exist."""
        plan_dir = tmp_path / '.plan'
        plan_dir.mkdir(parents=True)
        (plan_dir / 'execute-script.py').write_text('# executor script')
        (plan_dir / 'marshal.json').write_text('{}')

        result = cmd_mode(Namespace(plan_dir=str(plan_dir)))
        assert result['status'] == 'success'
        assert result['mode'] == 'menu'
        assert result['reason'] == 'both_exist'

    def test_nonexistent_plan_dir(self, tmp_path):
        """Should return wizard mode for non-existent plan directory."""
        nonexistent_dir = tmp_path / 'nonexistent'

        result = cmd_mode(Namespace(plan_dir=str(nonexistent_dir)))
        assert result['status'] == 'success'
        assert result['mode'] == 'wizard'
        assert result['reason'] == 'executor_missing'

    def test_determine_mode_function_directly(self, tmp_path):
        """Test the raw determine_mode function."""
        plan_dir = tmp_path / '.plan'
        plan_dir.mkdir(parents=True)
        mode, reason = determine_mode(plan_dir)
        assert mode == 'wizard'
        assert reason == 'executor_missing'


class TestCheckDocsSubcommand:
    """Test the 'check-docs' subcommand via direct import."""

    def test_ok_when_no_docs_exist(self, tmp_path):
        """Should return ok when no documentation files exist."""
        result = cmd_check_docs(Namespace(project_root=str(tmp_path)))
        assert result['status'] == 'success'
        assert result['check_status'] == 'ok'
        assert result['missing_count'] == 0

    def test_ok_when_docs_have_all_patterns(self, tmp_path):
        """Should return ok when docs have all required content."""
        claude_md = tmp_path / 'CLAUDE.md'
        claude_md.write_text(
            '# Project\n\nUse `.plan/temp/` for temporary files.\n\n'
            'For file operations use Glob, Read, Grep tools.\n'
        )

        result = cmd_check_docs(Namespace(project_root=str(tmp_path)))
        assert result['status'] == 'success'
        assert result['check_status'] == 'ok'
        assert result['missing_count'] == 0

    def test_needs_update_when_claude_md_missing_plan_temp(self, tmp_path):
        """Should detect missing plan_temp pattern in CLAUDE.md."""
        claude_md = tmp_path / 'CLAUDE.md'
        claude_md.write_text('# Project\n\nFor file operations use Glob, Read, Grep tools.\n')

        result = cmd_check_docs(Namespace(project_root=str(tmp_path)))
        assert result['status'] == 'success'
        assert result['check_status'] == 'needs_update'
        assert 'CLAUDE.md' in result.get('plan_temp', '')

    def test_needs_update_when_claude_md_missing_file_ops(self, tmp_path):
        """Should detect missing file_ops pattern in CLAUDE.md."""
        claude_md = tmp_path / 'CLAUDE.md'
        claude_md.write_text('# Project\n\nUse .plan/temp for files.\n')

        result = cmd_check_docs(Namespace(project_root=str(tmp_path)))
        assert result['status'] == 'success'
        assert result['check_status'] == 'needs_update'
        assert 'CLAUDE.md' in result.get('file_ops', '')

    def test_needs_update_when_agents_md_missing_plan_temp(self, tmp_path):
        """Should detect missing plan_temp in agents.md."""
        agents_md = tmp_path / 'agents.md'
        agents_md.write_text('# Agents\n\nSome other content.\n')

        result = cmd_check_docs(Namespace(project_root=str(tmp_path)))
        assert result['status'] == 'success'
        assert result['check_status'] == 'needs_update'
        assert 'agents.md' in result.get('plan_temp', '')

    def test_needs_update_when_both_missing_all(self, tmp_path):
        """Should list all missing checks across both files."""
        (tmp_path / 'CLAUDE.md').write_text('# Project\n')
        (tmp_path / 'agents.md').write_text('# Agents\n')

        result = cmd_check_docs(Namespace(project_root=str(tmp_path)))
        assert result['status'] == 'success'
        assert result['check_status'] == 'needs_update'
        # plan_temp missing from both files
        assert 'CLAUDE.md' in result.get('plan_temp', '')
        assert 'agents.md' in result.get('plan_temp', '')
        # file_ops missing from CLAUDE.md
        assert 'CLAUDE.md' in result.get('file_ops', '')

    def test_file_ops_not_checked_for_agents_md(self, tmp_path):
        """file_ops should only be checked for CLAUDE.md, not agents.md."""
        (tmp_path / 'agents.md').write_text('Use .plan/temp for files.\n')

        result = cmd_check_docs(Namespace(project_root=str(tmp_path)))
        assert result['status'] == 'success'
        assert result['check_status'] == 'ok'

    def test_mixed_files_one_ok_one_missing(self, tmp_path):
        """Should only list files that need updating."""
        (tmp_path / 'CLAUDE.md').write_text(
            'Use .plan/temp for temp files\n'
            'For file operations use Glob, Read, Grep tools\n'
        )
        (tmp_path / 'agents.md').write_text('# Agents\n')

        result = cmd_check_docs(Namespace(project_root=str(tmp_path)))
        assert result['status'] == 'success'
        assert result['check_status'] == 'needs_update'
        assert result['missing_count'] == 1
        assert 'agents.md' in result.get('plan_temp', '')

    def test_missing_count_reflects_total_entries(self, tmp_path):
        """missing_count should reflect total number of missing check entries."""
        # CLAUDE.md missing both checks (plan_temp, file_ops), agents.md missing plan_temp = 3 entries
        (tmp_path / 'CLAUDE.md').write_text('# Project\n')
        (tmp_path / 'agents.md').write_text('# Agents\n')

        result = cmd_check_docs(Namespace(project_root=str(tmp_path)))
        assert result['status'] == 'success'
        assert result['missing_count'] == 3

    def test_check_docs_function_directly(self, tmp_path):
        """Test the raw check_docs function."""
        status, missing = check_docs(tmp_path)
        assert status == 'ok'
        assert missing == []


class TestFixDocsSubcommand:
    """Test the 'fix-docs' subcommand via direct import."""

    def test_ok_when_no_docs_exist(self, tmp_path):
        """Should return ok when no documentation files exist."""
        result = cmd_fix_docs(Namespace(project_root=str(tmp_path)))
        assert result['status'] == 'success'
        assert result['fix_status'] == 'ok'
        assert result['fixed_count'] == 0

    def test_ok_when_docs_already_complete(self, tmp_path):
        """Should return ok when docs already have all required content."""
        claude_md = tmp_path / 'CLAUDE.md'
        claude_md.write_text(
            '# Project\n\nUse `.plan/temp/` for temporary files.\n\n'
            'use Glob, Read, Grep tools.\n'
        )
        result = cmd_fix_docs(Namespace(project_root=str(tmp_path)))
        assert result['fix_status'] == 'ok'
        assert result['fixed_count'] == 0

    def test_fixes_missing_plan_temp_in_claude_md(self, tmp_path):
        """Should append plan_temp content to CLAUDE.md."""
        claude_md = tmp_path / 'CLAUDE.md'
        claude_md.write_text('# Project\n\nuse Glob, Read, Grep tools.\n')
        result = cmd_fix_docs(Namespace(project_root=str(tmp_path)))
        assert result['fix_status'] == 'fixed'
        assert 'plan_temp:CLAUDE.md' in result['fixes']

        content = claude_md.read_text()
        assert '.plan/temp/' in content
        assert 'Write(.plan/**)' in content

    def test_fixes_missing_file_ops(self, tmp_path):
        """Should append file_ops content to CLAUDE.md."""
        claude_md = tmp_path / 'CLAUDE.md'
        claude_md.write_text('# Project\n\nUse .plan/temp for files.\n')
        result = cmd_fix_docs(Namespace(project_root=str(tmp_path)))
        assert result['fix_status'] == 'fixed'
        assert 'file_ops:CLAUDE.md' in result['fixes']

        content = claude_md.read_text()
        assert 'use Glob, Read, Grep' in content

    def test_fixes_multiple_missing_checks(self, tmp_path):
        """Should fix all missing checks in one call."""
        claude_md = tmp_path / 'CLAUDE.md'
        claude_md.write_text('# Project\n')
        result = cmd_fix_docs(Namespace(project_root=str(tmp_path)))
        assert result['fix_status'] == 'fixed'
        assert result['fixed_count'] == 2

        content = claude_md.read_text()
        assert '.plan/temp/' in content
        assert 'use Glob, Read, Grep' in content

    def test_fixes_agents_md_plan_temp(self, tmp_path):
        """Should append plan_temp to agents.md when missing."""
        agents_md = tmp_path / 'agents.md'
        agents_md.write_text('# Agents\n')
        result = cmd_fix_docs(Namespace(project_root=str(tmp_path)))
        assert result['fix_status'] == 'fixed'
        assert 'plan_temp:agents.md' in result['fixes']

        content = agents_md.read_text()
        assert '.plan/temp/' in content

    def test_idempotent_on_second_run(self, tmp_path):
        """Running fix-docs twice should be idempotent."""
        claude_md = tmp_path / 'CLAUDE.md'
        claude_md.write_text('# Project\n')

        cmd_fix_docs(Namespace(project_root=str(tmp_path)))
        result2 = cmd_fix_docs(Namespace(project_root=str(tmp_path)))
        assert result2['fix_status'] == 'ok'
        assert result2['fixed_count'] == 0

    def test_fix_docs_function_directly(self, tmp_path):
        """Test the raw fix_docs function."""
        status, fixes = fix_docs(tmp_path)
        assert status == 'ok'
        assert fixes == []


# =============================================================================
# Subprocess (Tier 3) tests — CLI plumbing only
# =============================================================================


class TestSubcommandRequired:
    """Test that subcommand is required (CLI plumbing)."""

    def test_error_without_subcommand(self):
        """Should error when no subcommand is provided."""
        result = run_script(SCRIPT_PATH)
        assert result.returncode != 0

    def test_toon_output_format(self, tmp_path):
        """Output should be valid TOON format (colon-space key-value pairs)."""
        plan_dir = tmp_path / '.plan'
        plan_dir.mkdir(parents=True)

        result = run_script(SCRIPT_PATH, 'mode', cwd=tmp_path)
        assert result.success, f'Script failed: {result.stderr}'

        lines = result.stdout.strip().split('\n')
        # status, mode, reason = 3 lines
        assert len(lines) == 3
        for line in lines:
            assert ': ' in line, f'Line should contain colon-space separator: {line}'


# =============================================================================
# check-working-prefixes subcommand (project.working_prefixes presence/drift)
# =============================================================================


def _write_marshal(plan_dir, config: dict) -> None:
    """Write a marshal.json fixture under ``plan_dir`` (created on demand)."""
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / 'marshal.json').write_text(json.dumps(config, indent=2), encoding='utf-8')


class TestCheckWorkingPrefixesSubcommand:
    """Test the 'check-working-prefixes' subcommand and its detector."""

    def test_present_and_current_not_flagged(self, tmp_path):
        """A marshal.json whose project.working_prefixes equals the default returns ok."""
        plan_dir = tmp_path / '.plan'
        _write_marshal(plan_dir, {'project': {'working_prefixes': copy.deepcopy(_DEFAULT_WORKING_PREFIXES)}})

        result = cmd_check_working_prefixes(Namespace(plan_dir=str(plan_dir)))

        assert result == {'status': 'ok'}

    def test_absent_key_flagged(self, tmp_path):
        """A project block lacking working_prefixes returns missing/absent."""
        plan_dir = tmp_path / '.plan'
        _write_marshal(plan_dir, {'project': {'default_base_branch': 'main'}})

        result = cmd_check_working_prefixes(Namespace(plan_dir=str(plan_dir)))

        assert result['status'] == 'missing'
        assert result['detail'] == 'absent'
        assert result['missing_keys'] == 'working_prefixes'

    def test_customized_superset_not_clobbered(self, tmp_path):
        """An operator superset (added prefixes) is honoured — never flagged."""
        superset = [*copy.deepcopy(_DEFAULT_WORKING_PREFIXES), 'spike/']
        plan_dir = tmp_path / '.plan'
        _write_marshal(plan_dir, {'project': {'working_prefixes': superset}})

        result = cmd_check_working_prefixes(Namespace(plan_dir=str(plan_dir)))

        assert result == {'status': 'ok'}

    def test_drift_missing_default_entry_flagged(self, tmp_path):
        """A working_prefixes missing a default entry returns missing/drift."""
        drifted = [e for e in copy.deepcopy(_DEFAULT_WORKING_PREFIXES) if e != 'chore/']
        plan_dir = tmp_path / '.plan'
        _write_marshal(plan_dir, {'project': {'working_prefixes': drifted}})

        result = cmd_check_working_prefixes(Namespace(plan_dir=str(plan_dir)))

        assert result['status'] == 'missing'
        assert result['detail'] == 'drift'
        assert result['missing_keys'] == 'working_prefixes'

    def test_missing_marshal_not_flagged(self, tmp_path):
        """No marshal.json present returns ok (graceful degrade)."""
        plan_dir = tmp_path / '.plan'
        plan_dir.mkdir(parents=True)

        result = cmd_check_working_prefixes(Namespace(plan_dir=str(plan_dir)))

        assert result == {'status': 'ok'}

    def test_detect_returns_structured_outcome_for_absent(self, tmp_path):
        """detect_working_prefixes_drift returns the absent outcome with working_prefixes key."""
        plan_dir = tmp_path / '.plan'
        _write_marshal(plan_dir, {'project': {}})

        result = detect_working_prefixes_drift(plan_dir)

        assert result == {'outcome': 'absent', 'missing_keys': ['working_prefixes']}

    def test_cli_plumbing_emits_toon(self, tmp_path):
        """check-working-prefixes via subprocess emits valid TOON for the absent case."""
        plan_dir = tmp_path / '.plan'
        _write_marshal(plan_dir, {'project': {}})

        result = run_script(SCRIPT_PATH, 'check-working-prefixes', '--plan-dir', str(plan_dir))

        assert result.success, f'Script failed: {result.stderr}'
        parsed = result.toon()
        assert parsed['status'] == 'missing'
        assert parsed['detail'] == 'absent'
        assert str(parsed['missing_keys']) == 'working_prefixes'
