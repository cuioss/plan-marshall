# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for ``analyze-logs.py``."""


from __future__ import annotations

import pytest
from _analyze_logs_fixtures import _analyze_logs, _line, _write_folded_log

# =============================================================================
# Voluntary-checkpoint polling detector (tightened)
# =============================================================================

class TestPerCallCeilingPreserved:
    """The per-call ceiling keeps its predicate and its count when the roll-up lands."""

    def test_ceiling_constant_unchanged(self):
        # The ceiling is blind to the dominant-but-fast class, and it is still
        # not the thing to move. Changing this value would silently redefine
        # ``slow_call_count`` for every archived plan already measured against it.
        assert _analyze_logs._GLOBAL_LOG_SLOW_SECONDS == 30.0

    def test_slow_call_count_still_fires_at_the_ceiling(self, tmp_path):
        logs_dir = tmp_path / 'logs'
        _write_folded_log(
            logs_dir,
            'script-execution-2026-06-01.log',
            [
                _line('2026-06-01T10:00:00Z', 'INFO', 'pm:a:a run (30.0s)'),
                _line('2026-06-01T10:00:01Z', 'INFO', 'pm:b:b run (1.0s)'),
            ],
        )

        signals = _analyze_logs.analyze_folded_global_logs(logs_dir)

        assert signals['slow_call_count'] == 1
        assert signals['cost_rollup']['calls_at_or_over_ceiling'] == 1


