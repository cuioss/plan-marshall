#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-metrics.py CLI script."""


from _manage_metrics_fixtures import (
    ns_accumulate,
    ns_generate,
)
from _manage_metrics_module_fixtures import (  # noqa: F401 — a fixture is used by NAME, not by reference
    _UNSEEDED_PLAN_IDS,
    _recorded_phase_row,
    _seed_guarded_plan_dirs,
    _write_dispatch_boundaries,
    cmd_accumulate_agent_usage,
    cmd_generate,
    manage_metrics,
)

# =============================================================================
# Test: _reconcile_accumulator_into_phase (Tier 2 - direct call)
# =============================================================================


class TestReconcileAccumulatorIntoPhase:
    """Direct, deterministic coverage of _reconcile_accumulator_into_phase.

    The helper folds a phase's durable on-disk accumulator totals into its
    metrics row in place, with explicit-wins precedence: a field already present
    on the row (recorded by end-phase / phase-boundary) is NEVER overwritten, and
    only a truthy accumulator value backfills an absent field. These unit tests
    pass phase_data and accumulator dicts explicitly so every branch is exercised
    without touching the filesystem; TestGenerateReconcilesAccumulator covers the
    cmd_generate integration path.
    """

    def test_backfills_all_three_fields_into_unclosed_row(self):
        """An unclosed row (wall span only) is backfilled from the accumulator."""
        # duration_seconds=600 keeps the folded-duration clamp a deterministic no-op.
        phase_data = {'duration_seconds': 600}
        manage_metrics._reconcile_accumulator_into_phase(
            phase_data, {'total_tokens': 12345, 'tool_uses': 7, 'duration_ms': 60000}
        )
        assert phase_data['total_tokens'] == 12345
        assert phase_data['tool_uses'] == 7
        assert phase_data['agent_duration_ms'] == 60000
        assert phase_data['agent_duration_seconds'] == 60.0

    def test_explicit_total_tokens_is_not_overwritten(self):
        """A row that already carries total_tokens keeps its own value (explicit-wins)."""
        phase_data = {'total_tokens': 50000}
        manage_metrics._reconcile_accumulator_into_phase(phase_data, {'total_tokens': 999})
        assert phase_data['total_tokens'] == 50000

    def test_explicit_tool_uses_is_not_overwritten(self):
        """A row that already carries tool_uses keeps its own value (explicit-wins)."""
        phase_data = {'tool_uses': 30}
        manage_metrics._reconcile_accumulator_into_phase(phase_data, {'tool_uses': 9})
        assert phase_data['tool_uses'] == 30

    def test_explicit_agent_duration_ms_is_not_overwritten(self):
        """A row with agent_duration_ms is untouched — agent_duration_seconds is not added."""
        phase_data = {'duration_seconds': 600, 'agent_duration_ms': 300000}
        manage_metrics._reconcile_accumulator_into_phase(phase_data, {'duration_ms': 99999})
        assert phase_data['agent_duration_ms'] == 300000
        assert 'agent_duration_seconds' not in phase_data

    def test_empty_accumulator_is_a_noop(self):
        """An absent/empty accumulator leaves the row unchanged."""
        phase_data = {'duration_seconds': 600}
        manage_metrics._reconcile_accumulator_into_phase(phase_data, {})
        assert phase_data == {'duration_seconds': 600}

    def test_zero_accumulator_values_are_not_backfilled(self):
        """Falsy accumulator values (zero) never backfill — indistinguishable from absent."""
        phase_data = {'duration_seconds': 600}
        manage_metrics._reconcile_accumulator_into_phase(
            phase_data, {'total_tokens': 0, 'tool_uses': 0, 'duration_ms': 0}
        )
        assert 'total_tokens' not in phase_data
        assert 'tool_uses' not in phase_data
        assert 'agent_duration_ms' not in phase_data

    def test_partial_backfill_only_absent_fields(self):
        """Only the absent fields are folded; present fields win."""
        phase_data = {'duration_seconds': 600, 'total_tokens': 50000}
        manage_metrics._reconcile_accumulator_into_phase(
            phase_data, {'total_tokens': 999, 'tool_uses': 7}
        )
        assert phase_data['total_tokens'] == 50000  # explicit wins
        assert phase_data['tool_uses'] == 7  # absent → folded

    def test_duration_clamped_to_wall_span_during_fold(self):
        """A folded duration_ms is clamped to the row's wall span."""
        phase_data = {'duration_seconds': 1.0}
        manage_metrics._reconcile_accumulator_into_phase(phase_data, {'duration_ms': 4000})
        assert phase_data['agent_duration_ms'] == 1000
        assert phase_data['agent_duration_seconds'] == 1.0

    def test_duration_unclamped_when_wall_span_absent(self):
        """Without a recorded wall span the folded duration flows through unclamped."""
        phase_data: dict = {}
        manage_metrics._reconcile_accumulator_into_phase(phase_data, {'duration_ms': 4000})
        assert phase_data['agent_duration_ms'] == 4000
        assert phase_data['agent_duration_seconds'] == 4.0


