#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-metrics.py CLI script."""


import pytest
from _manage_metrics_fixtures import (
    ns_accumulate,
    ns_generate,
)
from _manage_metrics_module_fixtures import (
    _UNSEEDED_PLAN_IDS,
    _recorded_phase_row,
    _write_dispatch_boundaries,
    cmd_accumulate_agent_usage,
    cmd_generate,
    manage_metrics,
)


@pytest.fixture(autouse=True)
def _seed_guarded_plan_dirs(plan_context, monkeypatch):
    """Auto-seed ``status.json`` at the require_plan_exists chokepoint.

    The patched guard resolves the plan dir via the real ``get_plan_dir`` and, for
    any plan_id NOT registered as unseeded, writes the ``status.json`` sentinel
    before delegating to the genuine ``require_plan_exists``. This keeps every
    positive test's happy path intact without per-test seeding, while the
    negative tests (which call ``_register_unseeded``) still exercise the real
    ``plan_not_found`` failure.
    """
    _UNSEEDED_PLAN_IDS.clear()
    real_require = manage_metrics.require_plan_exists
    real_get_plan_dir = manage_metrics.get_plan_dir

    def _seeding_require(plan_id):
        if plan_id not in _UNSEEDED_PLAN_IDS:
            plan_dir = real_get_plan_dir(plan_id)
            plan_dir.mkdir(parents=True, exist_ok=True)
            sentinel = plan_dir / 'status.json'
            if not sentinel.is_file():
                sentinel.write_text('{}', encoding='utf-8')
        return real_require(plan_id)

    monkeypatch.setattr(manage_metrics, 'require_plan_exists', _seeding_require)
    return plan_context


class TestGenerateReconcilesDispatchBoundaries:
    """cmd_generate reconciles a dispatched phase's under-counted total against the
    dispatch-boundaries sum via same-population max — the #565 divergence.
    """

    def test_reconciles_undercounted_phase_to_boundary_sum(self, plan_context):
        """A 5-execute row reporting ~89k against a ~2.0M boundary sum renders the boundary
        sum, persists it as a DISTINCT field, keeps total_tokens byte-identical, and annotates.
        """
        manage_metrics.write_metrics(
            'db-recon-under',
            {
                'phases': {
                    '5-execute': {
                        'start_time': '2026-05-08T13:00:00+00:00',
                        'end_time': '2026-05-08T14:00:00+00:00',
                        'total_tokens': 89000,
                    },
                },
            },
        )
        _write_dispatch_boundaries(plan_context, 'db-recon-under', '5-execute', [1_000_000, 1_000_000])

        result = cmd_generate(ns_generate('db-recon-under'))
        assert result['status'] == 'success'
        # The reconciled (larger) boundary sum feeds the Total.
        assert result['total_tokens'] == 2_000_000

        toon = (plan_context.plan_dir_for('db-recon-under') / 'work' / 'metrics.toon').read_text()
        # Explicit-wins: the recorded total_tokens stays byte-identical.
        assert 'total_tokens: 89000' in toon
        # The boundary sum is persisted as a DISTINCT field, never overwriting total_tokens.
        assert 'dispatch_boundary_total: 2000000' in toon

        # The row count persists alongside the sum so the measure's coverage is
        # readable without re-parsing the boundary file.
        assert 'dispatch_boundary_rows_recorded: 2' in toon

        md = (plan_context.plan_dir_for('db-recon-under') / 'metrics.md').read_text()
        assert '2,000,000' in md
        # The annotation names WHICH measure won and what it beat, rather than
        # asserting an unqualified "same-population max".
        assert 'Tokens reconciled across the competing measures' in md
        assert 'dispatch_boundary_total 2,000,000 (> total_tokens 89,000)' in md
        # The recorded raw total is still visible in the Phase Details section.
        assert '89,000' in md

    def test_absent_boundary_file_is_clean_noop(self, plan_context):
        """With no boundary file, the recorded total renders unchanged and no distinct
        field or annotation appears.
        """
        manage_metrics.write_metrics(
            'db-recon-noop',
            {
                'phases': {
                    '5-execute': {
                        'start_time': '2026-05-08T13:00:00+00:00',
                        'end_time': '2026-05-08T14:00:00+00:00',
                        'total_tokens': 50000,
                    },
                },
            },
        )

        result = cmd_generate(ns_generate('db-recon-noop'))
        assert result['status'] == 'success'
        assert result['total_tokens'] == 50000

        toon = (plan_context.plan_dir_for('db-recon-noop') / 'work' / 'metrics.toon').read_text()
        assert 'total_tokens: 50000' in toon
        assert 'dispatch_boundary_total' not in toon

        md = (plan_context.plan_dir_for('db-recon-noop') / 'metrics.md').read_text()
        assert 'reconciled from dispatch boundaries' not in md

    def test_smaller_boundary_sum_prefers_recorded_total(self, plan_context):
        """When the boundary sum is smaller than the recorded total, the render prefers the
        recorded value and emits no annotation — but the distinct field is still persisted.
        """
        manage_metrics.write_metrics(
            'db-recon-smaller',
            {
                'phases': {
                    '5-execute': {
                        'start_time': '2026-05-08T13:00:00+00:00',
                        'end_time': '2026-05-08T14:00:00+00:00',
                        'total_tokens': 89000,
                    },
                },
            },
        )
        _write_dispatch_boundaries(plan_context, 'db-recon-smaller', '5-execute', [10000])

        result = cmd_generate(ns_generate('db-recon-smaller'))
        assert result['status'] == 'success'
        # max(89000, 10000) = 89000 feeds the Total; no reconciliation occurs.
        assert result['total_tokens'] == 89000

        toon = (plan_context.plan_dir_for('db-recon-smaller') / 'work' / 'metrics.toon').read_text()
        assert 'total_tokens: 89000' in toon
        # The distinct field is still recorded even when it is the smaller of the pair.
        assert 'dispatch_boundary_total: 10000' in toon

        md = (plan_context.plan_dir_for('db-recon-smaller') / 'metrics.md').read_text()
        assert 'reconciled from dispatch boundaries' not in md


