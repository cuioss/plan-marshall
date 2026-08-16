#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""``billing-composition`` payload-byte shares and emission — byte-share derivation,
the absent-is-not-zero rule, and the emitted block.
"""

from pathlib import Path

from _audit_fixtures import (
    _billing_row,
    _clean_metrics_body,
    _phase_block,
    _write_billing_plan,
    _write_shipping_plan,
    audit,
)


class TestBillingCompositionByteShares:
    """The four byte shares are taken over ALL buckets, residual included."""

    def test_byte_shares_use_the_whole_observed_payload_population(
        self, tmp_path: Path
    ):
        inputs = _write_billing_plan(
            tmp_path,
            'bytes',
            _clean_metrics_body(
                input_tokens=1000,
                output_tokens=500,
                cache_read_input_tokens=200_000,
                cache_creation_input_tokens=8_000,
                exploration_result_bytes=400,
                work_result_bytes=300,
                execute_result_bytes=200,
                orchestration_result_bytes=50,
                unclassified_result_bytes=50,
            ),
        )

        result = audit.cross_billing_composition([inputs])
        row = _billing_row(result, 'bytes')

        # Denominator is 1000 (all five buckets), NOT 950 (the four named ones).
        assert row['denom_bytes'] == 1000
        assert row['residual_bytes'] == 50
        assert row['exploration_byte_share'] == '40.0%'
        assert row['work_byte_share'] == '30.0%'
        assert row['execute_byte_share'] == '20.0%'
        assert row['orchestration_byte_share'] == '5.0%'
        # Re-normalising over the four named sources would give 42.1% — the
        # inflation this denominator choice exists to prevent.
        assert row['exploration_byte_share'] != '42.1%'

    def test_residual_is_never_folded_into_a_named_share(self, tmp_path: Path):
        # `unclassified` is emitted as a raw byte count, never as a fifth share,
        # so the four named shares plus the residual account for the whole.
        inputs = _write_billing_plan(
            tmp_path,
            'residual',
            _clean_metrics_body(
                input_tokens=1000,
                exploration_result_bytes=500,
                unclassified_result_bytes=500,
            ),
        )

        result = audit.cross_billing_composition([inputs])
        row = _billing_row(result, 'residual')

        assert row['exploration_byte_share'] == '50.0%'
        assert row['residual_bytes'] == 500
        assert 'unclassified_byte_share' not in row
        figure_names = {f['figure'] for f in result['figures']}
        assert 'byte_share_unclassified' not in figure_names


class TestBillingCompositionAbsentIsNotZero:
    """A plan that measured neither family is excluded, never admitted at zero."""

    def test_plan_measuring_neither_family_is_excluded_and_named(
        self, tmp_path: Path
    ):
        # A metrics.toon carrying only durations — no four-field view, no byte
        # counters — measured nothing this check can read.
        body = ''.join(
            _phase_block(phase, total_tokens=100, duration_seconds=5)
            for phase in audit._TE_PHASES
        )
        inputs = _write_billing_plan(tmp_path, 'unmeasured', body)

        result = audit.cross_billing_composition([inputs])

        assert result['plans_in_corpus'] == 0
        assert result['rows'] == []
        assert result['plans_excluded_no_counters'] == 1
        assert result['excluded_plan_ids'] == ['unmeasured']

    def test_measured_zero_stays_in_the_corpus(self, tmp_path: Path):
        # The matched control for the exclusion: a PRESENT four-field view whose
        # values are zero is a real observation and is NOT excluded.
        inputs = _write_billing_plan(
            tmp_path,
            'measured-zero',
            _clean_metrics_body(
                input_tokens=0,
                output_tokens=0,
                cache_read_input_tokens=0,
                cache_creation_input_tokens=0,
            ),
        )

        result = audit.cross_billing_composition([inputs])

        assert result['plans_in_corpus'] == 1
        assert result['excluded_plan_ids'] == []

    def test_empty_corpus_degrades_without_raising(self):
        result = audit.cross_billing_composition([])

        assert result['plans_in_corpus'] == 0
        assert result['rows'] == []
        # Every figure is still emitted, each honestly reporting a zero population.
        assert result['figures']
        for figure in result['figures']:
            assert figure['population'] == 0, figure


class TestBillingCompositionEmit:
    """The emitted block shape: a figures table plus the per-plan audit rows."""

    def test_block_carries_both_tables_and_the_severity_column(self, tmp_path: Path):
        inputs = _write_billing_plan(
            tmp_path,
            'emit',
            _clean_metrics_body(
                input_tokens=1000,
                output_tokens=500,
                cache_read_input_tokens=200_000,
                cache_creation_input_tokens=8_000,
                close_count=2,
            ),
        )
        result = audit.cross_billing_composition([inputs])

        block = audit.emit_billing_composition_block(result)

        assert 'check: billing-composition' in block
        assert 'status: success' in block
        assert 'plans_in_corpus: 1' in block
        assert 'unabsorbed_loop_back_plans: 1' in block
        assert 'omitted_row_plans: 0' in block
        assert 'genuine_signal_count: 1' in block
        assert (
            'figures[8]{figure,unit,value,population,floor_population,label}:'
            in block
        )
        assert (
            'rows[1]{plan_id,billing_total,cache_read_share,cache_creation_share,'
            'output_share,exploration_byte_share,work_byte_share,'
            'execute_byte_share,orchestration_byte_share,residual_bytes,'
            'denom_bytes,reconciled_phases,unabsorbed_loop_back,omitted_row,'
            'metrics_marker_schema,label,severity}:' in block
        )
        # The two unreadable-marker tallies ride the block header, counted apart.
        assert 'old_schema_marker_plans: 0' in block
        assert 'pre_812_marker_plans: 0' in block
        genuine_row = next(
            ln.strip() for ln in block.splitlines() if ln.strip().startswith('emit,')
        )
        assert genuine_row.endswith(',genuine')
        # The schema cell renders the readable state for this clean fixture.
        assert f',{audit.METRICS_SCHEMA_CURRENT},' in genuine_row

    def test_block_states_the_reconciliation_and_exclusion_rules(
        self, tmp_path: Path
    ):
        # The rules ride the block so a reader can never mistake the
        # reconciliation for a sum, or an excluded plan for a zero share.
        result = audit.cross_billing_composition([])

        block = audit.emit_billing_composition_block(result)

        assert 'reconciliation_rule:' in block
        assert 'NOT a sum' in block
        assert 'exclusion_rule:' in block
        assert 'byte_denominator:' in block

    def test_full_run_annotates_the_non_shipping_exclusion(self, tmp_path: Path):
        # billing-composition is a delivery-cost check, so a plan with no delivery
        # evidence is partitioned out and NAMED — a number distinct from
        # `plans_excluded_no_counters`.
        shipping = _write_billing_plan(
            tmp_path,
            'ships',
            _clean_metrics_body(
                input_tokens=1000,
                output_tokens=500,
                cache_read_input_tokens=200_000,
                cache_creation_input_tokens=8_000,
            ),
        )
        no_ship = _write_shipping_plan(
            tmp_path, 'no-ship', archived_reason='closed_superseded'
        )

        output = audit.run_checks(
            [shipping, no_ship], ['billing-composition'], tmp_path
        )

        assert 'plans_excluded_non_shipping: 1' in output
        assert 'excluded_non_shipping_plan_ids: no-ship:closed_superseded' in output
        assert 'ships' in output
