#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""``global-log-analysis`` line parsing — the log-line grammar, per-notation call
aggregation, and duration banding.
"""

from pathlib import Path

from _audit_fixtures import (
    _line,
    _write_log,
    audit,
)


class TestGlobalLogAnalysisLineGrammar:
    """The shared line grammar drives every downstream signal — a line that does
    not match ``_LOG_LINE_RE`` is silently skipped and never counted."""

    def test_well_formed_line_is_counted_by_level(self, tmp_path: Path):
        # two grammar-valid lines at distinct levels
        _write_log(
            tmp_path,
            'work-2026-06-01.log',
            [
                _line('2026-06-01T10:00:00Z', 'INFO', '[STATUS] (x) ok'),
                _line('2026-06-01T10:00:01Z', 'WARNING', '[STATUS] (x) heads up'),
            ],
        )

        result = audit.cross_global_log_analysis(tmp_path)

        # both lines parsed; level buckets reflect each LEVEL cell
        assert result['total_log_lines'] == 2
        assert result['level_counts'] == {'INFO': 1, 'WARNING': 1}

    def test_malformed_lines_are_skipped(self, tmp_path: Path):
        # only the first line matches the bracketed grammar
        _write_log(
            tmp_path,
            'work-2026-06-01.log',
            [
                _line('2026-06-01T10:00:00Z', 'INFO', '[STATUS] (x) ok'),
                'this line has no bracketed timestamp/level/hash prefix',
                '[2026-06-01T10:00:02Z] INFO missing-hash-brackets',
            ],
        )

        result = audit.cross_global_log_analysis(tmp_path)

        # only the single well-formed line is counted
        assert result['total_log_lines'] == 1
        assert result['level_counts'] == {'INFO': 1}

    def test_missing_logs_dir_yields_empty_all_zero_result(self, tmp_path: Path):
        # no .plan/local/logs directory at all
        # best-effort: empty result rather than raising
        result = audit.cross_global_log_analysis(tmp_path)

        assert result['logs_present'] is False
        assert result['total_log_lines'] == 0
        assert result['error_count'] == 0
        assert result['slow_call_count'] == 0
        assert result['high_frequency_count'] == 0
        assert result['fixture_leak_count'] == 0


class TestGlobalLogAnalysisCallAggregation:
    """Script-execution lines aggregate per ``notation subcommand`` key, summing
    call counts and durations across the corpus."""

    def test_calls_aggregate_per_notation_and_subcommand(self, tmp_path: Path):
        # three calls: two share a key, one is a different subcommand
        _write_log(
            tmp_path,
            'script-execution-2026-06-01.log',
            [
                _line('2026-06-01T10:00:00Z', 'INFO', 'pm:manage-tasks:manage-tasks read --plan-id p (0.10s)'),
                _line('2026-06-01T10:00:01Z', 'INFO', 'pm:manage-tasks:manage-tasks read --plan-id q (0.20s)'),
                _line('2026-06-01T10:00:02Z', 'INFO', 'pm:manage-tasks:manage-tasks update --status done (0.30s)'),
            ],
        )

        result = audit.cross_global_log_analysis(tmp_path)

        # total wall-clock summed; per-key aggregation distinct by subcommand
        assert result['total_script_seconds'] == 0.6
        # no high-frequency / slow rows at these low counts/durations
        assert result['high_frequency_count'] == 0
        assert result['slow_call_count'] == 0

    def test_high_frequency_caller_flagged_at_ceiling(self, tmp_path: Path):
        # exactly high_frequency_calls (50) identical-key calls
        ceiling = audit.THRESHOLDS['high_frequency_calls']
        lines = [
            _line(
                '2026-06-01T10:00:00Z',
                'INFO',
                'pm:manage-logging:manage-logging work --plan-id p (0.01s)',
            )
            for _ in range(ceiling)
        ]
        _write_log(tmp_path, 'script-execution-2026-06-01.log', lines)

        result = audit.cross_global_log_analysis(tmp_path)

        # the >=ceiling key surfaces as a single high-frequency row
        assert result['high_frequency_count'] == 1
        row = result['high_frequency'][0]
        assert row['count'] == ceiling
        assert row['key'] == 'pm:manage-logging:manage-logging work'

    def test_below_high_frequency_ceiling_not_flagged(self, tmp_path: Path):
        # one call below the (50) ceiling
        ceiling = audit.THRESHOLDS['high_frequency_calls']
        lines = [
            _line('2026-06-01T10:00:00Z', 'INFO', 'pm:manage-files:manage-files exists --file f (0.01s)')
            for _ in range(ceiling - 1)
        ]
        _write_log(tmp_path, 'script-execution-2026-06-01.log', lines)

        result = audit.cross_global_log_analysis(tmp_path)

        # under threshold, no high-frequency row
        assert result['high_frequency_count'] == 0


class TestGlobalLogAnalysisDurationBands:
    """Durations split into three bands: normal (< slow), slow
    (slow <= d < impossible), and impossible (>= impossible ceiling)."""

    def test_slow_call_flagged_at_slow_ceiling(self, tmp_path: Path):
        # a call exactly at slow_call_seconds (30.0)
        slow = audit.THRESHOLDS['slow_call_seconds']
        _write_log(
            tmp_path,
            'script-execution-2026-06-01.log',
            [
                _line(
                    '2026-06-01T10:00:00Z',
                    'INFO',
                    f'pm:build-pyproject:pyproject_build run --command-args verify ({slow:.1f}s)',
                ),
            ],
        )

        result = audit.cross_global_log_analysis(tmp_path)

        # lands in the slow band, not impossible
        assert result['slow_call_count'] == 1
        assert result['impossible_count'] == 0
        assert result['slow_calls'][0]['seconds'] == slow

    def test_fast_call_not_flagged_slow(self, tmp_path: Path):
        # just under the slow ceiling
        _write_log(
            tmp_path,
            'script-execution-2026-06-01.log',
            [_line('2026-06-01T10:00:00Z', 'INFO', 'pm:s:s run (29.9s)')],
        )

        result = audit.cross_global_log_analysis(tmp_path)

        assert result['slow_call_count'] == 0
        assert result['impossible_count'] == 0

    def test_impossible_duration_flagged_separately_from_slow(self, tmp_path: Path):
        # a hang-shaped duration at the impossible ceiling (600s)
        _write_log(
            tmp_path,
            'script-execution-2026-06-01.log',
            [_line('2026-06-01T10:00:00Z', 'INFO', 'pm:s:s run (650.0s)')],
        )

        result = audit.cross_global_log_analysis(tmp_path)

        # counted as impossible, NOT double-counted as slow
        assert result['impossible_count'] == 1
        assert result['slow_call_count'] == 0
        assert result['impossible_calls'][0]['seconds'] == 650.0

    def test_slow_calls_sorted_descending_by_seconds(self, tmp_path: Path):
        # two slow calls of differing magnitude
        _write_log(
            tmp_path,
            'script-execution-2026-06-01.log',
            [
                _line('2026-06-01T10:00:00Z', 'INFO', 'pm:a:a run (35.0s)'),
                _line('2026-06-01T10:00:01Z', 'INFO', 'pm:b:b run (90.0s)'),
            ],
        )

        result = audit.cross_global_log_analysis(tmp_path)

        # slowest first
        seconds = [r['seconds'] for r in result['slow_calls']]
        assert seconds == [90.0, 35.0]