# =============================================================================
# Test: cmd_generate reconciles each phase against its accumulator
# =============================================================================


class TestGenerateReconcilesAccumulator:
    """cmd_generate folds each phase's durable accumulator into its row before rendering.

    Anchored to the terminal-phase gap: a 6-finalize row that accrued subagent
    tokens (via accumulate-agent-usage) but was never closed by end-phase /
    phase-boundary would otherwise drop those tokens from the report. generate
    reconciles the row against the on-disk accumulator so the snapshot survives,
    while leaving explicitly-closed rows untouched (explicit-wins precedence).
    """

    def test_generate_folds_accumulator_into_unclosed_phase_row(self, plan_context):
        """An unclosed 6-finalize row surfaces its accumulator totals after generate."""
        # Producer: seed the durable accumulator (subagent returns during finalize).
        cmd_accumulate_agent_usage(
            ns_accumulate(
                'recon-gen-unclosed', '6-finalize', total_tokens=12345, tool_uses=7, duration_ms=60000
            )
        )
        # The phase row exists (wall span recorded) but was never token-closed.
        manage_metrics.write_metrics(
            'recon-gen-unclosed',
            {'phases': {'6-finalize': {'duration_seconds': 600}}},
        )

        result = cmd_generate(ns_generate('recon-gen-unclosed'))
        assert result['status'] == 'success'

        six = manage_metrics.read_metrics_raw('recon-gen-unclosed')['phases']['6-finalize']
        assert six['total_tokens'] == 12345
        assert six['tool_uses'] == 7
        # 60000 ms < 600 s wall → clamp no-op; folded as agent_duration_ms.
        assert six['agent_duration_ms'] == 60000
        toon = (plan_context.plan_dir_for('recon-gen-unclosed') / 'work' / 'metrics.toon').read_text()
        assert 'agent_duration_ms: 60000' in toon

    def test_generate_preserves_explicit_row_over_divergent_accumulator(self, plan_context):
        """A token-closed row wins over a divergent accumulator (explicit-wins)."""
        cmd_accumulate_agent_usage(
            ns_accumulate(
                'recon-gen-explicit', '6-finalize', total_tokens=999, tool_uses=9, duration_ms=99999
            )
        )
        manage_metrics.write_metrics(
            'recon-gen-explicit',
            {
                'phases': {
                    '6-finalize': {
                        'duration_seconds': 600,
                        'total_tokens': 50000,
                        'tool_uses': 30,
                        'agent_duration_ms': 300000,
                    },
                },
            },
        )

        result = cmd_generate(ns_generate('recon-gen-explicit'))
        assert result['status'] == 'success'

        six = manage_metrics.read_metrics_raw('recon-gen-explicit')['phases']['6-finalize']
        assert six['total_tokens'] == 50000
        assert six['tool_uses'] == 30
        assert six['agent_duration_ms'] == 300000

    def test_generate_partial_row_folds_only_absent_fields(self, plan_context):
        """A row with an explicit total_tokens folds only the missing fields from the accumulator."""
        cmd_accumulate_agent_usage(
            ns_accumulate(
                'recon-gen-partial', '6-finalize', total_tokens=999, tool_uses=7, duration_ms=60000
            )
        )
        manage_metrics.write_metrics(
            'recon-gen-partial',
            {'phases': {'6-finalize': {'duration_seconds': 600, 'total_tokens': 50000}}},
        )

        result = cmd_generate(ns_generate('recon-gen-partial'))
        assert result['status'] == 'success'

        six = manage_metrics.read_metrics_raw('recon-gen-partial')['phases']['6-finalize']
        assert six['total_tokens'] == 50000  # explicit wins
        assert six['tool_uses'] == 7  # folded from accumulator
        assert six['agent_duration_ms'] == 60000  # folded from accumulator


