#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""``billing-composition`` phase scoping and population — the canonical phase set the
reconstruction runs over, its floor, and the population each figure carries.
"""

from pathlib import Path

from _audit_fixtures import (
    _EXECUTE_PHASE,
    _billing_row,
    _clean_metrics_body,
    _phase_block,
    _write_billing_plan,
    audit,
)


class TestBillingCompositionCanonicalPhaseScoping:
    """Only canonical `_TE_PHASES` sections feed the corpus figures."""

    def test_non_phase_section_is_not_accumulated(self, tmp_path: Path):
        """A `[totals]` roll-up carrying the same keys must not be summed as a phase.

        The parser admits every `[...]` section, so without canonical-phase
        scoping a roll-up section would be added into `billing` and
        `denom_bytes` on top of the phases it already summarises — inflating
        every share's denominator against a phase set the omitted-row check
        never reasons over.
        """
        byte_field = audit._BC_BYTE_FIELDS[0]
        clean = _clean_metrics_body(
            input_tokens=1000,
            output_tokens=500,
            cache_read_input_tokens=200_000,
            cache_creation_input_tokens=8_000,
            **{byte_field: 50_000},
        )
        baseline_inputs = _write_billing_plan(tmp_path, 'no-rollup', clean)
        baseline = audit.cross_billing_composition([baseline_inputs])
        baseline_row = _billing_row(baseline, 'no-rollup')
        # Guard the guard: a zero denominator would make the equality below
        # trivially true whether or not the roll-up was excluded.
        assert baseline_row['billing_total'] > 0
        assert baseline_row['denom_bytes'] > 0

        # The SAME body plus a non-canonical roll-up section repeating the figures.
        with_rollup = clean + _phase_block(
            'totals',
            total_tokens=100,
            input_tokens=1000,
            output_tokens=500,
            cache_read_input_tokens=200_000,
            cache_creation_input_tokens=8_000,
            **{byte_field: 50_000},
        )
        rollup_inputs = _write_billing_plan(tmp_path, 'with-rollup', with_rollup)
        rollup = audit.cross_billing_composition([rollup_inputs])
        rollup_row = _billing_row(rollup, 'with-rollup')

        # The roll-up changed nothing: the figures are identical to the baseline.
        assert rollup_row['billing_total'] == baseline_row['billing_total']
        assert rollup_row['denom_bytes'] == baseline_row['denom_bytes']
        # And it is not reported as an extra recorded phase.
        assert 'totals' not in rollup_row['unabsorbed_loop_back']
        assert 'totals' not in rollup_row['omitted_row']


class TestBillingCompositionFloorAndPopulation:
    """Every figure carries its own population, and a floored figure says so."""

    def test_every_emitted_figure_carries_a_population_and_a_label(
        self, tmp_path: Path
    ):
        inputs = _write_billing_plan(
            tmp_path,
            'pop',
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

        assert result['figures'], 'no figures emitted'
        for figure in result['figures']:
            assert figure['population'] == 1, figure
            assert figure['label'] in {'measured', 'floor'}, figure
            assert 'floor_population' in figure, figure
            assert figure['unit'] in {'share', 'weighted_tokens'}, figure

    def test_populations_are_per_figure_not_per_block(self, tmp_path: Path):
        # The two families are independent: a plan carrying the billing view but
        # NO payload-byte counters contributes to the billing figures only. A
        # single block-level corpus size would overstate the byte figures.
        billing_only = _write_billing_plan(
            tmp_path,
            'billing-only',
            _clean_metrics_body(
                input_tokens=1000,
                output_tokens=500,
                cache_read_input_tokens=200_000,
                cache_creation_input_tokens=8_000,
            ),
        )
        both = _write_billing_plan(
            tmp_path,
            'both',
            _clean_metrics_body(
                input_tokens=1000,
                output_tokens=500,
                cache_read_input_tokens=200_000,
                cache_creation_input_tokens=8_000,
                exploration_result_bytes=400,
                work_result_bytes=600,
            ),
        )

        result = audit.cross_billing_composition([billing_only, both])
        by_figure = {f['figure']: f for f in result['figures']}

        assert result['plans_in_corpus'] == 2
        assert by_figure['billing_share_output_tokens']['population'] == 2
        assert by_figure['byte_share_exploration']['population'] == 1

    def test_metrics_blind_plan_floors_the_figures_it_contributed_to(
        self, tmp_path: Path
    ):
        # A zero-token 5-execute with NO partiality marker is `metrics_blind` —
        # the input-integrity verdict this check consumes rather than re-derives.
        body = ''.join(
            _phase_block(
                phase,
                total_tokens=0 if phase == _EXECUTE_PHASE else 100,
                **(
                    {
                        'input_tokens': 1000,
                        'output_tokens': 500,
                        'cache_read_input_tokens': 200_000,
                        'cache_creation_input_tokens': 8_000,
                    }
                    if phase == _EXECUTE_PHASE
                    else {}
                ),
            )
            for phase in audit._TE_PHASES
        )
        inputs = _write_billing_plan(tmp_path, 'blind', body)

        # Matched control: input-integrity really does call this plan blind, so
        # the floor label below is traceable to that verdict.
        assert _EXECUTE_PHASE in audit.check_input_integrity(inputs)['metrics_blind']

        result = audit.cross_billing_composition([inputs])
        row = _billing_row(result, 'blind')

        assert row['label'] == 'floor'
        assert audit._billing_composition_genuine(row) is True

        # The floor label is per-FIGURE, keyed on contribution — not per-block.
        # This plan carries the billing view but no payload-byte counters, so it
        # contributed to the billing figures only; scoping the loop by
        # `population` is what makes the assertion say what its name says.
        contributed = [f for f in result['figures'] if f['population']]
        assert contributed, 'no figure recorded a contribution'
        for figure in contributed:
            assert figure['label'] == 'floor', figure
            assert figure['floor_population'] == 1, figure

        # Matched complement: the byte figures nobody contributed to stay at a
        # zero population and are NOT floored by association. Without this half
        # the loop above would still pass if `label` were floored block-wide.
        uncontributed = [f for f in result['figures'] if not f['population']]
        assert uncontributed, 'no uncontributed figure — complement is vacuous'
        for figure in uncontributed:
            assert figure['floor_population'] == 0, figure
            assert figure['value'] == 'n/a', figure

    def test_fully_recorded_plan_is_measured_not_floored(self, tmp_path: Path):
        # The matched NEGATIVE control for the floor label: the same shape without
        # the blind phase must come out `measured`, otherwise the label would be
        # unconditional and carry no information.
        inputs = _write_billing_plan(
            tmp_path,
            'measured',
            _clean_metrics_body(
                input_tokens=1000,
                output_tokens=500,
                cache_read_input_tokens=200_000,
                cache_creation_input_tokens=8_000,
            ),
        )

        result = audit.cross_billing_composition([inputs])
        row = _billing_row(result, 'measured')

        assert row['label'] == 'measured'
        assert audit._billing_composition_genuine(row) is False
        for figure in result['figures']:
            assert figure['label'] == 'measured', figure
            assert figure['floor_population'] == 0, figure