# =============================================================================
# Test: cmd_generate reconciles each phase against its accumulator
# =============================================================================

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


# =============================================================================
# Test: dispatch-boundary reconciliation (D1) — _read_dispatch_boundary_totals
# and the cmd_generate same-population max reconciliation
# =============================================================================

class TestReadDispatchBoundaryTotals:
    """Direct coverage of the _read_dispatch_boundary_totals reader.

    The reader returns ``(sum, rows_counted)``: the sum alone cannot state its own
    coverage, and the row count is what lets the reconciliation mark the measure
    partial and refuse it the maximum.
    """

    def test_sums_total_tokens_column_across_rows(self, plan_context):
        """The reader sums the total_tokens column (position 2) across all data rows."""
        _write_dispatch_boundaries(plan_context, 'db-read-sum', '5-execute', [1_000_000, 1_000_000])
        assert manage_metrics._read_dispatch_boundary_totals('db-read-sum', '5-execute') == (
            2_000_000,
            2,
        )

    def test_absent_file_returns_zero(self, plan_context):
        """A missing boundary file reads as (0, 0) — the caller's clean no-op signal."""
        assert manage_metrics._read_dispatch_boundary_totals('db-read-absent', '5-execute') == (0, 0)

    def test_header_and_malformed_rows_are_skipped(self, plan_context):
        """Header lines and a short/malformed data row are skipped, not summed or fatal."""
        path = manage_metrics._dispatch_boundary_path('db-read-malformed', '5-execute')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            'plan_id: db-read-malformed\n'
            'phase: 5-execute\n'
            'rows[]{timestamp,termination_cause,total_tokens}:\n'
            '2026-05-08T14:00:11Z,budget_yield,500\n'
            'too,short\n'
            '2026-05-08T14:01:11Z,budget_yield,not_an_int,x,y\n'
            '2026-05-08T14:02:11Z,budget_yield,700\n',
            encoding='utf-8',
        )
        # Only the two well-formed integer rows (500 + 700) contribute — and the
        # row count reports 2, not the 4 lines the file holds, so a malformed row
        # cannot inflate the measure's apparent coverage.
        assert manage_metrics._read_dispatch_boundary_totals('db-read-malformed', '5-execute') == (
            1200,
            2,
        )


# =============================================================================
# Test: first-class partiality fields (Tier 2 - direct import)
# =============================================================================

