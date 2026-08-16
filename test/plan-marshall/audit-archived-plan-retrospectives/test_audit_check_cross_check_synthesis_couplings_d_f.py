#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""``cross-check-synthesis`` couplings (d)-(f) — ``argparse_signature_cluster``,
``scope_underestimate_cost``, and ``redundant_build_churn``.
"""

from _audit_fixtures import (
    _coupling_row,
    _flag_result,
    audit,
)


class TestCrossCheckSynthesisCouplingD:
    """Coupling (d) argparse_signature_cluster: argparse-shaped recurring
    signatures AND global-log errors AND unfiled quality-verification
    signatures — collapse-to-ONE source-keyed candidate."""

    def test_fires_when_all_three_facets_present(self):
        # an argparse signature, a global-log error, an unfiled lesson
        all_results = {
            'recurring-pattern-detector': {
                'rows': [{'signature': 'argparse: invalid choice foo'}]
            },
            'global-log-analysis': {'error_count': 3},
            'quality-verification-report': [{'unfiled_lessons': 1}],
        }

        result = audit.cross_check_synthesis(all_results)
        row = _coupling_row(result, 'argparse_signature_cluster')

        # fired, caveat names the single-source collapse
        assert row['fired'] is True
        assert 'collapse to ONE' in row['detail']

    def test_does_not_fire_without_global_errors(self):
        # argparse signature + unfiled lesson but ZERO global errors
        all_results = {
            'recurring-pattern-detector': {
                'rows': [{'signature': 'argparse: unrecognized argument'}]
            },
            'global-log-analysis': {'error_count': 0},
            'quality-verification-report': [{'unfiled_lessons': 2}],
        }

        result = audit.cross_check_synthesis(all_results)
        row = _coupling_row(result, 'argparse_signature_cluster')

        # missing one of the three facets => not fired
        assert row['fired'] is False

    def test_does_not_fire_when_signature_not_argparse_shaped(self):
        # a non-argparse signature does not match _SYN_ARGPARSE_SIG_RE
        all_results = {
            'recurring-pattern-detector': {
                'rows': [{'signature': 'flaky network timeout'}]
            },
            'global-log-analysis': {'error_count': 5},
            'quality-verification-report': [{'unfiled_lessons': 1}],
        }

        result = audit.cross_check_synthesis(all_results)
        row = _coupling_row(result, 'argparse_signature_cluster')

        # no argparse-shaped signature => not fired
        assert row['fired'] is False


class TestCrossCheckSynthesisCouplingE:
    """Coupling (e) scope_underestimate_cost: a scope-estimate mismatch AND
    (high tokens/file >= corpus median OR a task-count outlier)."""

    def test_fires_on_scope_mismatch_plus_high_tpf(self):
        # p-hi mismatches scope AND sits at/above the tpf median
        all_results = {
            'scope-estimate-accuracy': [
                {'plan_id': 'p-hi', 'mismatch': True},
            ],
            'token-economics': _flag_result(
                [
                    {'plan_id': 'p-hi', 'flags': [], 'tokens_per_file': 9000},
                    {'plan_id': 'p-lo', 'flags': [], 'tokens_per_file': 1000},
                ]
            ),
            'task-count-efficiency': [],
        }

        result = audit.cross_check_synthesis(all_results)
        row = _coupling_row(result, 'scope_underestimate_cost')

        # fired via the high-tokens/file arm
        assert row['fired'] is True
        assert 'p-hi' in row['detail']

    def test_fires_on_scope_mismatch_plus_task_outlier(self):
        # mismatch intersects with a task-count outlier
        all_results = {
            'scope-estimate-accuracy': [
                {'plan_id': 'p-out', 'mismatch': True},
            ],
            'token-economics': _flag_result([]),
            'task-count-efficiency': [
                {'plan_id': 'p-out', 'outlier': True},
            ],
        }

        result = audit.cross_check_synthesis(all_results)
        row = _coupling_row(result, 'scope_underestimate_cost')

        # fired via the task-outlier arm
        assert row['fired'] is True
        assert 'p-out' in row['detail']

    def test_does_not_fire_without_cost_signal(self):
        # scope mismatch but median guard suppresses tpf, no outlier
        all_results = {
            'scope-estimate-accuracy': [
                {'plan_id': 'p-m', 'mismatch': True},
            ],
            'token-economics': _flag_result([]),
            'task-count-efficiency': [],
        }

        result = audit.cross_check_synthesis(all_results)
        row = _coupling_row(result, 'scope_underestimate_cost')

        # no cost signal => not fired
        assert row['fired'] is False


class TestCrossCheckSynthesisCouplingF:
    """Coupling (f) redundant_build_churn: a plan whose task graph carries an
    in_task_build AND whose sequence was flagged build_churn / phase_reentry."""

    def test_fires_on_in_task_build_plus_build_churn(self):
        # same plan flagged in_task_build AND build_churn
        all_results = {
            'task-graph-redundancy': [
                {'plan_id': 'p-x', 'in_task_build': 'T2:module-tests'},
            ],
            'sequence-and-build-minimality': _flag_result(
                [{'plan_id': 'p-x', 'flags': ['build_churn:3']}]
            ),
        }

        result = audit.cross_check_synthesis(all_results)
        row = _coupling_row(result, 'redundant_build_churn')

        # fired, naming the plan
        assert row['fired'] is True
        assert 'p-x' in row['detail']

    def test_fires_on_in_task_build_plus_phase_reentry(self):
        # in_task_build AND phase_reentry on the same plan
        all_results = {
            'task-graph-redundancy': [
                {'plan_id': 'p-y', 'in_task_build': 'T1:quality-gate'},
            ],
            'sequence-and-build-minimality': _flag_result(
                [{'plan_id': 'p-y', 'flags': ['phase_reentry:5-execute']}]
            ),
        }

        result = audit.cross_check_synthesis(all_results)
        row = _coupling_row(result, 'redundant_build_churn')

        # fired
        assert row['fired'] is True

    def test_does_not_fire_when_signals_disjoint(self):
        # in_task_build on one plan, churn on a DIFFERENT plan
        all_results = {
            'task-graph-redundancy': [
                {'plan_id': 'p-a', 'in_task_build': 'T2:module-tests'},
            ],
            'sequence-and-build-minimality': _flag_result(
                [{'plan_id': 'p-b', 'flags': ['build_churn:3']}]
            ),
        }

        result = audit.cross_check_synthesis(all_results)
        row = _coupling_row(result, 'redundant_build_churn')

        # not fired (no plan carries both)
        assert row['fired'] is False

    def test_does_not_fire_without_in_task_build(self):
        # churn present but no in_task_build anywhere
        all_results = {
            'task-graph-redundancy': [
                {'plan_id': 'p-c', 'in_task_build': ''},
            ],
            'sequence-and-build-minimality': _flag_result(
                [{'plan_id': 'p-c', 'flags': ['build_churn:3']}]
            ),
        }

        result = audit.cross_check_synthesis(all_results)
        row = _coupling_row(result, 'redundant_build_churn')

        # not fired
        assert row['fired'] is False
