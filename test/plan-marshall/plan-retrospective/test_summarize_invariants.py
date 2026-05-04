"""Tests for ``summarize-invariants.py``.

The script reads phase-handshake captures from ``<plan_dir>/handshakes.toon``
(canonical storage owned by ``plan-marshall:plan-marshall:phase_handshake``)
rather than ``status.metadata.phase_handshake``. Fixtures in ``_fixtures.py``
materialize the file in the same TOON shape ``_handshake_store.save_rows``
emits in production.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _fixtures import (  # noqa: E402
    _HAPPY_HANDSHAKE_ROWS,
    setup_archived_plan,
    setup_broken_plan,
    setup_live_plan,
    write_handshakes,
)

from conftest import MARKETPLACE_ROOT, run_script  # noqa: E402

SCRIPT_PATH = (
    MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'plan-retrospective' / 'scripts' / 'summarize-invariants.py'
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
        """The script must read ``handshakes.toon`` verbatim.

        We inject a synthetic SHA no real capture would produce and confirm
        the script surfaces the row without round-tripping through
        ``phase_handshake capture``.
        """
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        rows = [dict(r) for r in _HAPPY_HANDSHAKE_ROWS]
        rows[0]['main_sha'] = 'synthetic-sha'
        write_handshakes(plan_dir, plan_id=plan_id, rows=rows)

        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()
        init_phase = next(p for p in data['phases'] if p['phase'] == '1-init')
        assert 'main_sha' in init_phase['invariants_present']

    def test_full_handshakes_produces_no_phase_handshake_findings(self, tmp_path, monkeypatch):
        """A fully-populated handshakes.toon must yield zero ``phase_handshake`` findings.

        Positive case: the canonical missing-data warning
        ``"No handshakes.toon found"`` is only emitted when the file is
        absent or empty. With both happy-path rows present, the only
        possible findings are ``invariants_missing`` per phase or drift —
        not the bulk ``phase_handshake`` warning.
        """
        plan_id, _ = setup_live_plan(tmp_path, monkeypatch)
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()
        bulk = [f for f in data['findings'] if f.get('invariant') == 'phase_handshake']
        assert bulk == [], f'fully-populated handshakes.toon must not produce phase_handshake findings, got {bulk}'


class TestFaultInjection:
    def test_missing_handshakes_emits_canonical_warning(self, tmp_path, monkeypatch):
        """A plan without ``handshakes.toon`` produces the canonical warning.

        ``setup_broken_plan`` does not write handshakes.toon, so the script
        must emit exactly the ``No handshakes.toon found`` finding.
        """
        plan_id, _ = setup_broken_plan(tmp_path, monkeypatch)
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()
        messages = [f.get('message', '') for f in data['findings']]
        assert 'No handshakes.toon found' in messages, f'expected canonical warning, got messages: {messages}'

    def test_handshakes_toon_deleted_emits_warning(self, tmp_path, monkeypatch):
        """If the handshakes file is deleted post-setup, the warning fires.

        Removing the file must not crash the script — it must surface the
        same canonical missing-data finding.
        """
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        handshakes = plan_dir / 'handshakes.toon'
        assert handshakes.exists(), 'fixture must have written handshakes.toon'
        handshakes.unlink()

        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()
        assert data['phases'] == []
        messages = [f.get('message', '') for f in data['findings']]
        assert 'No handshakes.toon found' in messages, messages

    def test_malformed_status_json_treated_as_empty(self, tmp_path, monkeypatch):
        """A corrupt status.json must not crash the script.

        ``status.json`` only contributes worktree-detection metadata; even if
        it fails to parse, the run should complete (using the default
        non-worktree expected-invariants set) and surface the per-phase
        rows from ``handshakes.toon`` as usual.
        """
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        status_path = plan_dir / 'status.json'
        status_path.write_text('{ not valid json', encoding='utf-8')

        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()
        # handshakes.toon is intact, so phase rows are still returned.
        phase_names = [p['phase'] for p in data['phases']]
        assert phase_names == ['1-init', '6-finalize'], phase_names
        # No bulk missing-data warning when handshakes.toon is present.
        bulk = [f for f in data['findings'] if f.get('invariant') == 'phase_handshake']
        assert bulk == [], bulk


class TestDriftDetection:
    def test_main_sha_drift_flagged(self, tmp_path, monkeypatch):
        """A main_sha change between phases must produce a drift finding."""
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        rows = [dict(r) for r in _HAPPY_HANDSHAKE_ROWS]
        # Deliberately diverge main_sha between init and finalize. The fixture
        # starts with matching values; changing one exercises detect_drift.
        rows[1]['main_sha'] = 'drifted-sha'
        write_handshakes(plan_dir, plan_id=plan_id, rows=rows)

        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()
        drift = data['drift']
        assert any(d.get('invariant') == 'main_sha' for d in drift), drift

    def test_main_dirty_excluded_from_drift(self, tmp_path, monkeypatch):
        """``main_dirty`` varies naturally and must not generate drift."""
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        rows = [dict(r) for r in _HAPPY_HANDSHAKE_ROWS]
        rows[1]['main_dirty'] = '1'
        write_handshakes(plan_dir, plan_id=plan_id, rows=rows)

        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        data = result.toon()
        # main_dirty is in the exclusion set inside detect_drift.
        assert not any(d.get('invariant') == 'main_dirty' for d in data['drift'])

    def test_pending_tasks_count_excluded_from_drift(self, tmp_path, monkeypatch):
        """``pending_tasks_count`` naturally drains across phases — not drift.

        The capture column is meaningful for the phase-5-execute transition
        guard and as a retrospective signal of orphaned fix tasks, but a
        change between phases is expected (the queue should drain). The
        ``detect_drift`` exclusion set must keep it out of the drift list.
        """
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        rows = [dict(r) for r in _HAPPY_HANDSHAKE_ROWS]
        rows[0]['pending_tasks_count'] = '5'
        rows[1]['pending_tasks_count'] = '0'
        write_handshakes(plan_dir, plan_id=plan_id, rows=rows)

        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        data = result.toon()
        assert not any(d.get('invariant') == 'pending_tasks_count' for d in data['drift']), data['drift']


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
        result = run_script(SCRIPT_PATH, 'run', '--archived-plan-path', str(archived), '--mode', 'archived')
        assert result.success, result.stderr
        data = result.toon()
        assert data['status'] == 'success'
        assert len(data['phases']) == 2
