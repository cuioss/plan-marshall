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
    def test_worktree_plan_omits_worktree_invariants_in_unphased_default(self, tmp_path, monkeypatch):
        """The top-level ``expected_invariants`` (un-phased default) omits worktree invariants.

        Even when ``metadata.worktree_path`` is set, the top-level
        ``expected_invariants`` TOON field is computed without a phase
        (``expected_invariants(metadata)`` with ``phase is None``). Under the
        ADR-002 gate, Signal 2 only fires at ``phase >= 5-execute``, so the
        un-phased default never carries worktree invariants — they surface in
        the per-phase expectation instead (see
        ``TestWorktreeInvariantGating`` and the integration test below).
        """
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        status_path = plan_dir / 'status.json'
        status = json.loads(status_path.read_text())
        status['metadata']['worktree_path'] = '/tmp/some/worktree'
        status_path.write_text(json.dumps(status))

        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()
        expected = data['expected_invariants']
        assert 'worktree_sha' not in expected, expected
        assert 'worktree_dirty' not in expected, expected
        # Core invariants are always present in the un-phased default.
        assert 'main_sha' in expected

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


class TestWorktreeInvariantGating:
    """Pin the contract for worktree-state invariants in ``expected_invariants``.

    The worktree-state invariants (``worktree_sha`` / ``worktree_dirty``) are
    expected when the plan is routed through a worktree, signalled one of two
    ways:

    - **Signal 1** (unconditional): a non-empty worktree value on the captured
      row proves the worktree was materialized when the phase captured —
      independent of the phase ordinal.
    - **Signal 2** (phase-gated): ``use_worktree`` / ``worktree_path`` in the
      plan's current metadata. Under the ADR-002 deferred-materialization model
      the worktree is not created until phase-5-execute, so Signal 2 is gated
      on ``phase >= 5-execute``. For phases 1-4 (and the un-phased default
      where ``phase is None``) Signal 2 is suppressed: the worktree is not yet
      materialized, so an empty captured worktree value is expected — not a
      missing invariant.
    """

    def test_expected_invariants_includes_worktree_when_metadata_worktree_routed_at_execute(self):
        """Signal 2 at phase >= 5-execute: worktree-routed metadata → worktree invariants."""
        metadata = {'worktree_path': '/some/worktree'}
        phase_values = {'main_sha': 'abc123', 'worktree_sha': None, 'worktree_dirty': ''}

        expected = _summarize.expected_invariants(metadata, '5-execute', phase_values)

        assert 'worktree_sha' in expected
        assert 'worktree_dirty' in expected
        assert 'main_sha' in expected

    def test_expected_invariants_includes_worktree_on_use_worktree_flag_at_execute(self):
        """Signal 2 fires on ``use_worktree`` alone (no worktree_path yet) at phase >= 5-execute."""
        metadata = {'use_worktree': True}
        phase_values = {'main_sha': 'abc123'}

        expected = _summarize.expected_invariants(metadata, '5-execute', phase_values)

        assert 'worktree_sha' in expected
        assert 'worktree_dirty' in expected

    def test_expected_invariants_includes_worktree_when_row_carries_value(self):
        """Signal 1: row carries worktree_sha → include worktree invariants."""
        metadata: dict[str, object] = {}
        phase_values = {'main_sha': 'abc123', 'worktree_sha': 'def456'}

        expected = _summarize.expected_invariants(metadata, '5-execute', phase_values)

        assert 'worktree_sha' in expected
        assert 'worktree_dirty' in expected

    def test_expected_invariants_excludes_worktree_for_main_checkout_plan(self):
        """Neither signal → main-checkout plan, no worktree invariants expected."""
        metadata: dict[str, object] = {}
        phase_values = {'main_sha': 'abc123'}

        expected = _summarize.expected_invariants(metadata, '3-outline', phase_values)

        assert 'worktree_sha' not in expected
        assert 'worktree_dirty' not in expected
        assert 'main_sha' in expected

    def test_signal2_suppressed_for_pre_execute_phases(self):
        """Regression: Signal 2 is gated off for phases 1-4.

        A worktree-routed plan (``worktree_path`` / ``use_worktree`` set) whose
        captured row carries no worktree value must NOT expect worktree
        invariants while the phase is below ``5-execute`` — the worktree is not
        yet materialized under ADR-002, so an empty captured value is expected,
        not a missing invariant. Exercises every pre-5 planning phase to pin
        the gate boundary.
        """
        metadata = {'worktree_path': '/some/worktree', 'use_worktree': True}
        phase_values = {'main_sha': 'abc123', 'worktree_sha': '', 'worktree_dirty': ''}

        for phase in ('1-init', '2-refine', '3-outline', '4-plan'):
            expected = _summarize.expected_invariants(metadata, phase, phase_values)
            assert 'worktree_sha' not in expected, (
                f'Signal 2 must be suppressed for {phase} (< 5-execute), got {expected}'
            )
            assert 'worktree_dirty' not in expected, (
                f'Signal 2 must be suppressed for {phase} (< 5-execute), got {expected}'
            )
            # Core invariants are still expected regardless of the gate.
            assert 'main_sha' in expected

    def test_signal2_suppressed_for_unphased_default(self):
        """Regression: Signal 2 is gated off for the un-phased default.

        The no-handshakes fallback path calls ``expected_invariants`` with
        ``phase is None``. ``_phase_at_or_after_execute(None)`` is ``False``, so
        a worktree-routed plan must not expect worktree invariants in the
        un-phased default set — otherwise the top-level ``expected_invariants``
        TOON field would carry a guaranteed false-positive.
        """
        metadata = {'worktree_path': '/some/worktree', 'use_worktree': True}

        expected = _summarize.expected_invariants(metadata)

        assert 'worktree_sha' not in expected, expected
        assert 'worktree_dirty' not in expected, expected
        assert 'main_sha' in expected

    def test_signal2_emitted_for_phase_at_or_after_execute(self):
        """Regression: Signal 2 fires for every phase >= 5-execute.

        Counterpart to the suppression tests above — a worktree-routed plan
        whose captured row carries no worktree value DOES expect worktree
        invariants once the phase ordinal reaches 5, because the worktree is
        materialized at phase-5-execute and an empty captured value is then a
        real capture gap.
        """
        metadata = {'worktree_path': '/some/worktree', 'use_worktree': True}
        phase_values = {'main_sha': 'abc123', 'worktree_sha': '', 'worktree_dirty': ''}

        for phase in ('5-execute', '6-finalize'):
            expected = _summarize.expected_invariants(metadata, phase, phase_values)
            assert 'worktree_sha' in expected, (
                f'Signal 2 must fire for {phase} (>= 5-execute), got {expected}'
            )
            assert 'worktree_dirty' in expected, (
                f'Signal 2 must fire for {phase} (>= 5-execute), got {expected}'
            )

    def test_run_includes_worktree_invariants_for_worktree_routed_plan(
        self, tmp_path, monkeypatch
    ):
        """Integration contract: a worktree-routed plan expects worktree
        invariants at every captured phase; phases that captured them list
        them in ``invariants_present``.
        """
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)

        # Mark the plan as worktree-routed in status.
        status_path = plan_dir / 'status.json'
        status = json.loads(status_path.read_text())
        status['metadata']['worktree_path'] = '/tmp/some/worktree'
        status['metadata']['use_worktree'] = True
        status_path.write_text(json.dumps(status))

        materialized_phases = ['5-execute', '6-finalize']
        rows = []
        for i, phase in enumerate(materialized_phases):
            rows.append(
                {
                    'phase': phase,
                    'captured_at': f'2026-04-17T2{i}:00:00Z',
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

        # Each materialized phase captured the worktree invariants and lists
        # them in invariants_present.
        materialized_phase_entries = [p for p in data['phases'] if p['phase'] in materialized_phases]
        for entry in materialized_phase_entries:
            present = entry.get('invariants_present', [])
            assert 'worktree_sha' in present, (
                f'{entry["phase"]} must list worktree_sha in invariants_present, got {present}'
            )
