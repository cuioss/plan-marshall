#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""``global-log-analysis`` flagging — error-line flagging, per-plan attribution, and
the guard that keeps a test fixture's own log lines out of the corpus result.
"""

from pathlib import Path

from _audit_fixtures import (
    _line,
    _write_log,
    _write_metrics_window,
    audit,
)


class TestGlobalLogAnalysisErrorFlagging:
    """Non-INFO levels and INFO lines carrying a failure marker both surface as
    error lines."""

    def test_non_info_level_flagged(self, tmp_path: Path):
        # an ERROR-level line with no failure marker in the body
        _write_log(
            tmp_path,
            'work-2026-06-01.log',
            [_line('2026-06-01T10:00:00Z', 'ERROR', '[STATUS] (x) something off')],
        )

        result = audit.cross_global_log_analysis(tmp_path)

        assert result['error_count'] == 1
        assert result['error_lines'][0]['level'] == 'ERROR'

    def test_info_line_with_failure_marker_flagged(self, tmp_path: Path):
        # INFO level but the body carries a fail marker (status: error)
        _write_log(
            tmp_path,
            'script-execution-2026-06-01.log',
            [_line('2026-06-01T10:00:00Z', 'INFO', 'pm:x:x run -> status: error exit_code: 1')],
        )

        result = audit.cross_global_log_analysis(tmp_path)

        # an INFO line still counts when a fail marker fires
        assert result['error_count'] == 1
        assert result['error_lines'][0]['level'] == 'INFO'

    def test_clean_info_line_not_flagged(self, tmp_path: Path):
        # INFO with no failure markers
        _write_log(
            tmp_path,
            'work-2026-06-01.log',
            [_line('2026-06-01T10:00:00Z', 'INFO', '[STATUS] (x) all good')],
        )

        result = audit.cross_global_log_analysis(tmp_path)

        assert result['error_count'] == 0


class TestGlobalLogAnalysisPlanAttribution:
    """A flagged line is attributed to every archived/active plan whose execution
    window (from ``metrics.toon`` start/end) contains its timestamp; a line
    outside every window is ad-hoc."""

    def test_in_window_line_attributed_to_plan(self, tmp_path: Path):
        # a plan window enclosing the error line's timestamp
        _write_metrics_window(
            tmp_path, 'plan-alpha', '2026-06-01T10:00:00Z', '2026-06-01T11:00:00Z'
        )
        _write_log(
            tmp_path,
            'work-2026-06-01.log',
            [_line('2026-06-01T10:30:00Z', 'ERROR', '[STATUS] (x) inside window')],
        )

        result = audit.cross_global_log_analysis(tmp_path)

        # the error row names the enclosing plan
        assert result['plan_windows_derived'] == 1
        assert result['error_lines'][0]['plans'] == ['plan-alpha']

    def test_outside_window_line_is_ad_hoc(self, tmp_path: Path):
        # the error timestamp falls OUTSIDE the plan window
        _write_metrics_window(
            tmp_path, 'plan-alpha', '2026-06-01T10:00:00Z', '2026-06-01T11:00:00Z'
        )
        _write_log(
            tmp_path,
            'work-2026-06-01.log',
            [_line('2026-06-01T23:00:00Z', 'ERROR', '[STATUS] (x) after window')],
        )

        result = audit.cross_global_log_analysis(tmp_path)

        # no plan window contains it; attribution is empty (emitted ad-hoc)
        assert result['error_lines'][0]['plans'] == []

    def test_active_plan_window_also_correlated(self, tmp_path: Path):
        # a window seeded under active plans/ (not archived-plans/)
        _write_metrics_window(
            tmp_path,
            'plan-active',
            '2026-06-01T09:00:00Z',
            '2026-06-01T09:30:00Z',
            archived=False,
        )
        _write_log(
            tmp_path,
            'work-2026-06-01.log',
            [_line('2026-06-01T09:15:00Z', 'WARNING', '[STATUS] (x) mid active run')],
        )

        result = audit.cross_global_log_analysis(tmp_path)

        # active-plan windows are correlated alongside archived ones
        assert result['plan_windows_derived'] == 1
        assert result['error_lines'][0]['plans'] == ['plan-active']

    def test_overlapping_windows_attribute_all_enclosing_plans(self, tmp_path: Path):
        # two plans whose windows both contain the timestamp
        _write_metrics_window(
            tmp_path, 'plan-aaa', '2026-06-01T10:00:00Z', '2026-06-01T12:00:00Z'
        )
        _write_metrics_window(
            tmp_path, 'plan-bbb', '2026-06-01T11:00:00Z', '2026-06-01T13:00:00Z'
        )
        _write_log(
            tmp_path,
            'work-2026-06-01.log',
            [_line('2026-06-01T11:30:00Z', 'ERROR', '[STATUS] (x) overlap zone')],
        )

        result = audit.cross_global_log_analysis(tmp_path)

        # both enclosing plans named, sorted
        assert result['error_lines'][0]['plans'] == ['plan-aaa', 'plan-bbb']


class TestGlobalLogAnalysisFixtureLeak:
    """Synthetic test-fixture bundle/plan ids must NEVER appear in the shared
    global log; their presence is a leak (a test wrote to the real logs)."""

    def test_fake_bundle_signature_flagged(self, tmp_path: Path):
        # a synthetic fixture bundle id leaked into the corpus
        _write_log(
            tmp_path,
            'script-execution-2026-06-01.log',
            [_line('2026-06-01T10:00:00Z', 'INFO', 'fake-test-bundle:skill:script run (0.01s)')],
        )

        result = audit.cross_global_log_analysis(tmp_path)

        # leak detector fires and captures the signature
        assert result['fixture_leak_count'] == 1
        assert 'fake-test-bundle' in result['fixture_leaks'][0]['signature']

    def test_idem_and_raising_bundle_signatures_flagged(self, tmp_path: Path):
        # the other two synthetic-bundle signatures from the regex
        _write_log(
            tmp_path,
            'work-2026-06-01.log',
            [
                _line('2026-06-01T10:00:00Z', 'INFO', '[STATUS] idem-bundle wrote a file'),
                _line('2026-06-01T10:00:01Z', 'INFO', '[STATUS] raising-bundle threw'),
            ],
        )

        result = audit.cross_global_log_analysis(tmp_path)

        # both synthetic-bundle leaks captured
        assert result['fixture_leak_count'] == 2

    def test_orphan_md_signature_flagged(self, tmp_path: Path):
        # an orphan-md-* synthetic plan id
        _write_log(
            tmp_path,
            'decision-2026-06-01.log',
            [_line('2026-06-01T10:00:00Z', 'INFO', '(x) plan orphan-md-xyz123 resolved')],
        )

        result = audit.cross_global_log_analysis(tmp_path)

        assert result['fixture_leak_count'] == 1
        assert 'orphan-md-xyz123' in result['fixture_leaks'][0]['signature']

    def test_clean_corpus_has_no_fixture_leaks(self, tmp_path: Path):
        # only real-looking notations, no synthetic signatures
        _write_log(
            tmp_path,
            'script-execution-2026-06-01.log',
            [_line('2026-06-01T10:00:00Z', 'INFO', 'pm:manage-tasks:manage-tasks read (0.01s)')],
        )

        result = audit.cross_global_log_analysis(tmp_path)

        assert result['fixture_leak_count'] == 0
