# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for ``script-failure-analysis.py``.

The script classifies non-zero-exit script calls in
``script-execution.log`` by stderr signature (invented_subcommand,
missing_required_flag, invented_flag, script_internal_error) and emits a
deduped TOON fragment for the retrospective compile-report consumer.
"""


from __future__ import annotations

from _script_failure_analysis_fixtures import (
    _mod,
    _prefix_drifted_work_failure,
    _unprefixed_work_failure,
    _work_failure,
    _work_status,
)


class TestRecognitionGuardIsPrefixIndependent:
    """The guard must survive a drift the PARSER does not survive.

    A guard that shares a leading construct with the pattern it backstops is
    defeated by the same drift, and the sink then reports a clean zero over a
    log that still carries the failure marker — indistinguishable from a log
    with no failures at all, which is precisely the state the guard exists to
    make visible.
    """

    _NOTATION = 'plan-marshall:manage-status:manage-status'
    _DETAIL = "manage-status: error: unrecognized arguments: --field"

    def test_record_prefix_drift_reports_unrecognized_not_clean_zero(self):
        """Reshaping ONLY the record prefix must still register as drift.

        The prefix embeds the exit code as its trailing number, so it is a
        varying value rather than a fixed marker — anchoring the guard on it
        made the guard exactly as fragile as the parser.
        """
        lines = [
            _prefix_drifted_work_failure(
                '01', self._NOTATION, 2, 'argparse_rejection', self._DETAIL
            ),
        ]

        scan = _mod.parse_work_log_failures(lines)

        assert scan.failures == [], 'the drifted line must not parse into a record'
        assert scan.unrecognized_lines == 1, (
            'a record-prefix drift reported a clean zero — the guard is coupled '
            'to the same leading construct as the parser'
        )

    def test_marker_fires_with_no_record_prefix_at_all(self):
        """The guard is anchored on nothing to the LEFT of ``script_failure``."""
        lines = [
            _unprefixed_work_failure(
                '02', self._NOTATION, 2, 'argparse_rejection', self._DETAIL
            ),
        ]

        scan = _mod.parse_work_log_failures(lines)

        assert scan.failures == []
        assert scan.unrecognized_lines == 1

    def test_narrative_mention_of_the_token_is_not_counted_as_drift(self):
        """work.log is a prose sink — a bare token in narrative is not a record.

        Several skills legitimately write ``script_failure`` in prose. A
        bare-token marker would count those lines as drift and manufacture a
        false alarm, trading a silent false negative for a noisy false positive.
        The structural pair is what separates an emitted record from prose.
        """
        lines = [
            _work_status('03', 'triaging the script_failure findings from this run'),
            _work_status(
                '04',
                'every script_failure record carries a notation field and an exit code',
            ),
        ]

        scan = _mod.parse_work_log_failures(lines)

        assert scan.failures == []
        assert scan.unrecognized_lines == 0, (
            'ordinary prose mentioning the token was counted as producer drift'
        )

    def test_intact_producer_line_still_parses_rather_than_counting_as_drift(self):
        """Negative control: the widened guard did not swallow the happy path."""
        lines = [
            _work_failure('05', self._NOTATION, 2, 'argparse_rejection', self._DETAIL),
        ]

        scan = _mod.parse_work_log_failures(lines)

        assert len(scan.failures) == 1
        assert scan.unrecognized_lines == 0


class TestDedupeFindings:
    def test_collapses_recurring_same_subtype(self):
        failures = [
            {
                'notation': 'plan-marshall:manage-tasks:manage-tasks',
                'exit_code': 2,
                'stderr': "invalid choice: 'foo'",
                'timestamp': 't1',
                'subcommand': 'foo',
            },
            {
                'notation': 'plan-marshall:manage-tasks:manage-tasks',
                'exit_code': 2,
                'stderr': "invalid choice: 'bar'",
                'timestamp': 't2',
                'subcommand': 'bar',
            },
        ]
        findings = _mod.dedupe_findings(failures)
        assert len(findings) == 1
        assert findings[0]['occurrence_count'] == 2
        assert findings[0]['subtype'] == 'invented_subcommand'

    def test_distinct_subtypes_kept_separate(self):
        failures = [
            {
                'notation': 'plan-marshall:manage-tasks:manage-tasks',
                'exit_code': 2,
                'stderr': "invalid choice: 'foo'",
                'timestamp': 't1',
                'subcommand': 'foo',
            },
            {
                'notation': 'plan-marshall:manage-tasks:manage-tasks',
                'exit_code': 2,
                'stderr': 'unrecognized arguments: --nope',
                'timestamp': 't2',
                'subcommand': 'add',
            },
        ]
        findings = _mod.dedupe_findings(failures)
        assert len(findings) == 2
        subtypes = {f['subtype'] for f in findings}
        assert subtypes == {'invented_subcommand', 'invented_flag'}


class TestDedupeMirroredFailures:
    """``dedupe_mirrored_failures`` drops work.log entries that mirror an
    script-execution.log entry on ``(notation, timestamp)`` so a single physical
    failure mirrored to both sinks is counted exactly once.
    """

    def test_drops_mirrored_work_failure(self):
        exec_failures = [
            {
                'notation': 'plan-marshall:manage-status:manage-status',
                'timestamp': '2026-05-26T10:00:01Z',
                'exit_code': 2,
                'stderr': 'unrecognized arguments: --field',
            },
        ]
        work_failures = [
            {
                'notation': 'plan-marshall:manage-status:manage-status',
                'timestamp': '2026-05-26T10:00:01Z',
                'exit_code': 2,
                'stderr': 'unrecognized arguments: --field',
            },
        ]
        # The mirrored work.log entry is dropped → empty residual.
        assert _mod.dedupe_mirrored_failures(exec_failures, work_failures) == []

    def test_retains_work_only_failure(self):
        # A work.log failure with no matching script-execution.log entry (the
        # originating-context gap) is retained.
        exec_failures = [
            {
                'notation': 'plan-marshall:manage-files:manage-files',
                'timestamp': '2026-05-26T10:00:01Z',
                'exit_code': 1,
                'stderr': 'boom',
            },
        ]
        work_failures = [
            {
                'notation': 'plan-marshall:manage-status:manage-status',
                'timestamp': '2026-05-26T11:00:30Z',
                'exit_code': 2,
                'stderr': 'unrecognized arguments: --field',
            },
        ]
        residual = _mod.dedupe_mirrored_failures(exec_failures, work_failures)
        assert len(residual) == 1
        assert residual[0]['notation'] == 'plan-marshall:manage-status:manage-status'

    def test_distinguishes_same_notation_different_timestamp(self):
        # Same notation but a DIFFERENT timestamp is a distinct physical event
        # and must be retained.
        exec_failures = [
            {
                'notation': 'plan-marshall:manage-tasks:manage-tasks',
                'timestamp': '2026-05-26T10:00:01Z',
                'exit_code': 2,
                'stderr': "invalid choice: 'foo'",
            },
        ]
        work_failures = [
            {
                'notation': 'plan-marshall:manage-tasks:manage-tasks',
                'timestamp': '2026-05-26T10:00:09Z',
                'exit_code': 2,
                'stderr': "invalid choice: 'bar'",
            },
        ]
        residual = _mod.dedupe_mirrored_failures(exec_failures, work_failures)
        assert len(residual) == 1
        assert residual[0]['timestamp'] == '2026-05-26T10:00:09Z'
