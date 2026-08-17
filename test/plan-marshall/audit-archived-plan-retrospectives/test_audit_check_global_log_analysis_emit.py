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
    minimal_corpus,
)


def _latest_report_metrics(repo_root: Path) -> dict:
    """Parse the summary-metric header of the report `run_checks` just persisted."""
    reports = sorted((repo_root / audit.AUDIT_REPORTS_REL).glob('*.toon'))
    return audit._parse_report_summary_metrics(reports[-1])


class TestEmitGlobalLogBlock:
    """``emit_global_log_block`` renders the result dict to a TOON block: every
    flagged line is a genuine signal and every cost-roll-up ranking row is
    informational, ad-hoc attribution fills empty windows, and the summary lines
    carry the level buckets and per-band counts."""

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
        # 3 rows, 2 of them genuine: the third is the cost roll-up's ranking row
        # for the one timed call, stamped `informational` so it does not inflate
        # the genuine count above.
        assert 'rows[3]{kind,detail,attributed_plans,severity}:' in block
        assert 'dominant-cost-caller,1x 40.000s 100.0% pm:y:y run,,informational' in block

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

    def test_absent_logs_report_unmeasured_not_a_zero_signal_block(self, tmp_path: Path):
        """No log directory means no substrate was read, so no count is published.

        This block previously rendered `genuine_signal_count: 0` beside
        `logs_present: false` — a zero that reads as health from a corpus that
        said nothing. The suspect-zero census then read that zero and reported
        `disciplinary`, asserting a non-empty population had been examined.
        """
        result = audit.cross_global_log_analysis(tmp_path)

        block = audit.emit_global_log_block(result)

        assert 'status: unmeasured' in block
        assert 'logs_present: false' in block
        assert 'unmeasured_reason:' in block
        # The counts a reader would take as a verdict are ABSENT, not zeroed.
        assert 'genuine_signal_count:' not in block
        assert 'error_count:' not in block
        assert 'rows[' not in block

    def test_present_but_empty_log_dir_reports_unmeasured(self, tmp_path: Path):
        """The directory exists and holds no matching log — no substrate was read.

        Gating on the DIRECTORY probe alone left this state publishing
        `total_log_lines: 0` and `genuine_signal_count: 0`, which the suspect-zero
        census then reported as `disciplinary`. It is not hypothetical: this
        tool's own `--dormate-global-logs` relocates completed logs out of a
        directory it leaves in place.
        """
        logs_dir = tmp_path / '.plan' / 'local' / 'logs'
        logs_dir.mkdir(parents=True)
        (logs_dir / 'not-a-log.txt').write_text('x', encoding='utf-8')

        result = audit.cross_global_log_analysis(tmp_path)

        assert result['logs_present'] is True
        assert result['logs_readable'] is False
        block = audit.emit_global_log_block(result)
        assert 'status: unmeasured' in block
        assert 'genuine_signal_count:' not in block

    def test_present_logs_with_no_signals_are_a_measured_zero(self, tmp_path: Path):
        """The discriminating half — substrate read, genuinely nothing to flag."""
        _write_log(
            tmp_path,
            'work-2026-06-01.log',
            [_line('2026-06-01T10:00:00Z', 'INFO', 'an unremarkable line')],
        )
        result = audit.cross_global_log_analysis(tmp_path)

        block = audit.emit_global_log_block(result)

        assert 'status: success' in block
        assert 'logs_present: true' in block
        assert 'genuine_signal_count: 0' in block
        assert 'rows[0]{kind,detail,attributed_plans,severity}:' in block

    def test_unreadable_log_file_is_not_readable_substrate(self, tmp_path: Path):
        """A file that EXISTS is not a file that was READ.

        The read loop swallows `OSError` per file, and a file whose lines match no
        grammar contributes nothing, so file-existence alone re-opened every
        surface the unmeasured branch closes.
        """
        _write_log(tmp_path, 'work-2026-06-01.log', ['not a parseable log line at all'])

        result = audit.cross_global_log_analysis(tmp_path)

        assert result['logs_present'] is True
        assert result['logs_readable'] is False
        assert 'status: unmeasured' in audit.emit_global_log_block(result)

    def test_unmeasured_run_withholds_the_summary_metrics(self, tmp_path: Path):
        """Surface (b) of the contract: nothing unsupported reaches the cross-run diff.

        `_report_diff_block` cannot tell a persisted 0 from a real one after the
        fact, so an unmeasured run must persist neither.
        """
        inputs = minimal_corpus(tmp_path)
        audit.run_checks(inputs, ['global-log-analysis'], tmp_path)
        report = _latest_report_metrics(tmp_path)

        assert 'global-log-analysis_errors' not in report
        assert 'global-log-analysis_fixture_leaks' not in report

    def test_measured_run_does_persist_the_summary_metrics(self, tmp_path: Path):
        """The discriminator — suppression must not silence a real zero."""
        _write_log(
            tmp_path,
            'work-2026-06-01.log',
            [_line('2026-06-01T10:00:00Z', 'INFO', 'an unremarkable line')],
        )
        inputs = minimal_corpus(tmp_path)
        audit.run_checks(inputs, ['global-log-analysis'], tmp_path)
        report = _latest_report_metrics(tmp_path)

        assert report['global-log-analysis_errors'] == 0

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
