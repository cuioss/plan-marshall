#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""``billing-composition`` under-counting — the cases where the re-derived figure
falls short of the ledger and how each is accounted for.
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


class TestBillingCompositionUnderCounts:
    """The two named under-counts are detected and reported SEPARATELY."""

    def test_close_count_above_one_is_unabsorbed_loop_back(self, tmp_path: Path):
        body = _clean_metrics_body(
            input_tokens=1000,
            output_tokens=500,
            cache_read_input_tokens=200_000,
            cache_creation_input_tokens=8_000,
            close_count=2,
        )
        inputs = _write_billing_plan(tmp_path, 'loopback', body)

        result = audit.cross_billing_composition([inputs])
        row = _billing_row(result, 'loopback')

        assert row['unabsorbed_loop_back'] == _EXECUTE_PHASE
        # Reported SEPARATELY — the other under-count did not fire.
        assert row['omitted_row'] == ''
        assert result['unabsorbed_loop_back_plans'] == 1
        assert result['omitted_row_plans'] == 0
        assert audit._billing_composition_genuine(row) is True

    def test_single_close_is_not_a_loop_back(self, tmp_path: Path):
        body = _clean_metrics_body(
            input_tokens=1000,
            output_tokens=500,
            cache_read_input_tokens=200_000,
            cache_creation_input_tokens=8_000,
            close_count=1,
        )
        inputs = _write_billing_plan(tmp_path, 'single-close', body)

        result = audit.cross_billing_composition([inputs])

        assert _billing_row(result, 'single-close')['unabsorbed_loop_back'] == ''

    def test_missing_canonical_phase_is_an_omitted_row(self, tmp_path: Path):
        # Drop `6-finalize` from an otherwise fully-recorded body.
        body = ''.join(
            _phase_block(
                phase,
                total_tokens=100,
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
            if phase != '6-finalize'
        )
        inputs = _write_billing_plan(tmp_path, 'omitted', body)

        result = audit.cross_billing_composition([inputs])
        row = _billing_row(result, 'omitted')

        assert row['omitted_row'] == '6-finalize'
        assert row['unabsorbed_loop_back'] == ''
        assert result['omitted_row_plans'] == 1
        # An omitted canonical row means the plan's figures are missing weight
        # outright, so the plan is floored.
        assert row['label'] == 'floor'

    def test_persisted_missing_end_time_marker_is_an_omitted_row(
        self, tmp_path: Path
    ):
        # A phase that HAS a section but which the recorder itself marked as
        # never closed is an omitted row too — the marker is consulted, not just
        # structural absence.
        body = (
            'any_phase_missing_end_time: true\n'
            'phases_missing_end_time: 6-finalize\n'
            + ''.join(
                _phase_block(
                    phase,
                    total_tokens=100,
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
        )
        inputs = _write_billing_plan(tmp_path, 'marked', body)

        result = audit.cross_billing_composition([inputs])
        row = _billing_row(result, 'marked')

        assert row['metrics_marker_schema'] == audit.METRICS_SCHEMA_CURRENT
        assert '6-finalize' in row['omitted_row']
        assert row['label'] == 'floor'

    def test_old_schema_marker_floors_the_plan_without_being_read(
        self, tmp_path: Path
    ):
        """A retired-key record floors the plan and is NEVER read for its value.

        Same six present sections as the test above and the same phase named —
        under the RETIRED keys. Two things must hold together: the plan is
        floored (an unknown is a lower bound), and `omitted_row` does NOT name
        6-finalize, because reading the retired keys is exactly what this reader
        refuses to do. Asserting only the floor would not distinguish "refused to
        read" from "read it and agreed".
        """
        body = (
            'partial: true\n'
            'unrecorded_phases: 6-finalize\n'
            + ''.join(
                _phase_block(
                    phase,
                    total_tokens=100,
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
        )
        inputs = _write_billing_plan(tmp_path, 'old-schema-billing', body)

        result = audit.cross_billing_composition([inputs])
        row = _billing_row(result, 'old-schema-billing')

        assert row['metrics_marker_schema'] == audit.METRICS_SCHEMA_OLD
        assert row['omitted_row'] == ''
        assert row['label'] == 'floor'
        # Counted under its own heading, separately from the pre-#812 tally.
        assert result['old_schema_marker_plans'] == 1
        assert result['pre_812_marker_plans'] == 0

    def test_pre_812_marker_tally_is_separate_from_old_schema(self, tmp_path: Path):
        """A record with NEITHER pair lands in the pre-#812 tally, not old-schema.

        The two counts answer different questions — which archives a re-read
        could still recover — so a single merged "unreadable" count would lose
        that.
        """
        body = ''.join(
            _phase_block(phase, total_tokens=100) for phase in audit._TE_PHASES
        )
        # 5-execute needs the billing fields or the plan is excluded outright.
        body = body.replace(
            f'[{_EXECUTE_PHASE}]\n  total_tokens: 100\n',
            _phase_block(
                _EXECUTE_PHASE,
                total_tokens=100,
                input_tokens=1000,
                output_tokens=500,
                cache_read_input_tokens=200_000,
                cache_creation_input_tokens=8_000,
            ),
        )
        inputs = _write_billing_plan(tmp_path, 'pre812-billing', body)

        result = audit.cross_billing_composition([inputs])
        row = _billing_row(result, 'pre812-billing')

        assert row['metrics_marker_schema'] == audit.METRICS_SCHEMA_PRE_812
        assert row['label'] == 'floor'
        assert result['pre_812_marker_plans'] == 1
        assert result['old_schema_marker_plans'] == 0

    def test_undercounted_plans_counts_a_both_ways_plan_once(self, tmp_path: Path):
        """A plan carrying BOTH under-counts is ONE under-counted plan, not two.

        `unabsorbed_loop_back_plans` and `omitted_row_plans` are independent
        per-plan tallies, so summing them double-counts this plan and can
        exceed `plans_in_corpus` — a movement no plan produced.
        """
        # `close_count: 2` on 5-execute (loop-back) AND no 6-finalize section
        # (omitted row) — the same plan trips both under-counts.
        body = ''.join(
            _phase_block(
                phase,
                total_tokens=100,
                **(
                    {
                        'input_tokens': 1000,
                        'output_tokens': 500,
                        'cache_read_input_tokens': 200_000,
                        'cache_creation_input_tokens': 8_000,
                        'close_count': 2,
                    }
                    if phase == _EXECUTE_PHASE
                    else {}
                ),
            )
            for phase in audit._TE_PHASES
            if phase != '6-finalize'
        )
        inputs = _write_billing_plan(tmp_path, 'both-ways', body)

        result = audit.cross_billing_composition([inputs])
        row = _billing_row(result, 'both-ways')

        # Both under-counts fired on this ONE plan.
        assert row['unabsorbed_loop_back'] == _EXECUTE_PHASE
        assert row['omitted_row'] == '6-finalize'
        assert result['unabsorbed_loop_back_plans'] == 1
        assert result['omitted_row_plans'] == 1

        # The distinct count is 1, and it never exceeds the corpus size.
        assert result['undercounted_plans'] == 1
        assert result['undercounted_plans'] <= result['plans_in_corpus']
        # Negative control on the superseded formula: naively summing the two
        # tallies would have reported 2 for a single plan.
        assert (
            result['unabsorbed_loop_back_plans'] + result['omitted_row_plans']
        ) == 2

    def test_undercounted_plans_is_load_bearing_for_disjoint_plans(
        self, tmp_path: Path
    ):
        """Matched control: two DIFFERENT plans each tripping one under-count sum to 2."""
        loopback_body = _clean_metrics_body(
            input_tokens=1000,
            output_tokens=500,
            cache_read_input_tokens=200_000,
            cache_creation_input_tokens=8_000,
            close_count=2,
        )
        omitted_body = ''.join(
            _phase_block(
                phase,
                total_tokens=100,
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
            if phase != '6-finalize'
        )
        a = _write_billing_plan(tmp_path, 'only-loopback', loopback_body)
        b = _write_billing_plan(tmp_path, 'only-omitted', omitted_body)

        result = audit.cross_billing_composition([a, b])

        # Disjoint plans — the distinct count equals the naive sum here, which
        # is what makes the both-ways case above a real discriminator.
        assert result['undercounted_plans'] == 2
        assert result['plans_in_corpus'] == 2
