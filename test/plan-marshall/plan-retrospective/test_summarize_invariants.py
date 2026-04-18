"""Tests for ``summarize-invariants.py``."""

from __future__ import annotations

import json
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
    / 'summarize-invariants.py'
)


class TestHappyPath:
    def test_extracts_phase_invariants(self, tmp_path, monkeypatch):
        plan_id, _ = setup_live_plan(tmp_path, monkeypatch)
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()

        assert data['status'] == 'success'
        assert data['aspect'] == 'invariant_summary'
        phases = data['phases']
        phase_names = [p['phase'] for p in phases]
        assert '1-init' in phase_names
        assert '6-finalize' in phase_names

    def test_does_not_re_run_capture(self, tmp_path, monkeypatch):
        """The script must read ``status.metadata.phase_handshake`` verbatim.

        We inject a synthetic SHA no real capture would produce and confirm
        the script surfaces the metadata without round-tripping through
        ``manage-status``.
        """
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        status_path = plan_dir / 'status.json'
        status = json.loads(status_path.read_text())
        status['metadata']['phase_handshake']['1-init']['main_sha'] = 'synthetic-sha'
        status_path.write_text(json.dumps(status))

        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()
        init_phase = next(p for p in data['phases'] if p['phase'] == '1-init')
        assert 'main_sha' in init_phase['invariants_present']


class TestFaultInjection:
    def test_missing_metadata_emits_warning(self, tmp_path, monkeypatch):
        plan_id, _ = setup_broken_plan(tmp_path, monkeypatch)
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()
        findings = data['findings']
        messages = [f.get('message', '') for f in findings]
        assert any('phase_handshake' in m.lower() or 'no phase' in m.lower() for m in messages)

    def test_malformed_status_json_treated_as_empty(self, tmp_path, monkeypatch):
        """A corrupt status.json must not crash — missing metadata is a warning."""
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        status_path = plan_dir / 'status.json'
        status_path.write_text('{ not valid json', encoding='utf-8')

        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()
        # Corrupt status means load_status returns {}; extract_phase_map
        # yields {} so the script emits the no-phase_handshake warning
        # rather than propagating a parse error.
        assert data['phases'] == []
        assert any(
            'phase_handshake' in f.get('message', '').lower()
            for f in data['findings']
        )


class TestDriftDetection:
    def test_main_sha_drift_flagged(self, tmp_path, monkeypatch):
        """A main_sha change between phases must produce a drift finding."""
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        status_path = plan_dir / 'status.json'
        status = json.loads(status_path.read_text())
        # Deliberately diverge main_sha between init and finalize. The fixture
        # starts with matching values; changing one exercises detect_drift.
        status['metadata']['phase_handshake']['6-finalize']['main_sha'] = 'drifted-sha'
        status_path.write_text(json.dumps(status))

        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()
        drift = data['drift']
        assert any(d.get('invariant') == 'main_sha' for d in drift), drift

    def test_main_dirty_excluded_from_drift(self, tmp_path, monkeypatch):
        """``main_dirty`` varies naturally and must not generate drift."""
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        status_path = plan_dir / 'status.json'
        status = json.loads(status_path.read_text())
        status['metadata']['phase_handshake']['6-finalize']['main_dirty'] = '1'
        status_path.write_text(json.dumps(status))

        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        data = result.toon()
        # main_dirty is in the exclusion set inside detect_drift.
        assert not any(d.get('invariant') == 'main_dirty' for d in data['drift'])


class TestExpectedInvariants:
    def test_worktree_plan_expects_worktree_invariants(self, tmp_path, monkeypatch):
        """When metadata.worktree_path is set, worktree invariants are expected."""
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        status_path = plan_dir / 'status.json'
        status = json.loads(status_path.read_text())
        status['metadata']['worktree_path'] = '/tmp/some/worktree'
        status_path.write_text(json.dumps(status))

        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()
        expected = data['expected_invariants']
        assert 'worktree_sha' in expected
        assert 'worktree_dirty' in expected

    def test_non_worktree_plan_omits_worktree_invariants(self, tmp_path, monkeypatch):
        """Without worktree_path, worktree_* invariants are not in expected."""
        plan_id, _ = setup_live_plan(tmp_path, monkeypatch)
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        data = result.toon()
        expected = data['expected_invariants']
        assert 'worktree_sha' not in expected
        assert 'worktree_dirty' not in expected


class TestArchivedMode:
    def test_archived_plan_summary(self, tmp_path):
        archived = setup_archived_plan(tmp_path)
        result = run_script(
            SCRIPT_PATH, 'run', '--archived-plan-path', str(archived), '--mode', 'archived'
        )
        assert result.success, result.stderr
        data = result.toon()
        assert data['status'] == 'success'
        assert len(data['phases']) == 2
