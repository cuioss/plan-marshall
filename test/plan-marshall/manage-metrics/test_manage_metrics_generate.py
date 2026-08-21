#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-metrics.py CLI script.

Its sections, in order:

* cmd_generate reconciles each phase against its accumulator
* enrich delegates to the platform-runtime normalized-tokens op
"""


from _manage_metrics_fixtures import (
    ns_accumulate,
    ns_end_phase,
    ns_generate,
    ns_start_phase,
)
from _manage_metrics_module_fixtures import (  # noqa: F401 — a fixture is used by NAME, not by reference
    _UNSEEDED_PLAN_IDS,
    _seed_guarded_plan_dirs,
    _write_dispatch_boundaries,
    cmd_accumulate_agent_usage,
    cmd_end_phase,
    cmd_generate,
    cmd_start_phase,
    manage_metrics,
)


def test_generate_total_row_sums_three_columns_independently(plan_context):
    """The Total row sums Worked, Reported (wall), and Idle independently."""
    manage_metrics.write_metrics(
        'metrics-gen-total',
        {
            'phases': {
                '1-init': {'duration_seconds': 200, 'agent_duration_ms': 120000},
                '2-refine': {'duration_seconds': 100, 'agent_duration_ms': 40000},
            },
        },
    )

    result = cmd_generate(ns_generate('metrics-gen-total'))
    assert result['status'] == 'success'
    # worked total = 120 + 40 = 160 s; wall total = 200 + 100 = 300 s;
    # idle total = (200-120) + (100-40) = 80 + 60 = 140 s.
    assert result['total_worked_seconds'] == 160.0
    assert result['total_wall_seconds'] == 300.0
    assert result['total_idle_seconds'] == 140.0


def test_generate_no_data(plan_context):
    """generate returns error when no metrics data exists."""
    result = cmd_generate(ns_generate('metrics-gen-02'))
    assert result['status'] == 'error'
    assert 'No metrics data' in str(result.get('message', ''))


def test_generate_all_six_phases(plan_context):
    """generate handles all 6 phases."""
    phases = ['1-init', '2-refine', '3-outline', '4-plan', '5-execute', '6-finalize']
    for phase in phases:
        cmd_start_phase(ns_start_phase('metrics-gen-03', phase))
        cmd_end_phase(ns_end_phase('metrics-gen-03', phase))

    result = cmd_generate(ns_generate('metrics-gen-03'))
    assert result['status'] == 'success'
    assert result['phases_recorded'] == 6

    md_content = (plan_context.plan_dir_for('metrics-gen-03') / 'metrics.md').read_text()
    for phase in phases:
        assert phase in md_content


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


# =============================================================================
# Test: enrich delegates to the platform-runtime normalized-tokens op
# =============================================================================

class TestGenerateRendersFourFieldUsage:
    """cmd_generate renders the four usage fields and the billing-weighted total."""

    def test_renders_four_fields_and_billing_total(self, plan_context):
        """metrics.md Phase Details renders each new field plus the billing note."""
        manage_metrics.write_metrics(
            'gen-4f',
            {
                'phases': {
                    '5-execute': {
                        'duration_seconds': 600,
                        'agent_duration_ms': 300000,
                        'input_tokens': 1000,
                        'output_tokens': 200,
                        'cache_read_input_tokens': 10000,
                        'cache_creation_input_tokens': 400,
                        'billing_weighted_total': 2700,
                    },
                },
            },
        )

        result = cmd_generate(ns_generate('gen-4f'))
        assert result['status'] == 'success'

        md = (plan_context.plan_dir_for('gen-4f') / 'metrics.md').read_text()
        assert '- **Input tokens**: 1,000' in md
        assert '- **Output tokens**: 200' in md
        assert '- **Cache read input tokens**: 10,000' in md
        assert '- **Cache creation input tokens**: 400' in md
        assert '- **Billing-weighted total**: 2,700' in md
        # The bullet DEFINES the measure — names its population and its weights —
        # rather than apologising for rendering it.
        assert 'derived-cost population' in md
        assert '0.1 × cache_read' in md
        assert '1.25 × cache_creation' in md
        # And the figure now also has a first-class column of its own.
        assert 'Billing (cost)' in md

    def test_absent_four_fields_render_nothing(self, plan_context):
        """A phase without the four fields renders no usage-view lines (no '- **Input tokens**')."""
        manage_metrics.write_metrics(
            'gen-4f-absent',
            {
                'phases': {
                    '1-init': {'duration_seconds': 100, 'agent_duration_ms': 50000},
                },
            },
        )

        result = cmd_generate(ns_generate('gen-4f-absent'))
        assert result['status'] == 'success'

        md = (plan_context.plan_dir_for('gen-4f-absent') / 'metrics.md').read_text()
        assert '- **Input tokens**' not in md
        assert '- **Billing-weighted total**' not in md

    def test_total_tokens_column_unchanged_alongside_four_fields(self, plan_context):
        """The legacy Tokens column still renders total_tokens when the four fields exist."""
        manage_metrics.write_metrics(
            'gen-4f-coexist',
            {
                'phases': {
                    '5-execute': {
                        'duration_seconds': 600,
                        'agent_duration_ms': 300000,
                        'total_tokens': 50000,
                        'input_tokens': 1000,
                        'output_tokens': 200,
                        'billing_weighted_total': 1200,
                    },
                },
            },
        )

        result = cmd_generate(ns_generate('gen-4f-coexist'))
        assert result['status'] == 'success'
        # total_tokens still flows to the Tokens column / Total tokens detail line.
        assert result['total_tokens'] == 50000
        md = (plan_context.plan_dir_for('gen-4f-coexist') / 'metrics.md').read_text()
        assert '- **Total tokens**: 50,000' in md
        assert '- **Input tokens**: 1,000' in md
