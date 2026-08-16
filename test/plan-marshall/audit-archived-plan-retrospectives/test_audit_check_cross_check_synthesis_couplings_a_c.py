#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""``cross-check-synthesis`` couplings (a)-(c) and the flagged-plans helper —
``trend_empty_untrustworthy``, ``churn_explains_walltime``, and
``qgate_gap_chain``.
"""

from _audit_fixtures import (
    _coupling_row,
    _flag_result,
    audit,
)


class TestCrossCheckSynthesisFlaggedPlansHelper:
    """``_syn_flagged_plans`` collects plan ids whose flags match a predicate;
    ``_syn_build_walltime_outlier_plans`` collects the build-wall-clock upper half."""

    def test_matching_flag_collected(self):
        # two plans, only one carries a build_churn flag
        result = _flag_result(
            [
                {'plan_id': 'p-churn', 'flags': ['build_churn:3']},
                {'plan_id': 'p-clean', 'flags': []},
            ]
        )

        matched = audit._syn_flagged_plans(
            result, lambda f: f.startswith('build_churn')
        )

        # only the churning plan is collected
        assert matched == {'p-churn'}

    def test_malformed_result_yields_empty_set(self):
        # a non-dict result is best-effort tolerated
        matched = audit._syn_flagged_plans(None, lambda f: True)

        # empty set, no raise
        assert matched == set()

    def test_build_walltime_outlier_plans_collected(self):
        # three build-running plans; the upper half (>= median total_build_seconds)
        result = _flag_result(
            [
                {'plan_id': 'p-hi', 'flags': [], 'total_build_seconds': 900},
                {'plan_id': 'p-mid', 'flags': [], 'total_build_seconds': 450},
                {'plan_id': 'p-lo', 'flags': [], 'total_build_seconds': 50},
            ]
        )

        plans = audit._syn_build_walltime_outlier_plans(result)

        # median of [50,450,900] = 450; plans >= 450 are the outliers
        assert plans == {'p-hi', 'p-mid'}

    def test_build_walltime_excludes_zero_build_plans(self):
        # a plan that ran no builds (0 seconds) cannot be a wall-clock outlier
        result = _flag_result(
            [
                {'plan_id': 'p-build', 'flags': [], 'total_build_seconds': 300},
                {'plan_id': 'p-nobuild', 'flags': [], 'total_build_seconds': 0},
            ]
        )

        plans = audit._syn_build_walltime_outlier_plans(result)

        # only the build-running plan; the zero-build plan is excluded entirely
        assert plans == {'p-build'}

    def test_build_walltime_non_dict_yields_empty_set(self):
        # best-effort on a non-dict input
        assert audit._syn_build_walltime_outlier_plans(None) == set()


class TestCrossCheckSynthesisCouplingA:
    """Coupling (a) trend_empty_untrustworthy: empty token-trend regression
    co-occurring with at least one blind-execute plan (input-integrity)."""

    def test_fires_on_empty_trend_with_blind_plan(self):
        # regression empty AND a blind input-integrity plan
        all_results = {
            'token-efficiency-trend': {'regression': ''},
            'input-integrity': [
                {'plan_id': 'p-blind', 'data_confidence': 'blind'},
            ],
        }

        result = audit.cross_check_synthesis(all_results)
        row = _coupling_row(result, 'trend_empty_untrustworthy')

        # fired, detail names the blind plan
        assert row['fired'] is True
        assert 'p-blind' in row['detail']

    def test_does_not_fire_when_regression_present(self):
        # a non-empty regression means the trend IS trustworthy
        all_results = {
            'token-efficiency-trend': {'regression': '12% rise'},
            'input-integrity': [
                {'plan_id': 'p-blind', 'data_confidence': 'blind'},
            ],
        }

        result = audit.cross_check_synthesis(all_results)
        row = _coupling_row(result, 'trend_empty_untrustworthy')

        # not fired
        assert row['fired'] is False

    def test_does_not_fire_without_blind_plan(self):
        # empty regression but no blind-execute plan
        all_results = {
            'token-efficiency-trend': {'regression': ''},
            'input-integrity': [
                {'plan_id': 'p-ok', 'data_confidence': 'fully_recorded'},
            ],
        }

        result = audit.cross_check_synthesis(all_results)
        row = _coupling_row(result, 'trend_empty_untrustworthy')

        # not fired
        assert row['fired'] is False


class TestCrossCheckSynthesisCouplingB:
    """Coupling (b) churn_explains_walltime: a plan flagged non_minimal_build /
    build_churn whose build WALL-CLOCK (total_build_seconds) is in the corpus upper
    half. It correlates churn against wall-clock — NOT against token metrics, which
    cannot see build cost (cache_read/cache_creation are excluded from total_tokens)."""

    def test_fires_on_churn_with_high_walltime(self):
        # a churning plan whose build wall-clock is at/above the corpus median
        all_results = {
            'sequence-and-build-minimality': _flag_result(
                [
                    {'plan_id': 'p-hi', 'flags': ['non_minimal_build:2'], 'total_build_seconds': 800},
                    {'plan_id': 'p-lo', 'flags': ['build_churn:3'], 'total_build_seconds': 100},
                ]
            ),
        }

        result = audit.cross_check_synthesis(all_results)
        row = _coupling_row(result, 'churn_explains_walltime')

        # median of [100,800]=450; only p-hi (800>=450) is both churning AND upper-half
        assert row['fired'] is True
        assert 'p-hi' in row['detail']
        assert 'p-lo' not in row['detail']

    def test_fires_on_build_churn_flag_specifically(self):
        # the build_churn flag (not just non_minimal_build) also qualifies
        all_results = {
            'sequence-and-build-minimality': _flag_result(
                [
                    {'plan_id': 'p-churn', 'flags': ['build_churn:6'], 'total_build_seconds': 600},
                    {'plan_id': 'p-clean', 'flags': [], 'total_build_seconds': 200},
                ]
            ),
        }

        result = audit.cross_check_synthesis(all_results)
        row = _coupling_row(result, 'churn_explains_walltime')

        # median [200,600]=400; p-churn (600>=400) churns AND is upper-half
        assert row['fired'] is True
        assert 'p-churn' in row['detail']

    def test_does_not_fire_when_churn_has_low_walltime(self):
        # churn on a plan whose build wall-clock is BELOW the corpus median
        all_results = {
            'sequence-and-build-minimality': _flag_result(
                [
                    {'plan_id': 'p-churn-lo', 'flags': ['build_churn:5'], 'total_build_seconds': 50},
                    {'plan_id': 'p-clean-hi', 'flags': [], 'total_build_seconds': 900},
                ]
            ),
        }

        result = audit.cross_check_synthesis(all_results)
        row = _coupling_row(result, 'churn_explains_walltime')

        # median [50,900]=475; the only upper-half plan (p-clean-hi) does not churn
        assert row['fired'] is False


class TestCrossCheckSynthesisCouplingC:
    """Coupling (c) qgate_gap_chain: a plan flagged no_qgate6 / auto_review_only
    (quality-chain) AND (ci_rerun (sequence) OR finalize_heavy (economics))."""

    def test_fires_on_qgate_gap_plus_ci_rerun(self):
        # qgate gap intersects with a ci_rerun flag
        all_results = {
            'quality-chain': _flag_result(
                [{'plan_id': 'p-z', 'flags': ['no_qgate6']}]
            ),
            'sequence-and-build-minimality': _flag_result(
                [{'plan_id': 'p-z', 'flags': ['ci_rerun:2']}]
            ),
            'token-economics': _flag_result([]),
        }

        result = audit.cross_check_synthesis(all_results)
        row = _coupling_row(result, 'qgate_gap_chain')

        # fired via the ci_rerun arm
        assert row['fired'] is True
        assert 'p-z' in row['detail']

    def test_fires_on_qgate_gap_plus_finalize_heavy(self):
        # auto_review_only intersects with finalize_heavy
        all_results = {
            'quality-chain': _flag_result(
                [{'plan_id': 'p-w', 'flags': ['auto_review_only']}]
            ),
            'sequence-and-build-minimality': _flag_result([]),
            'token-economics': _flag_result(
                [{'plan_id': 'p-w', 'flags': ['finalize_heavy']}]
            ),
        }

        result = audit.cross_check_synthesis(all_results)
        row = _coupling_row(result, 'qgate_gap_chain')

        # fired via the finalize_heavy arm
        assert row['fired'] is True
        assert 'p-w' in row['detail']

    def test_does_not_fire_without_downstream_signal(self):
        # qgate gap present but no ci_rerun / finalize_heavy anywhere
        all_results = {
            'quality-chain': _flag_result(
                [{'plan_id': 'p-q', 'flags': ['no_qgate6']}]
            ),
            'sequence-and-build-minimality': _flag_result([]),
            'token-economics': _flag_result([]),
        }

        result = audit.cross_check_synthesis(all_results)
        row = _coupling_row(result, 'qgate_gap_chain')

        # no downstream cost signal => not fired
        assert row['fired'] is False
