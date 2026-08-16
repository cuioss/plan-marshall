#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The persisted report sink — path-guarding on write, the load/diff round-trip, the
summary-metric diff, and metric coercion.
"""

from pathlib import Path

from _audit_fixtures import audit


class TestPersistedReportSink:
    """``write_persisted_report`` writes only under ``audit-reports/`` and the
    round-trip ``load_latest_prior_report`` reads back the summary metrics it
    persisted."""

    def test_write_creates_report_under_audit_reports(self, tmp_path: Path):
        blocks = ['check: metrics\nstatus: success\n']
        summary = {'plans_scanned': 2, 'metrics_genuine': 1}

        dest = audit.write_persisted_report(tmp_path, blocks, summary)

        # landed under the guarded directory with the timestamp grammar
        assert dest is not None
        reports_dir = (tmp_path / audit.AUDIT_REPORTS_REL).resolve()
        assert dest.parent == reports_dir
        assert audit._REPORT_STEM_RE.match(dest.stem)
        assert dest.is_file()

    def test_written_report_carries_summary_metrics_header(self, tmp_path: Path):
        summary = {'plans_scanned': 3, 'foo': 'bar'}

        dest = audit.write_persisted_report(tmp_path, ['check: x\n'], summary)
        assert dest is not None
        text = dest.read_text(encoding='utf-8')

        # header block + keys (sorted) + the run's block text
        assert 'report: audit' in text
        assert 'summary_metrics:' in text
        assert 'plans_scanned: 3' in text
        assert 'foo: bar' in text
        assert 'check: x' in text

    def test_load_latest_prior_round_trips_summary_metrics(self, tmp_path: Path):
        # write a report, then read its summary back
        summary = {'plans_scanned': 5, 'metrics_genuine': 2, 'regression': True}
        audit.write_persisted_report(tmp_path, ['check: m\n'], summary)

        loaded = audit.load_latest_prior_report(tmp_path)

        # int + bool coercion round-trips through _coerce_metric
        assert loaded is not None
        assert loaded['plans_scanned'] == 5
        assert loaded['metrics_genuine'] == 2
        assert loaded['regression'] is True

    def test_load_latest_prior_returns_none_when_no_reports(self, tmp_path: Path):
        # no audit-reports directory at all
        loaded = audit.load_latest_prior_report(tmp_path)

        assert loaded is None

    def test_load_latest_prior_ignores_non_timestamp_files(self, tmp_path: Path):
        # a stray non-grammar file must not be picked as "latest"
        reports_dir = (tmp_path / audit.AUDIT_REPORTS_REL).resolve()
        reports_dir.mkdir(parents=True)
        (reports_dir / 'not-a-report.toon').write_text('garbage\n', encoding='utf-8')

        loaded = audit.load_latest_prior_report(tmp_path)

        # no valid timestamp-stem report exists
        assert loaded is None

    def test_latest_is_lexicographically_greatest_stem(self, tmp_path: Path):
        # two valid reports; the greater stem is "latest prior"
        reports_dir = (tmp_path / audit.AUDIT_REPORTS_REL).resolve()
        reports_dir.mkdir(parents=True)
        older = reports_dir / '20260101T000000Z.toon'
        newer = reports_dir / '20260601T120000Z.toon'
        older.write_text(
            'report: audit\nsummary_metrics:\n  plans_scanned: 1\n', encoding='utf-8'
        )
        newer.write_text(
            'report: audit\nsummary_metrics:\n  plans_scanned: 9\n', encoding='utf-8'
        )

        loaded = audit.load_latest_prior_report(tmp_path)

        # the newer (greater stem) summary is returned
        assert loaded is not None
        assert loaded['plans_scanned'] == 9


class TestDiffSummaryMetrics:
    """``diff_summary_metrics`` reports every changed metric, sorted, with empty
    strings filling a side where a key is absent."""

    def test_changed_keys_reported_sorted(self):
        prior = {'a': 1, 'b': 2, 'c': 3}
        current = {'a': 1, 'b': 99, 'c': 3}

        changes = audit.diff_summary_metrics(prior, current)

        # only b changed
        assert changes == [('b', 2, 99)]

    def test_added_key_reports_empty_prior_side(self):
        # key only in current
        changes = audit.diff_summary_metrics({}, {'new_metric': 7})

        assert changes == [('new_metric', '', 7)]

    def test_removed_key_reports_empty_current_side(self):
        # key only in prior
        changes = audit.diff_summary_metrics({'gone': 4}, {})

        assert changes == [('gone', 4, '')]

    def test_no_changes_yields_empty_list(self):
        assert audit.diff_summary_metrics({'a': 1}, {'a': 1}) == []

    def test_full_round_trip_write_load_diff(self, tmp_path: Path):
        # write a prior report, then diff a current summary against it
        prior_summary = {'plans_scanned': 4, 'metrics_genuine': 1}
        audit.write_persisted_report(tmp_path, ['check: p\n'], prior_summary)
        prior = audit.load_latest_prior_report(tmp_path)
        assert prior is not None
        current_summary = {'plans_scanned': 4, 'metrics_genuine': 3}

        changes = audit.diff_summary_metrics(prior, current_summary)

        # only metrics_genuine moved 1 -> 3
        assert changes == [('metrics_genuine', 1, 3)]


class TestCoerceMetric:
    """``_coerce_metric`` reconstructs bool / int / str types when reading a
    persisted report's summary header back from text."""

    def test_bool_strings_coerce_to_bool(self):
        assert audit._coerce_metric('True') is True
        assert audit._coerce_metric('False') is False

    def test_int_string_coerces_to_int(self):
        assert audit._coerce_metric('42') == 42
        assert isinstance(audit._coerce_metric('42'), int)

    def test_non_numeric_string_stays_string(self):
        assert audit._coerce_metric('plan-abc') == 'plan-abc'
