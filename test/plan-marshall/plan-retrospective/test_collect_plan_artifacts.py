"""Tests for ``collect-plan-artifacts.py``."""

from __future__ import annotations

# Import shared fixture helpers from the sibling module.
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _fixtures import setup_archived_plan, setup_live_plan  # noqa: E402

from conftest import MARKETPLACE_ROOT, run_script  # noqa: E402

SCRIPT_PATH = (
    MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'plan-retrospective' / 'scripts' / 'collect-plan-artifacts.py'
)


class TestLiveMode:
    """Tests for ``--mode live`` with a happy-path plan directory."""

    def test_classifies_standard_artifacts(self, tmp_path, monkeypatch):
        plan_id, _ = setup_live_plan(tmp_path, monkeypatch)
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()

        assert data['status'] == 'success'
        assert data['mode'] == 'live'
        assert data['plan_id'] == plan_id
        assert int(data['total_files']) >= 8

        by_kind = data['by_kind']
        for kind in ('status', 'solution_outline', 'references', 'metrics', 'request', 'tasks', 'logs'):
            assert kind in by_kind, f'missing kind {kind}: {by_kind}'

    def test_lists_all_files_with_relative_paths(self, tmp_path, monkeypatch):
        plan_id, _ = setup_live_plan(tmp_path, monkeypatch)
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        data = result.toon()
        entries = data['entries']
        assert isinstance(entries, list)
        for entry in entries:
            assert not entry['path'].startswith('/'), entry


class TestArchivedMode:
    """Tests for ``--mode archived``."""

    def test_archived_path_resolved_directly(self, tmp_path):
        archived = setup_archived_plan(tmp_path)
        result = run_script(SCRIPT_PATH, 'run', '--archived-plan-path', str(archived), '--mode', 'archived')
        assert result.success, result.stderr
        data = result.toon()
        assert data['status'] == 'success'
        assert data['mode'] == 'archived'
        assert str(data['plan_dir']) == str(archived)


class TestFaultPaths:
    """Tests for invalid invocations."""

    def test_missing_plan_id_in_live_mode_errors(self, tmp_path, monkeypatch):
        monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
        result = run_script(SCRIPT_PATH, 'run', '--mode', 'live')
        assert not result.success

    def test_missing_archived_path_in_archived_mode_errors(self, tmp_path, monkeypatch):
        monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
        result = run_script(SCRIPT_PATH, 'run', '--mode', 'archived')
        assert not result.success

    def test_nonexistent_plan_errors(self, tmp_path, monkeypatch):
        monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', 'does-not-exist', '--mode', 'live')
        assert not result.success
