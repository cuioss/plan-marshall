# SPDX-License-Identifier: FSL-1.1-ALv2
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

from _plan_retrospective_fixtures import (  # noqa: E402
    _HAPPY_HANDSHAKE_ROWS,
    setup_archived_plan,
    setup_live_plan,
    write_handshakes,
)

from conftest import MARKETPLACE_ROOT, run_script  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))


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
    - **Signal 2** (phase-gated): the plan is worktree-routed, resolved by
      ``plan_is_worktree_routed`` and passed in as a BOOLEAN. Under the ADR-002
      deferred-materialization model the worktree is not created until
      phase-5-execute, so Signal 2 is gated on ``phase >= 5-execute``. For
      phases 1-4 (and the un-phased default where ``phase is None``) Signal 2 is
      suppressed: the worktree is not yet materialized, so an empty captured
      worktree value is expected — not a missing invariant.

    Signal 2's first parameter is a ``bool``, never a metadata dict. It
    previously took the raw ``status.metadata`` mapping and re-derived the
    worktree face inline by testing ``worktree_path`` / ``use_worktree``; that
    resolution now belongs to ``plan_is_worktree_routed``, which asks
    ``file_ops.resolve_plan_context`` for a live plan. These tests therefore pass
    ``True`` / ``False`` explicitly — a metadata dict would still "work" by
    truthiness while asserting nothing about the real contract.
    """

    def test_expected_invariants_includes_worktree_when_routed_at_execute(self):
        """Signal 2 at phase >= 5-execute: worktree-routed → worktree invariants."""
        phase_values = {'main_sha': 'abc123', 'worktree_sha': None, 'worktree_dirty': ''}

        expected = _summarize.expected_invariants(True, '5-execute', phase_values)

        assert 'worktree_sha' in expected
        assert 'worktree_dirty' in expected
        assert 'main_sha' in expected

    def test_expected_invariants_includes_worktree_with_no_captured_values(self):
        """Signal 2 fires on the routing verdict alone, with no captured values."""
        phase_values = {'main_sha': 'abc123'}

        expected = _summarize.expected_invariants(True, '5-execute', phase_values)

        assert 'worktree_sha' in expected
        assert 'worktree_dirty' in expected

    def test_expected_invariants_includes_worktree_when_row_carries_value(self):
        """Signal 1: row carries worktree_sha → include worktree invariants.

        Signal 1 is independent of the routing verdict, so ``False`` is passed
        deliberately — the row's own value is the proof.
        """
        phase_values = {'main_sha': 'abc123', 'worktree_sha': 'def456'}

        expected = _summarize.expected_invariants(False, '5-execute', phase_values)

        assert 'worktree_sha' in expected
        assert 'worktree_dirty' in expected

    def test_expected_invariants_excludes_worktree_for_main_checkout_plan(self):
        """Neither signal → main-checkout plan, no worktree invariants expected."""
        phase_values = {'main_sha': 'abc123'}

        expected = _summarize.expected_invariants(False, '3-outline', phase_values)

        assert 'worktree_sha' not in expected
        assert 'worktree_dirty' not in expected
        assert 'main_sha' in expected

    def test_signal2_suppressed_for_pre_execute_phases(self):
        """Regression: Signal 2 is gated off for phases 1-4.

        A worktree-routed plan whose captured row carries no worktree value must
        NOT expect worktree invariants while the phase is below ``5-execute`` —
        the worktree is not yet materialized under ADR-002, so an empty captured
        value is expected, not a missing invariant. Exercises every pre-5
        planning phase to pin the gate boundary.
        """
        phase_values = {'main_sha': 'abc123', 'worktree_sha': '', 'worktree_dirty': ''}

        for phase in ('1-init', '2-refine', '3-outline', '4-plan'):
            expected = _summarize.expected_invariants(True, phase, phase_values)
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
        expected = _summarize.expected_invariants(True)

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
        phase_values = {'main_sha': 'abc123', 'worktree_sha': '', 'worktree_dirty': ''}

        for phase in ('5-execute', '6-finalize'):
            expected = _summarize.expected_invariants(True, phase, phase_values)
            assert 'worktree_sha' in expected, (
                f'Signal 2 must fire for {phase} (>= 5-execute), got {expected}'
            )
            assert 'worktree_dirty' in expected, (
                f'Signal 2 must fire for {phase} (>= 5-execute), got {expected}'
            )

    def test_metadata_dict_is_not_an_accepted_routing_verdict(self):
        """Guard: the first parameter is a bool, not a metadata mapping.

        Before the migration this parameter was the raw ``status.metadata`` dict
        and the function re-derived routing from its keys. Passing a mapping now
        must NOT be interpretable as a routing verdict by key content — a
        main-checkout metadata dict is non-empty and would read as truthy, which
        is exactly how a stale caller would silently invert the gate. Asserting
        both dicts behave identically pins that no key is consulted.
        """
        phase_values = {'main_sha': 'abc123', 'worktree_sha': '', 'worktree_dirty': ''}

        routed_shape = _summarize.expected_invariants(
            {'worktree_path': '/wt', 'use_worktree': True}, '5-execute', phase_values
        )
        main_checkout_shape = _summarize.expected_invariants(
            {'title': 'no worktree keys at all'}, '5-execute', phase_values
        )

        assert routed_shape == main_checkout_shape, (
            'expected_invariants must not read keys off its first parameter — '
            'the routing verdict is resolved by plan_is_worktree_routed'
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
