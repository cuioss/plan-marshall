"""Tests for ``analyze-logs.py``."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _fixtures import setup_archived_plan, setup_broken_plan, setup_live_plan  # noqa: E402

from conftest import MARKETPLACE_ROOT, run_script  # noqa: E402

SCRIPT_PATH = (
    MARKETPLACE_ROOT
    / 'plan-marshall'
    / 'skills'
    / 'plan-retrospective'
    / 'scripts'
    / 'analyze-logs.py'
)


# Direct import of analyze-logs.py (hyphenated filename → importlib). Used by
# the regression tests below that call ``read_log`` in-process so they can
# capture stderr WARN lines reliably without shell-level quoting noise.
_spec = importlib.util.spec_from_file_location('analyze_logs', str(SCRIPT_PATH))
assert _spec is not None and _spec.loader is not None
_analyze_logs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_analyze_logs)
read_log = _analyze_logs.read_log


class TestHappyPath:
    def test_counts_log_entries_by_level(self, tmp_path, monkeypatch):
        plan_id, _ = setup_live_plan(tmp_path, monkeypatch)
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()

        assert data['status'] == 'success'
        assert data['aspect'] == 'log_analysis'
        counts = data['counts']
        assert int(counts['work_entries']) == 3
        assert int(counts['warnings_work']) == 1
        assert int(counts['script_entries']) == 3
        assert int(counts['errors_script']) == 1

    def test_phases_seen_extracted_from_logs(self, tmp_path, monkeypatch):
        plan_id, _ = setup_live_plan(tmp_path, monkeypatch)
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        data = result.toon()
        phases = data['phases_seen']
        assert '1-init' in phases
        assert '3-outline' in phases
        assert '5-execute' in phases

    def test_script_durations_percentiles(self, tmp_path, monkeypatch):
        plan_id, _ = setup_live_plan(tmp_path, monkeypatch)
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        data = result.toon()
        assert float(data['script_duration_max_ms']) >= 2500.0

    def test_slowest_scripts_ordered_desc(self, tmp_path, monkeypatch):
        plan_id, _ = setup_live_plan(tmp_path, monkeypatch)
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        data = result.toon()
        slowest = data['slowest_scripts']
        assert slowest[0]['notation'] == 'plan-marshall:manage-status:manage_status'


class TestFaultPaths:
    def test_missing_logs_dir_returns_zero_counts(self, tmp_path, monkeypatch):
        plan_id, _ = setup_broken_plan(tmp_path, monkeypatch)
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()
        counts = data['counts']
        assert int(counts['work_entries']) == 0
        assert int(counts['script_entries']) == 0


class TestArchivedMode:
    def test_archived_plan_path_reads_logs(self, tmp_path):
        archived = setup_archived_plan(tmp_path)
        result = run_script(
            SCRIPT_PATH, 'run', '--archived-plan-path', str(archived), '--mode', 'archived'
        )
        assert result.success, result.stderr
        data = result.toon()
        assert data['status'] == 'success'
        assert int(data['counts']['work_entries']) == 3


class TestRegression:
    """Regression tests that lock in the production-shape bug fixes.

    The parent plan was triggered by four concrete defects: among them,
    ``analyze-logs`` was reading the wrong filename so ``errors_script``
    came back zero even when the script-execution log had ERROR entries,
    and ``read_log`` silently returned [] for missing log files which hid
    log-source drift from the retrospective. These tests fail whenever
    either regression reappears.
    """

    def test_errors_script_counts_three_error_entries(self, tmp_path, monkeypatch):
        """A ``script-execution.log`` with 3 ERROR lines must produce
        ``counts.errors_script == 3``. Before the fix, analyze-logs read
        from ``script.log`` and this counter was always 0.
        """
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch, plan_id='retro-errors-script')
        logs_dir = plan_dir / 'logs'
        logs_dir.mkdir(exist_ok=True)
        # Overwrite the happy-path fixture (1 ERROR) with a 3-ERROR log to
        # exercise the counter exactly. Filename MUST match what
        # ``analyze-logs`` reads — ``script-execution.log`` per the fix.
        (logs_dir / 'script-execution.log').write_text(
            '2026-04-17T10:00:01Z ERROR plan-marshall:manage-tasks:manage-tasks add (0.12s)\n'
            '2026-04-17T10:00:02Z ERROR plan-marshall:manage-status:manage_status read (2.5s)\n'
            '2026-04-17T10:00:10Z ERROR plan-marshall:manage-files:manage-files add (0.05s)\n',
            encoding='utf-8',
        )
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()
        assert int(data['counts']['errors_script']) == 3, (
            f'Expected errors_script == 3 on a 3-ERROR script-execution.log, '
            f'got {data["counts"]["errors_script"]}. This regression means '
            f'analyze-logs is reading the wrong filename again.'
        )

    def test_read_log_missing_path_emits_stderr_warn(self, tmp_path, capsys):
        """``read_log`` must surface a stderr WARN line (not silently
        return []) when the target file is missing. Silent-swallowing
        hides log-source drift from the retrospective reader.
        """
        missing_path = tmp_path / 'definitely-not-a-real-log.log'
        assert not missing_path.exists()

        # Act: call read_log directly so we get clean stderr capture.
        result = read_log(missing_path)

        # Assert: empty list for missing file is still the contract, but
        # the stderr WARN line MUST be present so operators notice.
        assert result == []
        captured = capsys.readouterr()
        assert 'WARN' in captured.err, (
            f'read_log on missing path must emit stderr WARN; got stderr: '
            f'{captured.err!r}'
        )
        assert str(missing_path) in captured.err, (
            'WARN line must include the missing path for operator debugging'
        )