class TestReadCostDecomposition:
    """Plan 030 D3: the read cost is published as its two factors — the
    resident-context factor as a PERSISTED field, and the turns factor as the
    existing tool_uses — so a consumer sees the two levers instead of one opaque
    number. The factor is persisted (not a render-time computation) and their
    product reconstructs cache_read_input_tokens.
    """

    def test_resident_context_factor_is_persisted_not_render_only(self, plan_context):
        """generate writes cache_read_per_tool_use = round(cache_read / tool_uses)
        into metrics.toon, so it is readable off the row without re-deriving it."""
        manage_metrics.write_metrics(
            'd3-persist',
            {
                'phases': {
                    '5-execute': {
                        'duration_seconds': 600,
                        'agent_duration_ms': 300000,
                        'tool_uses': 8,
                        'cache_read_input_tokens': 80000,
                    },
                },
            },
        )

        result = cmd_generate(ns_generate('d3-persist'))
        assert result['status'] == 'success'

        five = manage_metrics.read_metrics_raw('d3-persist')['phases']['5-execute']
        # Persisted, and equal to the decomposition factor.
        assert five['cache_read_per_tool_use'] == round(80000 / 8)
        # The product of the two factors reconstructs the read cost exactly here.
        assert five['cache_read_per_tool_use'] * five['tool_uses'] == 80000

    def test_factor_absent_when_tool_uses_is_zero_or_missing(self, plan_context):
        """A guessed factor over a zero/absent turn count is never written."""
        manage_metrics.write_metrics(
            'd3-absent',
            {
                'phases': {
                    # tool_uses absent
                    '3-outline': {
                        'duration_seconds': 100,
                        'cache_read_input_tokens': 5000,
                    },
                    # tool_uses present but zero
                    '5-execute': {
                        'duration_seconds': 200,
                        'tool_uses': 0,
                        'cache_read_input_tokens': 5000,
                    },
                },
            },
        )

        cmd_generate(ns_generate('d3-absent'))
        phases = manage_metrics.read_metrics_raw('d3-absent')['phases']
        assert 'cache_read_per_tool_use' not in phases['3-outline']
        assert 'cache_read_per_tool_use' not in phases['5-execute']

    def test_render_states_the_decomposition_and_discloses_the_population_span(
        self, plan_context
    ):
        """The rendered bullet states the identity and, per D4, names that the ratio
        spans two populations rather than reading as a single-population measure."""
        manage_metrics.write_metrics(
            'd3-render',
            {
                'phases': {
                    '5-execute': {
                        'duration_seconds': 600,
                        'agent_duration_ms': 300000,
                        'tool_uses': 8,
                        'cache_read_input_tokens': 80000,
                    },
                },
            },
        )

        cmd_generate(ns_generate('d3-render'))
        md = (plan_context.plan_dir_for('d3-render') / 'metrics.md').read_text()
        assert '- **Read-cost decomposition**:' in md
        assert 'resident context per tool-use (10,000)' in md
        assert 'turns (8)' in md
        # D4: the figure names its population span, not a single population.
        assert 'derived-cost ratio' in md
        assert 'the two populations differ' in md

    def test_stale_factor_is_cleared_when_operands_stop_qualifying(self, plan_context):
        """A cache_read_per_tool_use left by an earlier generate is REMOVED (not
        left to render an invalid identity or crash the render) when a later
        generate sees a missing or non-positive tool_uses. Presence is an invariant:
        present iff derivable from this regenerate's operands."""
        # Row seeded WITH a stale factor but a tool_uses that no longer qualifies:
        # one row has tool_uses missing entirely, one has tool_uses == 0.
        manage_metrics.write_metrics(
            'd3-stale',
            {
                'phases': {
                    '3-outline': {
                        'duration_seconds': 100,
                        'cache_read_input_tokens': 5000,
                        'cache_read_per_tool_use': 999,  # stale
                    },
                    '5-execute': {
                        'duration_seconds': 200,
                        'tool_uses': 0,
                        'cache_read_input_tokens': 5000,
                        'cache_read_per_tool_use': 999,  # stale
                    },
                },
            },
        )

        # Must not raise (the old unconditional tool_uses read would KeyError here).
        result = cmd_generate(ns_generate('d3-stale'))
        assert result['status'] == 'success'

        phases = manage_metrics.read_metrics_raw('d3-stale')['phases']
        assert 'cache_read_per_tool_use' not in phases['3-outline']
        assert 'cache_read_per_tool_use' not in phases['5-execute']
        # And the render carries no decomposition bullet for either.
        md = (plan_context.plan_dir_for('d3-stale') / 'metrics.md').read_text()
        assert '- **Read-cost decomposition**:' not in md
