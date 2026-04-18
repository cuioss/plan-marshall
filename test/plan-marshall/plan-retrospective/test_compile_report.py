"""Tests for ``compile-report.py``."""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _fixtures import setup_archived_plan, setup_live_plan  # noqa: E402

from conftest import MARKETPLACE_ROOT, run_script  # noqa: E402

SCRIPT_PATH = (
    MARKETPLACE_ROOT
    / 'plan-marshall'
    / 'skills'
    / 'plan-retrospective'
    / 'scripts'
    / 'compile-report.py'
)


def _write_fragments(tmp_path: Path, with_failure_aspects: bool = False) -> Path:
    """Write a minimal TOON fragments bundle.

    The conditional aspects include at least one ``failures``/``prompts``
    item so ``should_emit`` recognizes them as non-empty.
    """
    lines = [
        '_executive_summary:',
        '  summary: "All green. 2 warnings worth reviewing."',
        'request_result_alignment:',
        '  status: success',
        '  aspect: request_result_alignment',
        'artifact_consistency:',
        '  status: success',
        '  aspect: artifact_consistency',
        'log_analysis:',
        '  status: success',
        '  aspect: log_analysis',
        'invariant_summary:',
        '  status: success',
        '  aspect: invariant_summary',
        'plan_efficiency:',
        '  status: success',
        '  aspect: plan_efficiency',
        'llm_to_script_opportunities:',
        '  status: success',
        '  aspect: llm_to_script_opportunities',
        'logging_gap_analysis:',
        '  status: success',
        '  aspect: logging_gap_analysis',
        'lessons_proposal:',
        '  status: success',
        '  aspect: lessons_proposal',
    ]
    if with_failure_aspects:
        lines.extend([
            'script_failure_analysis:',
            '  status: success',
            '  aspect: script_failure_analysis',
            '  failures[1]{notation,exit_code}:',
            '    plan-marshall:foo:bar,1',
            'permission_prompt_analysis:',
            '  status: success',
            '  aspect: permission_prompt_analysis',
            '  prompts[1]{tool,resource}:',
            '    Bash,some-command',
        ])
    fragments_file = tmp_path / 'fragments.toon'
    fragments_file.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return fragments_file


class TestLiveMode:
    def test_writes_quality_verification_document(self, tmp_path, monkeypatch):
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        fragments = _write_fragments(tmp_path)

        result = run_script(
            SCRIPT_PATH,
            'run',
            '--plan-id',
            plan_id,
            '--mode',
            'live',
            '--fragments-file',
            str(fragments),
        )
        assert result.success, result.stderr
        data = result.toon()
        assert data['status'] == 'success'
        expected = plan_dir / 'quality-verification-report.md'
        assert Path(data['output_path']) == expected
        assert expected.exists()
        content = expected.read_text(encoding='utf-8')
        assert f'Plan Retrospective — {plan_id}' in content
        assert 'Executive Summary' in content
        assert 'mode: live' in content

    def test_conditional_sections_omitted_when_empty(self, tmp_path, monkeypatch):
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        fragments = _write_fragments(tmp_path, with_failure_aspects=False)

        result = run_script(
            SCRIPT_PATH,
            'run',
            '--plan-id',
            plan_id,
            '--mode',
            'live',
            '--fragments-file',
            str(fragments),
        )
        assert result.success, result.stderr
        data = result.toon()
        omitted = data['sections_omitted']
        assert 'Script Failure Analysis' in omitted
        assert 'Permission Prompt Analysis' in omitted
        content = (plan_dir / 'quality-verification-report.md').read_text()
        assert 'Script Failure Analysis' not in content
        assert 'Permission Prompt Analysis' not in content

    def test_conditional_sections_emitted_when_data_present(self, tmp_path, monkeypatch):
        plan_id, _ = setup_live_plan(tmp_path, monkeypatch)
        fragments = _write_fragments(tmp_path, with_failure_aspects=True)

        result = run_script(
            SCRIPT_PATH,
            'run',
            '--plan-id',
            plan_id,
            '--mode',
            'live',
            '--fragments-file',
            str(fragments),
        )
        assert result.success, result.stderr
        data = result.toon()
        written = data['sections_written']
        assert 'Script Failure Analysis' in written
        assert 'Permission Prompt Analysis' in written


class TestArchivedMode:
    def test_archived_mode_writes_audit_filename(self, tmp_path):
        archived = setup_archived_plan(tmp_path)
        fragments = _write_fragments(tmp_path)
        result = run_script(
            SCRIPT_PATH,
            'run',
            '--archived-plan-path',
            str(archived),
            '--mode',
            'archived',
            '--fragments-file',
            str(fragments),
        )
        assert result.success, result.stderr
        data = result.toon()
        output_path = Path(data['output_path'])
        assert output_path.parent == archived
        assert output_path.name.startswith('quality-verification-report-audit-')
        assert output_path.name.endswith('.md')

    def test_archived_mode_does_not_overwrite(self, tmp_path):
        archived = setup_archived_plan(tmp_path)
        fragments = _write_fragments(tmp_path)
        result_a = run_script(
            SCRIPT_PATH,
            'run',
            '--archived-plan-path',
            str(archived),
            '--mode',
            'archived',
            '--fragments-file',
            str(fragments),
        )
        data_a = result_a.toon()
        time.sleep(1.1)
        result_b = run_script(
            SCRIPT_PATH,
            'run',
            '--archived-plan-path',
            str(archived),
            '--mode',
            'archived',
            '--fragments-file',
            str(fragments),
        )
        data_b = result_b.toon()
        assert data_a['output_path'] != data_b['output_path']
        assert Path(data_a['output_path']).exists()
        assert Path(data_b['output_path']).exists()


class TestFaultPaths:
    def test_missing_fragments_file_errors(self, tmp_path, monkeypatch):
        plan_id, _ = setup_live_plan(tmp_path, monkeypatch)
        result = run_script(
            SCRIPT_PATH,
            'run',
            '--plan-id',
            plan_id,
            '--mode',
            'live',
            '--fragments-file',
            str(tmp_path / 'does-not-exist.toon'),
        )
        assert not result.success


class TestSessionIdPassthrough:
    def test_session_id_written_to_header_when_provided(self, tmp_path, monkeypatch):
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        fragments = _write_fragments(tmp_path)
        result = run_script(
            SCRIPT_PATH,
            'run',
            '--plan-id',
            plan_id,
            '--mode',
            'live',
            '--fragments-file',
            str(fragments),
            '--session-id',
            'abc-123',
        )
        assert result.success, result.stderr
        content = (plan_dir / 'quality-verification-report.md').read_text()
        assert 'session_id: abc-123' in content

    def test_session_id_default_string_when_missing(self, tmp_path, monkeypatch):
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        fragments = _write_fragments(tmp_path)
        run_script(
            SCRIPT_PATH,
            'run',
            '--plan-id',
            plan_id,
            '--mode',
            'live',
            '--fragments-file',
            str(fragments),
        )
        content = (plan_dir / 'quality-verification-report.md').read_text()
        assert 'session_id: not provided' in content