class TestContextPositionCost:
    """Marginal cost scales with WHERE a step runs, not only with what it does."""

    def _phase(self, rows):
        return {'present': True, 'rows': rows}

    def test_reports_per_phase_rate_and_position_multiple(self):
        per_phase = {
            '4-plan': self._phase([
                {'tool_uses': 10, 'cache_read_input_tokens': 100_000},
            ]),
            '6-finalize': self._phase([
                {'tool_uses': 10, 'cache_read_input_tokens': 1_000_000},
            ]),
        }

        result = _analyze_logs.summarize_context_position_cost(per_phase)

        by_phase = {row['phase']: row for row in result['by_phase']}
        assert by_phase['4-plan']['cache_read_per_tool_use'] == pytest.approx(10_000.0)
        assert by_phase['6-finalize']['cache_read_per_tool_use'] == pytest.approx(100_000.0)
        # An order of magnitude between phases, which is the reported dimension.
        assert result['position_multiple'] == pytest.approx(10.0)

    def test_unmeasured_row_is_excluded_never_read_as_zero(self):
        # A row whose cache_read column was unmeasured/indeterminate carries NO
        # key. Folding it in as 0 would understate the rate; it is excluded and
        # counted instead.
        per_phase = {
            '5-execute': self._phase([
                {'tool_uses': 10, 'cache_read_input_tokens': 500_000},
                {'tool_uses': 10},  # unmeasured -> excluded
            ]),
        }

        result = _analyze_logs.summarize_context_position_cost(per_phase)

        row = result['by_phase'][0]
        assert row['rows'] == 2
        assert row['measured_rows'] == 1
        assert row['cache_read_per_tool_use'] == pytest.approx(50_000.0)
        assert result['measured_rows'] == 1
        assert result['unmeasured_rows'] == 1

    def test_zero_tool_uses_is_undefined_not_unmeasured(self):
        # The row WAS measured; the ratio simply cannot be formed. Reporting it
        # as `unmeasured` would claim a recording gap that does not exist.
        per_phase = {'6-finalize': self._phase([{'tool_uses': 0, 'cache_read_input_tokens': 900}])}

        result = _analyze_logs.summarize_context_position_cost(per_phase)

        assert result['by_phase'][0]['cache_read_per_tool_use'] == 'undefined'
        assert result['measured_rows'] == 0
        assert result['no_tool_use_rows'] == 1
        assert result['unmeasured_rows'] == 0

    def test_absent_key_and_zero_tool_uses_are_counted_apart(self):
        # The two exclusion causes need different remedies, so they are never
        # summed into one bucket. The three counts reconcile against total_rows.
        per_phase = {
            '5-execute': self._phase([
                {'tool_uses': 4, 'cache_read_input_tokens': 4_000},
                {'tool_uses': 9},                                   # writer recorded nothing
                {'tool_uses': 0, 'cache_read_input_tokens': 700},   # recorded, ratio undefined
            ]),
        }

        result = _analyze_logs.summarize_context_position_cost(per_phase)

        assert result['total_rows'] == 3
        assert result['measured_rows'] == 1
        assert result['unmeasured_rows'] == 1
        assert result['no_tool_use_rows'] == 1
        assert (
            result['measured_rows'] + result['unmeasured_rows'] + result['no_tool_use_rows']
            == result['total_rows']
        )

    def test_undefined_requires_a_complete_phase_record(self):
        # `undefined` asserts the record is complete. A phase carrying BOTH an
        # unmeasured row and a zero-tool-use row is NOT complete, so the weaker
        # `unmeasured` is the honest token — claiming `undefined` here would
        # assert completeness the phase does not have.
        per_phase = {
            '5-execute': self._phase([
                {'tool_uses': 5},                                  # writer recorded nothing
                {'tool_uses': 0, 'cache_read_input_tokens': 10},   # recorded, ratio undefined
            ]),
        }

        result = _analyze_logs.summarize_context_position_cost(per_phase)

        assert result['by_phase'][0]['cache_read_per_tool_use'] == 'unmeasured'
        assert result['unmeasured_rows'] == 1
        assert result['no_tool_use_rows'] == 1

    def test_missing_tool_uses_key_is_a_recording_gap_not_an_undefined_ratio(self):
        # A rate needs a numerator the writer measured AND a denominator it
        # recorded. A row missing `tool_uses` entirely is a writer-side gap, so
        # it belongs in `unmeasured_rows` — not in `no_tool_use_rows`, whose
        # contract states that nothing is missing from the record.
        per_phase = {'5-execute': self._phase([{'cache_read_input_tokens': 900}])}

        result = _analyze_logs.summarize_context_position_cost(per_phase)

        assert result['unmeasured_rows'] == 1
        assert result['no_tool_use_rows'] == 0
        assert result['by_phase'][0]['cache_read_per_tool_use'] == 'unmeasured'

    def test_null_tool_uses_is_a_recording_gap_not_a_complete_record(self):
        # `undefined` asserts the record is complete, so a null denominator must
        # not reach it: folding None into 0 would claim completeness on the
        # strength of a value the writer failed to record.
        per_phase = {
            '5-execute': self._phase([{'cache_read_input_tokens': 900, 'tool_uses': None}]),
        }

        result = _analyze_logs.summarize_context_position_cost(per_phase)

        assert result['unmeasured_rows'] == 1
        assert result['no_tool_use_rows'] == 0
        assert result['by_phase'][0]['cache_read_per_tool_use'] == 'unmeasured'

    def test_null_cache_read_is_a_recording_gap_not_a_crash(self):
        # The numerator needs the same guard as the denominator. Unguarded, a
        # null here reaches the accumulator and raises TypeError, crashing log
        # analysis on a row this function exists to classify as a gap.
        per_phase = {
            '5-execute': self._phase([{'cache_read_input_tokens': None, 'tool_uses': 5}]),
        }

        result = _analyze_logs.summarize_context_position_cost(per_phase)

        assert result['unmeasured_rows'] == 1
        assert result['measured_rows'] == 0
        assert result['by_phase'][0]['cache_read_per_tool_use'] == 'unmeasured'

    def test_non_numeric_cache_read_is_a_recording_gap(self):
        # A string that looks like a number is still not a recorded measurement.
        per_phase = {
            '5-execute': self._phase([{'cache_read_input_tokens': '900', 'tool_uses': 5}]),
        }

        result = _analyze_logs.summarize_context_position_cost(per_phase)

        assert result['unmeasured_rows'] == 1
        assert result['measured_rows'] == 0

    def test_negative_cache_read_is_a_recording_gap(self):
        # A negative token count is corruption, not a measurement.
        per_phase = {
            '5-execute': self._phase([{'cache_read_input_tokens': -5, 'tool_uses': 5}]),
        }

        result = _analyze_logs.summarize_context_position_cost(per_phase)

        assert result['unmeasured_rows'] == 1
        assert result['measured_rows'] == 0

    def test_bool_value_is_a_recording_gap_not_the_count_one(self):
        # `bool` is an `int` subclass, so `True` would otherwise pass as the
        # count 1 and assert a measurement nobody recorded.
        per_phase = {
            '5-execute': self._phase([{'cache_read_input_tokens': True, 'tool_uses': 5}]),
        }

        result = _analyze_logs.summarize_context_position_cost(per_phase)

        assert result['unmeasured_rows'] == 1
        assert result['measured_rows'] == 0

    def test_negative_tool_uses_is_a_recording_gap(self):
        # A negative call count is corruption, not an undefined ratio.
        per_phase = {
            '5-execute': self._phase([{'cache_read_input_tokens': 900, 'tool_uses': -3}]),
        }

        result = _analyze_logs.summarize_context_position_cost(per_phase)

        assert result['unmeasured_rows'] == 1
        assert result['no_tool_use_rows'] == 0

    def test_phase_with_no_rows_reports_the_weaker_token(self):
        # An empty phase has no zero-tool-use row to justify `undefined`, which
        # would assert a complete record. `unmeasured` is the honest default.
        per_phase = {'5-execute': self._phase([])}

        result = _analyze_logs.summarize_context_position_cost(per_phase)

        assert result['by_phase'][0]['rows'] == 0
        assert result['by_phase'][0]['cache_read_per_tool_use'] == 'unmeasured'

    def test_basis_names_two_distinct_phases_when_rates_tie(self):
        # `max` and `min` both return the first maximal element, so equal rates
        # would make the basis read `{phase}/{phase}` — a label contradicting its
        # own contract beside a perfectly correct multiple of 1.0.
        per_phase = {
            '4-plan': self._phase([{'tool_uses': 5, 'cache_read_input_tokens': 500}]),
            '6-finalize': self._phase([{'tool_uses': 5, 'cache_read_input_tokens': 500}]),
        }

        result = _analyze_logs.summarize_context_position_cost(per_phase)

        assert result['position_multiple'] == pytest.approx(1.0)
        highest, lowest = result['position_multiple_basis'].split('/')
        assert highest != lowest

    def test_zero_denominator_multiple_is_undefined_not_unmeasured(self):
        # Two phases DO carry rates, so nothing is missing — but the lowest is
        # 0.0 and the division cannot be performed.
        per_phase = {
            '4-plan': self._phase([{'tool_uses': 5, 'cache_read_input_tokens': 0}]),
            '6-finalize': self._phase([{'tool_uses': 5, 'cache_read_input_tokens': 5_000}]),
        }

        result = _analyze_logs.summarize_context_position_cost(per_phase)

        assert result['by_phase'][0]['cache_read_per_tool_use'] == 0.0
        assert result['position_multiple'] == 'undefined'
        assert result['position_multiple_basis'] == 'undefined'

    def test_single_measured_phase_cannot_yield_a_multiple(self):
        # A multiple needs two phases to compare; one is not a position signal.
        per_phase = {'5-execute': self._phase([{'tool_uses': 5, 'cache_read_input_tokens': 5_000}])}

        result = _analyze_logs.summarize_context_position_cost(per_phase)

        assert result['position_multiple'] == 'unmeasured'
        assert result['position_multiple_basis'] == 'unmeasured'

    def test_no_boundary_artifacts_publishes_an_empty_population(self):
        result = _analyze_logs.summarize_context_position_cost({})

        assert result['total_rows'] == 0
        assert result['measured_rows'] == 0
        assert result['by_phase'] == []
        assert result['position_multiple'] == 'unmeasured'
