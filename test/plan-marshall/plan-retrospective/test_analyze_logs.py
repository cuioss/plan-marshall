"""Tests for ``analyze-logs.py``."""

from __future__ import annotations

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
