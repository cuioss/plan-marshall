#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The ``global-log-analysis`` emitted block — its columns, severity, and the
metrics window it reports over.
"""

from pathlib import Path

from _audit_fixtures import (
    _line,
    _write_log,
    _write_metrics_window,
    audit,
)


class TestEmitGlobalLogBlock:
    """``emit_global_log_block`` renders the result dict to a TOON block: every
    flagged line is a genuine signal, ad-hoc attribution fills empty windows, and
    the summary lines carry the level buckets and per-band counts."""

    def test_block_carries_summary_lines_and_genuine_count(self, tmp_path: Path):
        # one genuine ERROR failure (carries failure markers) + one slow call
        _write_metrics_window(
            tmp_path, 'plan-x', '2026-06-01T10:00:00Z', '2026-06-01T11:00:00Z'
        )
        _write_log(
            tmp_path,
            'script-execution-2026-06-01.log',
            [
                # A real failure: carries markers (status: error / exit_code=1) and is
                # NOT a bare script-call probe, so the corrected flagger flags it.
                _line('2026-06-01T10:10:00Z', 'ERROR', 'pm:x:x run -> status: error exit_code=1'),
                _line('2026-06-01T10:20:00Z', 'INFO', 'pm:y:y run (40.0s)'),
            ],
        )
        result = audit.cross_global_log_analysis(tmp_path)

        block = audit.emit_global_log_block(result)

        # header, counts, and a genuine-only signal total
        assert 'check: global-log-analysis' in block
        assert 'status: success' in block
        # one error line + one slow call = 2 genuine signals
        assert 'genuine_signal_count: 2' in block
        assert 'error_count: 1' in block
        assert 'slow_call_count: 1' in block
        assert 'rows[2]{kind,detail,attributed_plans,severity}:' in block

    def test_debug_and_benign_probes_excluded_from_error_count(self, tmp_path: Path):
        # The corrected flagger flags only elevated levels (>=WARNING) + real failure
        # markers, and excludes (a) DEBUG diagnostics (below INFO) and (b) bare
        # script-call probes at an elevated level with no failure marker (a benign
        # non-zero-exit query such as `exists`/`read` answering "not found").
        _write_metrics_window(
            tmp_path, 'plan-x', '2026-06-01T10:00:00Z', '2026-06-01T11:00:00Z'
        )
        _write_log(
            tmp_path,
            'script-execution-2026-06-01.log',
            [
                # DEBUG diagnostic — NOT an error.
                _line('2026-06-01T10:05:00Z', 'DEBUG', 'pm:a:a resolve cache hit'),
                # benign ERROR-level probe: a completed script call (has a duration)
                # with no failure marker — a "not found" boolean query, NOT a failure.
                _line('2026-06-01T10:10:00Z', 'ERROR', 'pm:f:f exists (0.21s)'),
                # a genuine marker-bearing failure IS still flagged at any level.
                _line('2026-06-01T10:20:00Z', 'INFO', 'pm:g:g check Traceback (most recent call last)'),
            ],
        )
        result = audit.cross_global_log_analysis(tmp_path)

        block = audit.emit_global_log_block(result)

        # Only the Traceback line is a genuine error; DEBUG + benign probe excluded.
        assert 'error_count: 1' in block
        assert 'genuine_signal_count: 1' in block

    def test_non_query_command_at_error_is_not_a_benign_probe(self, tmp_path: Path):
        # The benign-probe exclusion is restricted to read-only QUERY subcommands.
        # A non-query command (e.g. `run`) at ERROR with no failure marker must STILL
        # be flagged — it is a genuine failure, not a "not found" probe.
        _write_metrics_window(
            tmp_path, 'plan-x', '2026-06-01T10:00:00Z', '2026-06-01T11:00:00Z'
        )
        _write_log(
            tmp_path,
            'script-execution-2026-06-01.log',
            [
                # ERROR-level `run` call, has a duration, NO failure marker — not a query.
                _line('2026-06-01T10:10:00Z', 'ERROR', 'pm:b:b run (0.50s)'),
                # ERROR-level `exists` query with a duration — benign, excluded.
                _line('2026-06-01T10:20:00Z', 'ERROR', 'pm:f:f exists (0.21s)'),
            ],
        )
        result = audit.cross_global_log_analysis(tmp_path)

        block = audit.emit_global_log_block(result)

        # the `run` failure is flagged; the `exists` probe is not
        assert 'error_count: 1' in block

    def test_empty_result_renders_zero_signal_block(self, tmp_path: Path):
        # no logs at all
        result = audit.cross_global_log_analysis(tmp_path)

        block = audit.emit_global_log_block(result)

        # well-formed block with zero rows and zero genuine signals
        assert 'genuine_signal_count: 0' in block
        assert 'logs_present: false' in block
        assert 'rows[0]{kind,detail,attributed_plans,severity}:' in block

    def test_ad_hoc_attribution_when_no_enclosing_window(self, tmp_path: Path):
        # an error line with no plan window covering it
        _write_log(
            tmp_path,
            'work-2026-06-01.log',
            [_line('2026-06-01T10:00:00Z', 'ERROR', 'orphaned error with no window')],
        )
        result = audit.cross_global_log_analysis(tmp_path)

        block = audit.emit_global_log_block(result)

        # the empty attribution renders as the literal ad-hoc sentinel
        assert 'ad-hoc' in block

    def test_global_log_analysis_in_check_registry(self):
        # the check is registered and cross-plan scoped
        assert 'global-log-analysis' in audit.CHECK_NAMES
        assert 'global-log-analysis' in audit.CROSS_PLAN_CHECKS