class TestReconcileFloorKeepsPartiality:
    """The reconcile `plan-marshall:plan-retrospective` performs before reading
    `metrics.md` (its Step 2.5) folds the OPEN 6-finalize accumulator FLOOR into the
    phase row while leaving the phase marked partial.

    This pins the D3 guarantee of plan 050: a run where the largest finalize phase
    did work must read NON-ZERO for that phase, and the partiality machinery must
    still flag the genuinely-absent boundary. The retrospective (order 995) reads
    per-phase tokens from `metrics.md` before `default:record-metrics` (order 998)
    performs the authoritative close, so an unreconciled `metrics.md` renders
    6-finalize as zero. Calling `generate` before the read folds the durable
    accumulator into the row (a non-zero floor) WITHOUT stamping an `end_time`, so
    record-metrics' later close stays authoritative (its accumulator read is
    assign-cumulative, so it overwrites the floor with the complete total) and a
    genuinely-open phase is still reported as partial.
    """

    def test_reconcile_folds_finalize_floor_but_keeps_it_marked_partial(self, plan_context):
        # A real non-zero phase, NOT a fixture that closes trivially: phases 1-5 are
        # closed; 6-finalize accrued subagent tokens into its durable accumulator but
        # was never token-closed (record-metrics has not run yet).
        phases = {name: _recorded_phase_row() for name in manage_metrics.PHASE_NAMES[:5]}
        phases['6-finalize'] = {'duration_seconds': 600}
        manage_metrics.write_metrics('d3-reconcile-floor', {'phases': phases})
        cmd_accumulate_agent_usage(
            ns_accumulate(
                'd3-reconcile-floor', '6-finalize', total_tokens=54321, tool_uses=11, duration_ms=120000
            )
        )

        # The reconcile the retrospective performs before aspect 4 reads metrics.md.
        result = cmd_generate(ns_generate('d3-reconcile-floor'))
        assert result['status'] == 'success'

        # (1) The largest finalize phase now reads its FLOOR, not zero.
        six = manage_metrics.read_metrics_raw('d3-reconcile-floor')['phases']['6-finalize']
        assert six['total_tokens'] == 54321, (
            'The reconcile must fold the 6-finalize accumulator floor into the row so '
            'the retrospective reads a phase that did work as non-zero, not zero.'
        )

        # (2) The partiality machinery is untouched: no end_time was stamped, so the
        # genuinely-open phase is STILL flagged — record-metrics (998) still owes the
        # authoritative close, and a future genuine omission still surfaces here.
        assert result['any_phase_missing_end_time'] is True
        assert '6-finalize' in result['phases_missing_end_time'], (
            'Folding the floor must not close the phase: leaving 6-finalize in '
            'phases_missing_end_time is what keeps the partiality signal honest.'
        )
