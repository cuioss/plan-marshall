#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Retrospective-token exclusion across the metrics-related checks — a retrospective
phase's tokens are excluded from the disproportionate-spend, optimization,
trend, and degrade verdicts.
"""

from _audit_fixtures import (
    _inputs,
    _phase,
    audit,
)


class TestRetrospectiveExclusionDisproportionate:
    def test_retrospective_does_not_trip_share_threshold(self, monkeypatch):
        # finalize raw total dominates (2000 of 2800 = 71%, which would
        # trip the 45% threshold on raw tokens), but the bulk is retrospective.
        # The two implementation phases carry balanced effective shares so that no
        # phase trips the threshold once retrospective spend is excluded.
        phases = [
            _phase('5-execute', total_tokens=400),
            _phase('3-outline', total_tokens=400),
            _phase('6-finalize', total_tokens=2000, retrospective_tokens=1800),
        ]
        monkeypatch.setattr(audit, 'parse_metrics_toon', lambda _p: phases)
        inputs = _inputs([])

        result = audit.check_metrics(inputs)

        # effective total 1000 (400 + 400 + 200); shares 40%/40%/20%,
        # none >= 45%, so nothing is flagged. Without exclusion, finalize's raw
        # 2000/2800 = 71% would have tripped the threshold.
        assert result['disproportionate_token'] == ''

    def test_negative_control_genuine_disproportionate_still_flagged(self, monkeypatch):
        # a genuine >=45% phase even after retrospective exclusion
        phases = [
            _phase('5-execute', total_tokens=300),
            _phase('3-outline', total_tokens=700),
            _phase('6-finalize', total_tokens=200, retrospective_tokens=100),
        ]
        monkeypatch.setattr(audit, 'parse_metrics_toon', lambda _p: phases)
        inputs = _inputs([])

        result = audit.check_metrics(inputs)

        # effective total 1100, outline 700/1100 = 63% → flagged
        assert '3-outline' in result['disproportionate_token']


class TestRetrospectiveExclusionOptimization:
    def test_retrospective_only_outlier_not_flagged(self, monkeypatch):
        # three balanced phases plus a finalize whose only spend is
        # retrospective (effective 0 → excluded from the ratio set).
        phases = [
            _phase('2-refine', total_tokens=1000, duration_seconds=100.0),
            _phase('4-plan', total_tokens=1100, duration_seconds=110.0),
            _phase('5-execute', total_tokens=900, duration_seconds=90.0),
            _phase(
                '6-finalize',
                total_tokens=9000,
                retrospective_tokens=9000,
                duration_seconds=10.0,
            ),
        ]
        monkeypatch.setattr(audit, 'parse_metrics_toon', lambda _p: phases)
        inputs = _inputs([])

        result = audit.check_metrics(inputs)

        # the finalize phase (raw 900 tok/s outlier) is excluded
        assert '6-finalize' not in result['optimization_signal']
        assert result['optimization_signal'] == ''


class TestRetrospectiveExclusionTrend:
    def test_total_and_divisor_exclude_retrospective(self, monkeypatch):
        # one plan whose finalize spend is entirely retrospective
        phases = [
            _phase('5-execute', total_tokens=500),
            _phase('6-finalize', total_tokens=400, retrospective_tokens=400),
        ]
        monkeypatch.setattr(audit, 'parse_metrics_toon', lambda _p: phases)
        inputs = _inputs([])

        result = audit.cross_token_trend([inputs])

        # effective total 500, only one implementation phase counted
        row = result['rows'][0]
        assert row['total_tokens'] == 500
        assert row['phases'] == 1
        assert row['tokens_per_phase'] == 500


class TestRetrospectiveExclusionDegrade:
    def test_absent_attribution_excludes_nothing(self, monkeypatch):
        # archived-plan shape: NO retrospective_tokens field anywhere
        phases = [
            _phase('5-execute', total_tokens=1000, duration_seconds=100.0),
            _phase('6-finalize', total_tokens=2000, duration_seconds=50.0),
        ]
        monkeypatch.setattr(audit, 'parse_metrics_toon', lambda _p: phases)
        inputs = _inputs([])

        metrics = audit.check_metrics(inputs)
        trend = audit.cross_token_trend([inputs])

        # behaves exactly as pre-D8 (2000/3000 = 67% finalize flagged)
        assert '6-finalize' in metrics['disproportionate_token']
        assert trend['rows'][0]['total_tokens'] == 3000
        assert trend['rows'][0]['phases'] == 2

    def test_only_retrospective_excluded_other_op_spend_counted(self, monkeypatch):
        # a finalize phase carrying q-gate-validation / other-op spend
        # (no retrospective_tokens) stays fully counted.
        phases = [
            _phase('5-execute', total_tokens=400),
            _phase('6-finalize', total_tokens=600),
        ]
        monkeypatch.setattr(audit, 'parse_metrics_toon', lambda _p: phases)
        inputs = _inputs([])

        result = audit.check_metrics(inputs)

        # effective total 1000, finalize 600/1000 = 60% → flagged
        assert '6-finalize' in result['disproportionate_token']
