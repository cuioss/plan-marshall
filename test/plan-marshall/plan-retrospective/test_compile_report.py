"""Tests for ``compile-report.py``."""

from __future__ import annotations

import importlib.util
import sys
import time
from argparse import Namespace
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

# Direct import of compile-report.py (hyphenated filename → importlib). This
# gives the cleanup tests access to cmd_run and Path.unlink from the same
# namespace the script uses, so monkeypatching affects the production code.
_spec = importlib.util.spec_from_file_location('compile_report', str(SCRIPT_PATH))
assert _spec is not None and _spec.loader is not None
_compile_report = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_compile_report)
cmd_run = _compile_report.cmd_run


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
        # compile-report auto-deletes the fragments bundle on success, so
        # each invocation needs its own freshly-written bundle.
        fragments_a = _write_fragments(tmp_path)
        result_a = run_script(
            SCRIPT_PATH,
            'run',
            '--archived-plan-path',
            str(archived),
            '--mode',
            'archived',
            '--fragments-file',
            str(fragments_a),
        )
        data_a = result_a.toon()
        time.sleep(1.1)
        fragments_b = _write_fragments(tmp_path)
        result_b = run_script(
            SCRIPT_PATH,
            'run',
            '--archived-plan-path',
            str(archived),
            '--mode',
            'archived',
            '--fragments-file',
            str(fragments_b),
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


def _run_args(
    mode: str,
    fragments_path: Path,
    plan_id: str | None = None,
    archived_plan_path: Path | None = None,
    session_id: str | None = None,
) -> Namespace:
    """Build the ``argparse.Namespace`` that ``cmd_run`` expects."""
    return Namespace(
        command='run',
        plan_id=plan_id,
        archived_plan_path=str(archived_plan_path) if archived_plan_path else None,
        mode=mode,
        fragments_file=str(fragments_path),
        session_id=session_id,
        func=cmd_run,
    )


class TestFragmentBundleCleanup:
    """Task-4 coverage: fragment-bundle cleanup on cmd_run success vs failure."""

    def test_bundle_deleted_after_successful_live_run(self, tmp_path, monkeypatch):
        # Arrange
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        fragments = _write_fragments(tmp_path)
        assert fragments.exists()

        # Act
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

        # Assert
        assert result.success, result.stderr
        assert (plan_dir / 'quality-verification-report.md').exists()
        assert not fragments.exists(), 'Fragments bundle should be deleted after successful live run'

    def test_bundle_deleted_after_successful_archived_run(self, tmp_path):
        # Arrange
        archived = setup_archived_plan(tmp_path)
        fragments = _write_fragments(tmp_path)
        assert fragments.exists()

        # Act
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

        # Assert
        assert result.success, result.stderr
        output_path = Path(result.toon()['output_path'])
        assert output_path.exists()
        assert not fragments.exists(), 'Fragments bundle should be deleted after successful archived run'

    def test_bundle_persists_when_cmd_run_raises_before_write(self, tmp_path, monkeypatch):
        # Arrange: create a live-mode plan directory, then point the script at
        # a non-existent plan_id so resolve_plan_dir() → plan_dir.exists() is
        # False and cmd_run raises ValueError BEFORE reaching the markdown
        # write (and therefore before the cleanup block).
        setup_live_plan(tmp_path, monkeypatch, plan_id='retro-happy')
        fragments = _write_fragments(tmp_path)
        assert fragments.exists()
        missing_plan_id = 'plan-that-does-not-exist'

        # Act
        result = run_script(
            SCRIPT_PATH,
            'run',
            '--plan-id',
            missing_plan_id,
            '--mode',
            'live',
            '--fragments-file',
            str(fragments),
        )

        # Assert: script errored AND bundle still exists on disk for debugging
        assert not result.success
        assert fragments.exists(), 'Fragments bundle must persist when cmd_run raises before the markdown write'

    def test_cleanup_tolerates_missing_bundle_silently(self, tmp_path, monkeypatch, capsys):
        # Arrange: call cmd_run in-process so we can monkeypatch Path.unlink.
        # The real fragments file exists during load_fragments; unlink raises
        # FileNotFoundError, simulating "bundle already removed" races.
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        fragments = _write_fragments(tmp_path)

        original_unlink = Path.unlink

        def fake_unlink(self, *args, **kwargs):
            if self == fragments:
                raise FileNotFoundError(str(self))
            return original_unlink(self, *args, **kwargs)

        monkeypatch.setattr(Path, 'unlink', fake_unlink)

        # Act
        cmd_run(_run_args('live', fragments, plan_id=plan_id))

        # Assert: no raise (test would fail otherwise), no stderr warning
        captured = capsys.readouterr()
        assert 'WARN' not in captured.err
        assert 'failed to delete fragments bundle' not in captured.err
        # Markdown was still written since unlink failure is silent-tolerated
        assert (plan_dir / 'quality-verification-report.md').exists()

    def test_cleanup_logs_warning_on_permission_error(self, tmp_path, monkeypatch, capsys):
        # Arrange: PermissionError (non-FileNotFoundError OSError) must be
        # logged to stderr but MUST NOT abort cmd_run.
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        fragments = _write_fragments(tmp_path)

        original_unlink = Path.unlink

        def fake_unlink(self, *args, **kwargs):
            if self == fragments:
                raise PermissionError(f'permission denied: {self}')
            return original_unlink(self, *args, **kwargs)

        monkeypatch.setattr(Path, 'unlink', fake_unlink)

        # Act: cmd_run should complete successfully despite the unlink failure
        result = cmd_run(_run_args('live', fragments, plan_id=plan_id))

        # Assert: success path, stderr carries the WARN line
        assert result['status'] == 'success'
        assert (plan_dir / 'quality-verification-report.md').exists()
        captured = capsys.readouterr()
        assert 'WARN' in captured.err
        assert 'failed to delete fragments bundle' in captured.err
        assert str(fragments) in captured.err

