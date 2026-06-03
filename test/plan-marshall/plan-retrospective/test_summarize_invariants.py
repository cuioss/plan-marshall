"""Tests for ``summarize-invariants.py``.

The script reads phase-handshake captures from ``<plan_dir>/handshakes.toon``
(canonical storage owned by ``plan-marshall:plan-marshall:phase_handshake``)
rather than ``status.metadata.phase_handshake``. Fixtures in
``_plan_retrospective_fixtures.py`` materialize the file in the same TOON
shape ``_handshake_store.save_rows``
emits in production.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _plan_retrospective_fixtures import (  # noqa: E402
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


def _load_summarize_module():
    """Import ``summarize-invariants.py`` as a module for function-level tests."""
    spec = importlib.util.spec_from_file_location('summarize_invariants_module', SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_summarize = _load_summarize_module()


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

    def test_unfinished_tasks_count_excluded_from_drift(self, tmp_path, monkeypatch):
        """``unfinished_tasks_count`` naturally drains across phases — not drift.

        The capture column is meaningful for the phase-5-execute transition
        guard and as a retrospective signal of orphaned fix tasks, but a
        change between phases is expected (the queue should drain). The
        ``detect_drift`` exclusion set must keep it out of the drift list.
        """
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        rows = [dict(r) for r in _HAPPY_HANDSHAKE_ROWS]
        rows[0]['unfinished_tasks_count'] = '5'
        rows[1]['unfinished_tasks_count'] = '0'
        write_handshakes(plan_dir, plan_id=plan_id, rows=rows)

        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        data = result.toon()
        assert not any(d.get('invariant') == 'unfinished_tasks_count' for d in data['drift']), data['drift']


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


class TestConditionalPhaseStepsExpectation:
    """Tests for the conditional phase_steps_complete expected-invariant rule.

    ``phase_steps_complete`` is expected only when the phase has a
    ``standards/required-steps.md`` file (currently only ``6-finalize``).
    Phases without that file must not be penalised for a missing
    ``phase_steps_complete`` column.
    """

    def test_phase_without_required_steps_not_penalised(self, tmp_path, monkeypatch):
        """Phase 1-init has no required-steps.md; phase_steps_complete must not appear in invariants_missing."""
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        # Strip phase_steps_complete from the 1-init row to simulate a plan
        # captured before the invariant existed.
        rows = [dict(r) for r in _HAPPY_HANDSHAKE_ROWS]
        rows[0].pop('phase_steps_complete', None)
        rows[0]['phase_steps_complete'] = ''
        write_handshakes(plan_dir, plan_id=plan_id, rows=rows)

        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()
        init_phase = next((p for p in data['phases'] if p['phase'] == '1-init'), None)
        assert init_phase is not None, 'expected 1-init phase in output'
        assert 'phase_steps_complete' not in init_phase['invariants_missing'], (
            'phase_steps_complete must not be flagged as missing for 1-init '
            '(no required-steps.md for that phase)'
        )

    def test_phase_with_required_steps_flagged_when_missing(self, tmp_path, monkeypatch):
        """Phase 6-finalize has required-steps.md; absent phase_steps_complete is a real gap."""
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        rows = [dict(r) for r in _HAPPY_HANDSHAKE_ROWS]
        # Clear the phase_steps_complete column for the 6-finalize row.
        rows[1]['phase_steps_complete'] = ''
        write_handshakes(plan_dir, plan_id=plan_id, rows=rows)

        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()
        finalize_phase = next((p for p in data['phases'] if p['phase'] == '6-finalize'), None)
        assert finalize_phase is not None, 'expected 6-finalize phase in output'
        assert 'phase_steps_complete' in finalize_phase['invariants_missing'], (
            'phase_steps_complete must be flagged as missing for 6-finalize '
            '(required-steps.md is present for that phase)'
        )

    def test_phase_with_required_steps_present_not_flagged(self, tmp_path, monkeypatch):
        """Phase 6-finalize with phase_steps_complete captured must list it in invariants_present."""
        plan_id, _ = setup_live_plan(tmp_path, monkeypatch)
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()
        finalize_phase = next((p for p in data['phases'] if p['phase'] == '6-finalize'), None)
        assert finalize_phase is not None, 'expected 6-finalize phase in output'
        assert 'phase_steps_complete' in finalize_phase['invariants_present'], (
            'phase_steps_complete must appear in invariants_present for 6-finalize '
            'when the value was captured'
        )
        assert 'phase_steps_complete' not in finalize_phase['invariants_missing'], (
            'phase_steps_complete must not be in invariants_missing for 6-finalize '
            'when the value was captured'
        )

    def test_default_expected_invariants_omits_phase_steps_complete(self, tmp_path, monkeypatch):
        """The un-phased default (no-handshakes path) must not include phase_steps_complete.

        ``expected_invariants`` is also reported in the top-level
        ``expected_invariants`` TOON field; without a phase it must reflect
        only the core invariants.
        """
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        # Remove the handshakes file so cmd_run uses the no-handshakes path.
        (plan_dir / 'handshakes.toon').unlink()

        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()
        assert 'phase_steps_complete' not in data['expected_invariants'], (
            'phase_steps_complete must not appear in top-level expected_invariants '
            'when no phase is in context'
        )


class TestDeferredMaterializationWindow:
    """Tests for the deferred-materialization fix in ``expected_invariants``.

    Phase-5-execute is the worktree materialization phase for worktree-bearing
    plans; phases 1-init through 4-plan declare the worktree intent but the
    directory itself is not created until phase-5-execute Step 2.5. Before the
    fix, ``expected_invariants`` consulted only the plan's current metadata
    and required ``worktree_sha`` / ``worktree_dirty`` for every phase,
    producing 8 spurious ERROR findings (2 per pre-5-execute phase) for every
    worktree-bearing plan. The fix makes the predicate row-aware: include
    worktree invariants only when the captured row carries them OR when the
    phase is at/after materialization.
    """

    def test_expected_invariants_excludes_worktree_for_deferred_materialization_window(self):
        """Function-level contract: pre-5-execute phase + empty row values → no worktree invariants."""
        metadata = {'worktree_path': '/some/worktree'}
        # The phase ran during the deferred-materialization window — its
        # captured row carries no worktree values yet.
        phase_values = {'main_sha': 'abc123', 'worktree_sha': None, 'worktree_dirty': ''}

        expected = _summarize.expected_invariants(metadata, '3-outline', phase_values)

        assert 'worktree_sha' not in expected, (
            f'worktree_sha must be excluded for deferred phase, got {expected}'
        )
        assert 'worktree_dirty' not in expected, (
            f'worktree_dirty must be excluded for deferred phase, got {expected}'
        )
        # Core invariants must still be present.
        assert 'main_sha' in expected

    def test_expected_invariants_includes_worktree_when_row_carries_value(self):
        """Function-level contract: row carries worktree_sha → include worktree invariants regardless of phase."""
        metadata = {'worktree_path': '/some/worktree'}
        phase_values = {'main_sha': 'abc123', 'worktree_sha': 'def456'}

        expected = _summarize.expected_invariants(metadata, '5-execute', phase_values)

        assert 'worktree_sha' in expected
        assert 'worktree_dirty' in expected

    def test_expected_invariants_includes_worktree_for_post_materialization_phase(self):
        """Function-level contract: 5-execute / 6-finalize phase + worktree metadata → expect worktree invariants."""
        metadata = {'worktree_path': '/some/worktree'}
        # Even when the row's worktree values are empty (a real capture gap),
        # phases at/after materialization MUST expect them.
        phase_values = {'main_sha': 'abc123', 'worktree_sha': None}

        for materialized_phase in ('5-execute', '6-finalize'):
            expected = _summarize.expected_invariants(metadata, materialized_phase, phase_values)
            assert 'worktree_sha' in expected, (
                f'{materialized_phase} must still expect worktree_sha as a real gap signal'
            )

    def test_run_emits_no_worktree_findings_in_pre_5_execute_phases_when_unmaterialized(
        self, tmp_path, monkeypatch
    ):
        """Integration contract: a worktree-bearing plan's pre-5-execute phases produce zero worktree ERROR findings.

        Reproduces the empirical 8-spurious-findings case from the originating
        lesson: a worktree-bearing plan captured 1-init through 4-plan during
        the deferred-materialization window (empty worktree_sha / worktree_dirty)
        and 5-execute / 6-finalize after materialization.
        """
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)

        # Mark the plan as worktree-bearing in status.
        status_path = plan_dir / 'status.json'
        status = json.loads(status_path.read_text())
        status['metadata']['worktree_path'] = '/tmp/some/worktree'
        status_path.write_text(json.dumps(status))

        # Synthesize a six-phase handshake history with the deferred shape:
        # phases 1-init..4-plan have empty worktree_* values (pre-materialization),
        # phases 5-execute and 6-finalize have populated values.
        deferred_phases = ['1-init', '2-refine', '3-outline', '4-plan']
        materialized_phases = ['5-execute', '6-finalize']
        rows = []
        for i, phase in enumerate(deferred_phases):
            rows.append(
                {
                    'phase': phase,
                    'captured_at': f'2026-04-17T1{i}:00:00Z',
                    'worktree_applicable': False,
                    'override': False,
                    'override_reason': '',
                    'main_sha': 'abc123',
                    'main_dirty': '0',
                    'worktree_sha': '',
                    'worktree_dirty': '',
                    'task_state_hash': 'hash1',
                    'qgate_open_count': '0',
                    'config_hash': 'cfg1',
                    'unfinished_tasks_count': '0',
                    'phase_steps_complete': '',
                }
            )
        for i, phase in enumerate(materialized_phases):
            rows.append(
                {
                    'phase': phase,
                    'captured_at': f'2026-04-17T2{i}:00:00Z',
                    'worktree_applicable': True,
                    'override': False,
                    'override_reason': '',
                    'main_sha': 'abc123',
                    'main_dirty': '0',
                    'worktree_sha': 'wsha-' + str(i),
                    'worktree_dirty': '0',
                    'task_state_hash': 'hash1',
                    'qgate_open_count': '0',
                    'config_hash': 'cfg1',
                    'unfinished_tasks_count': '0',
                    'phase_steps_complete': 'sha-' + phase,
                }
            )
        write_handshakes(plan_dir, plan_id=plan_id, rows=rows)

        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()

        findings = data.get('findings', [])
        worktree_findings_in_deferred_phases = [
            f
            for f in findings
            if f.get('severity') == 'error'
            and f.get('invariant') in ('worktree_sha', 'worktree_dirty')
            and f.get('phase') in deferred_phases
        ]
        assert worktree_findings_in_deferred_phases == [], (
            f'Expected zero worktree ERROR findings for pre-5-execute phases in deferred window, '
            f'got {worktree_findings_in_deferred_phases}'
        )

        # Sanity check: the materialized phases must still include the worktree
        # invariants in their expected set (so any real capture gap would be flagged).
        materialized_phase_entries = [p for p in data['phases'] if p['phase'] in materialized_phases]
        for entry in materialized_phase_entries:
            present = entry.get('invariants_present', [])
            assert 'worktree_sha' in present, (
                f'{entry["phase"]} must list worktree_sha in invariants_present, got {present}'
            )
