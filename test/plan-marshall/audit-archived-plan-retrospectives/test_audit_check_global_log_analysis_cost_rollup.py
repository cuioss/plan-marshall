#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""``global-log-analysis`` cumulative cost roll-up — the instrument that answers
"what owns the time?".

The corpus-wide view already carried `call_seconds` and `total_script_seconds`
but ranked ONLY by call count behind a `>= high_frequency_calls` gate. That
answers "who is called most often?", which is a FREQUENCY question. It cannot
answer "what owns the time?": a key below the count gate is dropped entirely
however much time it owns, and above the gate the ordering ignores duration.
The cost roll-up is the complementary instrument — no count gate, ranked by
time owned, with the share of the published denominator.
"""

from pathlib import Path

import pytest
from _audit_fixtures import (
    _line,
    _write_log,
    audit,
)


class TestGlobalLogCostRollup:
    def test_ranks_by_time_owned_not_by_call_count(self, tmp_path: Path):
        # `pm:hot:hot run`  — 60 calls x 0.5s = 30.0s   (most CALLS)
        # `pm:heavy:heavy run` — 4 calls x 20.0s = 80.0s (most TIME)
        lines = [
            _line(f'2026-06-01T10:00:{i % 60:02d}Z', 'INFO', 'pm:hot:hot run (0.5s)')
            for i in range(60)
        ]
        lines += [
            _line(f'2026-06-01T11:0{i}:00Z', 'INFO', 'pm:heavy:heavy run (20.0s)')
            for i in range(4)
        ]
        _write_log(tmp_path, 'script-execution-2026-06-01.log', lines)

        result = audit.cross_global_log_analysis(tmp_path)

        # The FREQUENCY view ranks the most-called key first...
        assert result['high_frequency'][0]['key'] == 'pm:hot:hot run'
        # ...and drops the time-dominant key entirely: 4 calls is under the gate.
        assert all(r['key'] != 'pm:heavy:heavy run' for r in result['high_frequency'])
        # The COST view ranks by time owned and has no count gate.
        assert result['cost_rollup'][0]['key'] == 'pm:heavy:heavy run'
        assert result['cost_rollup'][0]['calls'] == 4
        assert result['cost_rollup'][0]['cumulative_seconds'] == pytest.approx(80.0)
        assert result['cost_rollup'][1]['key'] == 'pm:hot:hot run'

    def test_dominant_fast_caller_is_visible_though_no_call_is_slow(self, tmp_path: Path):
        # 100 calls at 0.2s own 20s of wall-clock while NO single call comes
        # anywhere near the 30s ceiling.
        lines = [
            _line(f'2026-06-01T10:00:{i % 60:02d}Z', 'INFO', 'pm:hot:hot run (0.2s)')
            for i in range(100)
        ]
        lines.append(_line('2026-06-01T11:00:00Z', 'INFO', 'pm:rare:rare run (5.0s)'))
        _write_log(tmp_path, 'script-execution-2026-06-01.log', lines)

        result = audit.cross_global_log_analysis(tmp_path)

        # The per-call ceiling reports nothing at all...
        assert result['slow_call_count'] == 0
        # ...while the roll-up names the script owning 80% of recorded time.
        top = result['cost_rollup'][0]
        assert top['key'] == 'pm:hot:hot run'
        assert top['share_pct'] == pytest.approx(80.0)
        assert top['max_seconds'] == pytest.approx(0.2)

    def test_share_is_a_share_of_the_published_denominator(self, tmp_path: Path):
        _write_log(
            tmp_path,
            'script-execution-2026-06-01.log',
            [
                _line('2026-06-01T10:00:00Z', 'INFO', 'pm:a:a run (30.0s)'),
                _line('2026-06-01T10:00:01Z', 'INFO', 'pm:b:b run (10.0s)'),
            ],
        )

        result = audit.cross_global_log_analysis(tmp_path)

        assert result['total_script_seconds'] == pytest.approx(40.0)
        assert result['cost_rollup'][0]['share_pct'] == pytest.approx(75.0)
        assert result['cost_rollup'][1]['share_pct'] == pytest.approx(25.0)
        assert result['distinct_timed_call_keys'] == 2

    def test_no_script_lines_yields_an_empty_rollup(self, tmp_path: Path):
        _write_log(
            tmp_path,
            'work-2026-06-01.log',
            [_line('2026-06-01T10:00:00Z', 'INFO', '[STATUS] (x) no duration')],
        )

        result = audit.cross_global_log_analysis(tmp_path)

        assert result['cost_rollup'] == []
        assert result['distinct_timed_call_keys'] == 0

    def test_rollup_rows_and_denominator_reach_the_emitted_block(self, tmp_path: Path):
        lines = [
            _line(f'2026-06-01T10:00:{i % 60:02d}Z', 'INFO', 'pm:hot:hot run (0.2s)')
            for i in range(100)
        ]
        _write_log(tmp_path, 'script-execution-2026-06-01.log', lines)

        output = audit.run_checks([], ['global-log-analysis'], tmp_path)

        assert 'cost_rollup_count: 1' in output
        assert 'distinct_timed_call_keys: 1' in output
        # The signal row names the share, so the read-out cannot be quoted
        # without its denominator.
        assert 'dominant-cost-caller' in output
        assert '100x 20.0s 100.0% pm:hot:hot run' in output

    def test_cross_plan_ceiling_constant_unchanged(self):
        # The roll-up was added BESIDE this ceiling precisely so the ceiling need
        # not move. Lowering it would silently redefine `slow_call_count` for
        # every archived plan already measured against it — and every other test
        # here reads the value dynamically, so nothing else would fail.
        assert audit.THRESHOLDS['slow_call_seconds'] == 30.0

    def test_calls_counts_only_timed_calls_not_every_notation_line(self, tmp_path: Path):
        # `call_counts` counts EVERY notation-headed line; only some carry a
        # trailing duration. Pairing an all-lines count with timed-only seconds
        # would publish "2x 5.0s" for a key where one call contributed all 5.0s
        # and the other contributed nothing measured — an absent duration read
        # as a zero, inside the roll-up's own denominator.
        _write_log(
            tmp_path,
            'script-execution-2026-06-01.log',
            [
                _line('2026-06-01T10:00:00Z', 'INFO', 'pm:x:x run (5.0s)'),
                # Same key, no trailing duration: a failure header whose timing
                # lives in a continuation block.
                _line('2026-06-01T10:00:01Z', 'ERROR', 'pm:x:x run -> status: error exit_code=1'),
            ],
        )

        result = audit.cross_global_log_analysis(tmp_path)

        row = result['cost_rollup'][0]
        assert row['key'] == 'pm:x:x run'
        assert row['calls'] == 1
        assert row['cumulative_seconds'] == pytest.approx(5.0)

    def test_untimed_keys_are_named_not_folded_into_the_timed_population(self, tmp_path: Path):
        # A key that never carried a duration cannot be ranked by time owned. It
        # is excluded from `distinct_timed_call_keys` and counted separately, so
        # the roll-up's truncation denominator is not silently inflated by keys
        # the roll-up was never eligible to carry.
        _write_log(
            tmp_path,
            'script-execution-2026-06-01.log',
            [
                _line('2026-06-01T10:00:00Z', 'INFO', 'pm:timed:timed run (1.0s)'),
                _line('2026-06-01T10:00:01Z', 'ERROR', 'pm:untimed:untimed run -> status: error'),
            ],
        )

        result = audit.cross_global_log_analysis(tmp_path)

        assert result['distinct_timed_call_keys'] == 1
        assert result['untimed_call_keys'] == 1
        assert [r['key'] for r in result['cost_rollup']] == ['pm:timed:timed run']

    def test_rollup_rows_are_informational_not_genuine_signals(self, tmp_path: Path):
        # Some key is ALWAYS the corpus's largest cost owner, so a roll-up row is
        # a ranking rather than a defect. Counting these as genuine would report
        # a "signal" for every non-empty corpus and train readers to ignore the
        # count — the noise-source failure this instrument exists to avoid.
        _write_log(
            tmp_path,
            'script-execution-2026-06-01.log',
            [_line('2026-06-01T10:00:00Z', 'INFO', 'pm:a:a run (1.0s)')],
        )

        result = audit.cross_global_log_analysis(tmp_path)
        block = audit.emit_global_log_block(result)

        assert 'cost_rollup_count: 1' in block
        assert 'dominant-cost-caller,1x 1.0s 100.0% pm:a:a run,,informational' in block
        assert 'genuine_signal_count: 0' in block
