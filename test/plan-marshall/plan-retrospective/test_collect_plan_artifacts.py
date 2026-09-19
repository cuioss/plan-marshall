# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for ``collect-plan-artifacts.py`` under the single-plan-root contract.

Every fragment path resolves from ONE plan root keyed by ``--plan-id``:

- ``live`` mode resolves via ``base_path`` and ignores ``--archived-plan-path``.
- ``archived`` mode honours an explicit ``--archived-plan-path`` and otherwise
  falls back to a synthetic per-plan tmp dir, so audits without an explicit
  archive path never mutate a real archived plan.

Unreadable inputs degrade the block to ``not_evaluated`` with a reason rather
than to a clean verdict — a could-not-look must never carry the same token as
a nothing-to-look-at.
"""

from __future__ import annotations

# Import shared fixture helpers from the sibling module.
from _plan_retrospective_fixtures import setup_archived_plan, setup_live_plan

from conftest import MARKETPLACE_ROOT, run_script

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

    def test_live_mode_ignores_archived_plan_path(self, tmp_path, monkeypatch):
        """Live mode resolves from the single plan root and ignores the archived path."""
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        result = run_script(
            SCRIPT_PATH,
            'run',
            '--plan-id',
            plan_id,
            '--mode',
            'live',
            '--archived-plan-path',
            '/definitely/not/a/plan',
        )
        assert result.success, result.stderr
        data = result.toon()
        assert data['status'] == 'success'
        assert data['plan_id'] == plan_id
        assert str(data['plan_dir']) == str(plan_dir)


class TestArchivedMode:
    """Tests for ``--mode archived`` under the single-root contract."""

    def test_archived_path_resolved_directly(self, tmp_path):
        archived = setup_archived_plan(tmp_path)
        result = run_script(
            SCRIPT_PATH,
            'run',
            '--plan-id',
            'retro-happy',
            '--archived-plan-path',
            str(archived),
            '--mode',
            'archived',
        )
        assert result.success, result.stderr
        data = result.toon()
        assert data['status'] == 'success'
        assert data['mode'] == 'archived'
        assert str(data['plan_dir']) == str(archived)

    def test_archived_without_path_falls_back_to_synthetic_root(self, tmp_path, monkeypatch):
        """No explicit archive path: the synthetic per-plan tmp root is used, and the
        missing dir degrades to not_evaluated rather than erroring or going clean."""
        monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
        plan_id = 'no-such-archive-plan'
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'archived')
        assert result.success, result.stderr
        data = result.toon()
        assert data['status'] == 'not_evaluated'
        assert data['plan_id'] == plan_id
        assert data['reason']

    def test_single_root_exactness_live_matches_archived(self, tmp_path, monkeypatch):
        """The same plan content manifests identically through either mode root."""
        plan_id, _ = setup_live_plan(tmp_path, monkeypatch)
        live = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live').toon()

        import json

        live_dir = tmp_path / 'base' / 'plans' / plan_id
        archived_copy = tmp_path / 'archived-copy'
        import shutil

        shutil.copytree(live_dir, archived_copy)
        archived = run_script(
            SCRIPT_PATH,
            'run',
            '--plan-id',
            plan_id,
            '--archived-plan-path',
            str(archived_copy),
            '--mode',
            'archived',
        ).toon()

        assert archived['status'] == 'success'
        live_paths = sorted(e['path'] for e in live['entries'])
        archived_paths = sorted(e['path'] for e in archived['entries'])
        assert archived_paths == live_paths
        assert json.dumps(archived['by_kind'], sort_keys=True) == json.dumps(live['by_kind'], sort_keys=True)


class TestFaultPaths:
    """Unreadable inputs degrade to not_evaluated, never to a clean verdict."""

    def test_missing_plan_id_in_live_mode_errors(self, tmp_path, monkeypatch):
        monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
        result = run_script(SCRIPT_PATH, 'run', '--mode', 'live')
        assert not result.success

    def test_missing_plan_id_in_archived_mode_errors(self, tmp_path, monkeypatch):
        """Single-root keying: --plan-id is required in archived mode too."""
        monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
        result = run_script(SCRIPT_PATH, 'run', '--mode', 'archived')
        assert not result.success

    def test_missing_archived_path_in_archived_mode_degrades_not_errors(self, tmp_path, monkeypatch):
        """The old missing-archived-path error is now the synthetic-root fallback."""
        monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', 'ghost-plan', '--mode', 'archived')
        assert result.success, result.stderr
        data = result.toon()
        assert data['status'] == 'not_evaluated'
        assert data['reason']

    def test_nonexistent_plan_degrades_to_not_evaluated(self, tmp_path, monkeypatch):
        monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', 'does-not-exist', '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()
        assert data['status'] == 'not_evaluated'
        assert data['reason']
        assert data['entries'] == []
        assert data['total_files'] == 0 or int(data['total_files']) == 0

    def test_not_evaluated_never_reads_clean(self, tmp_path, monkeypatch):
        """A degraded block carries its reason and never an empty-but-success verdict."""
        monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', 'does-not-exist', '--mode', 'live')
        data = result.toon()
        assert data['status'] != 'success'
        assert data['status'] == 'not_evaluated'
        assert isinstance(data['reason'], str) and data['reason'].strip()
