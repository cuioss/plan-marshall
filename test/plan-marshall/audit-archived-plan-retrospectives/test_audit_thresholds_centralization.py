#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""``THRESHOLDS`` centralization — every threshold resolves from the single source
table, back-compat aliases keep resolving, and the corpus-relative helpers derive
percentile and median values from the corpus rather than from constants.
"""

from _audit_fixtures import audit


class TestThresholdsCentralization:
    """The ``THRESHOLDS`` table is the single source of truth and every
    back-compatible module-level alias resolves to the same value it owns."""

    def test_systemic_threshold_alias_matches_table(self):
        # the request-mandated 3+ occurrences
        assert audit.SYSTEMIC_THRESHOLD == audit.THRESHOLDS['systemic_occurrences']
        assert audit.SYSTEMIC_THRESHOLD == 3

    def test_pr_slow_review_alias_matches_table(self):
        assert audit.PR_SLOW_REVIEW_HOURS == audit.THRESHOLDS['pr_slow_review_hours']

    def test_phase_token_share_alias_matches_table(self):
        assert (
            audit.PHASE_TOKEN_SHARE_THRESHOLD
            == audit.THRESHOLDS['phase_token_share']
        )

    def test_scope_file_bands_alias_matches_table(self):
        # alias is the same mapping object the table owns
        assert audit.SCOPE_FILE_BANDS == audit.THRESHOLDS['scope_file_bands']
        assert audit.SCOPE_FILE_BANDS['surgical'] == (1, 3)
        assert audit.SCOPE_FILE_BANDS['multi_module'] == (5, None)

    def test_tasks_per_deliverable_aliases_match_table(self):
        assert (
            audit.TASKS_PER_DELIVERABLE_LOW
            == audit.THRESHOLDS['tasks_per_deliverable_low']
        )
        assert (
            audit.TASKS_PER_DELIVERABLE_HIGH
            == audit.THRESHOLDS['tasks_per_deliverable_high']
        )

    def test_thresholds_table_carries_every_documented_constant(self):
        # every magic number the checks consume must live in the table
        expected_keys = {
            'systemic_occurrences',
            'preference_disposition_occurrences',
            'pr_slow_review_hours',
            'phase_token_share',
            'token_rate_outlier_multiple',
            'token_trend_regression_fraction',
            'build_minimal_seconds',
            'build_heavy_seconds',
            'build_clustering_minutes',
            'long_session_messages',
            'slow_call_seconds',
            'high_frequency_calls',
            'scope_file_bands',
            'tasks_per_deliverable_low',
            'tasks_per_deliverable_high',
        }

        # table is a superset of the documented constants
        assert expected_keys <= set(audit.THRESHOLDS)


class TestCorpusRelativeHelpers:
    """``median`` / ``percentile`` are the corpus-relative threshold helpers a
    check SHOULD prefer over a hard-coded constant when a live distribution
    exists."""

    def test_median_empty_returns_zero(self):
        assert audit.median([]) == 0.0

    def test_median_odd_length_returns_middle(self):
        # unsorted input is sorted internally
        assert audit.median([3.0, 1.0, 2.0]) == 2.0

    def test_median_even_length_averages_two_middle(self):
        assert audit.median([1.0, 2.0, 3.0, 4.0]) == 2.5

    def test_percentile_empty_returns_zero(self):
        assert audit.percentile([], 50.0) == 0.0

    def test_percentile_nearest_rank_is_deterministic(self):
        # nearest-rank: rank = round(pct/100 * n), floored at 1
        values = [10.0, 20.0, 30.0, 40.0]

        assert audit.percentile(values, 0.0) == 10.0
        assert audit.percentile(values, 100.0) == 40.0
        assert audit.percentile(values, 50.0) == 20.0

    def test_percentile_clamps_out_of_range_pct(self):
        values = [5.0, 15.0, 25.0]

        # pct outside [0,100] is clamped, never raises
        assert audit.percentile(values, -10.0) == 5.0
        assert audit.percentile(values, 250.0) == 25.0
