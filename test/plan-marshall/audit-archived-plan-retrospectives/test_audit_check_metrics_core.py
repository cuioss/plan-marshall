#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""``check_metrics`` positive path — the core flagging logic and the end-time marker
states a plan's metrics can be in.
"""

from _audit_fixtures import (
    _inputs,
    _phase,
    audit,
)


class TestMetricsCoreFlags:
    """``check_metrics`` flags disproportionate token share, incomplete (zero-token)
    phase recordings, impossible durations, and token-rate optimization outliers."""

    def test_no_metrics_reports_incomplete(self, monkeypatch):
        # no phases parsed at all.
        monkeypatch.setattr(audit, 'parse_metrics_toon', lambda _p: [])
        inputs = _inputs([])

        result = audit.check_metrics(inputs)

        # the empty-metrics sentinel row
        assert result['phases_recorded'] == 0
        assert result['incomplete_recording'] == 'true'
        assert result['anomalies'] == ['no metrics.toon recorded']

    def test_disproportionate_share_flagged(self, monkeypatch):
        # outline consumes 600/1000 = 60% (>= 45% threshold).
        phases = [
            _phase('3-outline', total_tokens=600),
            _phase('5-execute', total_tokens=400),
        ]
        monkeypatch.setattr(audit, 'parse_metrics_toon', lambda _p: phases)
        inputs = _inputs([])

        result = audit.check_metrics(inputs)

        assert result['disproportionate_token'] == '3-outline=60%'
        assert any('3-outline' in a for a in result['anomalies'])

    def test_zero_token_phase_flagged_incomplete(self, monkeypatch):
        # a recorded phase carrying zero tokens.
        phases = [
            _phase('5-execute', total_tokens=500),
            _phase('6-finalize', total_tokens=0),
        ]
        monkeypatch.setattr(audit, 'parse_metrics_toon', lambda _p: phases)
        inputs = _inputs([])

        result = audit.check_metrics(inputs)

        # the zero-token phase name lands in incomplete_recording
        assert result['incomplete_recording'] == '6-finalize'

    def test_worked_exceeding_wall_is_impossible(self, monkeypatch):
        # agent worked 200s but wall-clock is only 100s.
        phases = [
            _phase(
                '5-execute',
                total_tokens=500,
                duration_seconds=100.0,
                agent_duration_seconds=200.0,
            ),
        ]
        monkeypatch.setattr(audit, 'parse_metrics_toon', lambda _p: phases)
        inputs = _inputs([])

        result = audit.check_metrics(inputs)

        # worked > wall flagged as impossible
        assert result['impossible_value'] == '5-execute:worked>100s'

    def test_negative_idle_is_impossible(self, monkeypatch):
        # a phase with a negative idle duration.
        phases = [
            _phase('5-execute', total_tokens=500, idle_duration_ms=-5.0),
        ]
        monkeypatch.setattr(audit, 'parse_metrics_toon', lambda _p: phases)
        inputs = _inputs([])

        result = audit.check_metrics(inputs)

        assert result['impossible_value'] == '5-execute:negative_idle'

    def test_token_rate_outlier_flagged(self, monkeypatch):
        # three baseline phases at ~10 tok/s plus one outlier at 100
        # tok/s (>= 3x the median non-zero ratio).
        phases = [
            _phase('2-refine', total_tokens=1000, duration_seconds=100.0),
            _phase('3-outline', total_tokens=1000, duration_seconds=100.0),
            _phase('4-plan', total_tokens=1000, duration_seconds=100.0),
            _phase('5-execute', total_tokens=1000, duration_seconds=10.0),
        ]
        monkeypatch.setattr(audit, 'parse_metrics_toon', lambda _p: phases)
        inputs = _inputs([])

        result = audit.check_metrics(inputs)

        # 5-execute (100 tok/s) is the >= 3x median outlier
        assert result['optimization_signal'].startswith('5-execute:')

    def test_balanced_phases_flag_nothing(self, monkeypatch):
        # three balanced phases, all non-zero, similar rates.
        phases = [
            _phase('3-outline', total_tokens=300, duration_seconds=30.0),
            _phase('4-plan', total_tokens=350, duration_seconds=35.0),
            _phase('5-execute', total_tokens=350, duration_seconds=35.0),
        ]
        monkeypatch.setattr(audit, 'parse_metrics_toon', lambda _p: phases)
        # The fixture's plan dir carries no metrics.toon at all, which would read
        # as `pre-#812` and append the unreadable-marker note. Isolate the anomaly
        # logic under test by supplying a READABLE marker record with nothing to
        # explain — the unreadable states get their own tests below.
        monkeypatch.setattr(
            audit,
            'parse_metrics_end_time_presence',
            lambda _p: audit.MetricsEndTimePresence(
                schema=audit.METRICS_SCHEMA_CURRENT,
                any_phase_missing_end_time=False,
                phases_missing_end_time=frozenset(),
            ),
        )
        inputs = _inputs([])

        result = audit.check_metrics(inputs)

        # no anomaly fields populated
        assert result['disproportionate_token'] == ''
        assert result['incomplete_recording'] == ''
        assert result['impossible_value'] == ''
        assert result['optimization_signal'] == ''
        assert result['anomalies'] == []


class TestMetricsEndTimeMarkerStates:
    """``check_metrics`` reads the #812 markers three-state and reports all three.

    The retired reader degraded BOTH unreadable states to "nothing to explain",
    which after the rename would have read every post-#812 archive as clean.
    """

    _ZERO_TOKEN_PHASES = (
        ('5-execute', 500),
        ('6-finalize', 0),
    )

    def _patch(self, monkeypatch, presence):
        phases = [
            _phase(name, total_tokens=tokens) for name, tokens in self._ZERO_TOKEN_PHASES
        ]
        monkeypatch.setattr(audit, 'parse_metrics_toon', lambda _p: phases)
        monkeypatch.setattr(
            audit, 'parse_metrics_end_time_presence', lambda _p: presence
        )
        return audit.check_metrics(_inputs([]))

    def test_current_marker_explains_the_zero_token_phase(self, monkeypatch):
        """A readable marker naming 6-finalize keeps it OUT of incomplete_recording."""
        result = self._patch(
            monkeypatch,
            audit.MetricsEndTimePresence(
                schema=audit.METRICS_SCHEMA_CURRENT,
                any_phase_missing_end_time=True,
                phases_missing_end_time=frozenset({'6-finalize'}),
            ),
        )

        assert result['incomplete_recording'] == ''
        assert any(
            'explained by the phases_missing_end_time marker' in a
            and '6-finalize' in a
            for a in result['anomalies']
        )

    def test_old_schema_explains_nothing_and_says_so(self, monkeypatch):
        """An old-schema record explains no phase AND names its own state.

        Same zero-token fixture as the test above: the ONLY difference is the
        marker schema, and the zero-token phase moves back into
        `incomplete_recording` because nothing readable accounted for it.
        """
        result = self._patch(
            monkeypatch,
            audit.MetricsEndTimePresence(
                schema=audit.METRICS_SCHEMA_OLD,
                any_phase_missing_end_time=None,
                phases_missing_end_time=None,
            ),
        )

        assert result['incomplete_recording'] == '6-finalize'
        note = next(a for a in result['anomalies'] if 'old-schema' in a)
        assert 'retired partial/unrecorded_phases keys' in note
        assert 'every derived figure is a floor' in note
        # NOT the pre-#812 wording — the two states stay distinguishable.
        assert 'pre-#812' not in note

    def test_pre_812_note_is_distinct_from_old_schema(self, monkeypatch):
        """A record with neither pair reports pre-#812 in its own words."""
        result = self._patch(
            monkeypatch,
            audit.MetricsEndTimePresence(
                schema=audit.METRICS_SCHEMA_PRE_812,
                any_phase_missing_end_time=None,
                phases_missing_end_time=None,
            ),
        )

        assert result['incomplete_recording'] == '6-finalize'
        note = next(a for a in result['anomalies'] if 'pre-#812' in a)
        assert 'carries no end_time-presence markers' in note
        assert 'old-schema' not in note

    def test_every_declared_marker_schema_is_exercised(self, monkeypatch):
        """The three per-state tests above are TOTAL over the module's state set.

        The states are three loose ``METRICS_SCHEMA_*`` module constants, not a
        closed tuple, so a FOURTH state added to ``audit.py`` would be driven by
        no test here while every test above kept passing — the non-total-guard
        archetype. The population is therefore DERIVED from the module and every
        member is driven through ``check_metrics``, so a new state fails HERE
        until the reader handles it.

        It bites because an unhandled state yields an empty ``unreadable_note``:
        the state would be unreadable (so its zero-token phase falls back into
        ``incomplete_recording``) while naming itself nowhere in ``anomalies``,
        which is exactly the "manufactured a verdict out of a state I could not
        read" failure the three-state read exists to prevent.
        """
        declared = {
            value
            for name, value in vars(audit).items()
            if name.startswith('METRICS_SCHEMA_') and isinstance(value, str)
        }

        # Non-vacuity: the derivation found the constants at all.
        assert declared, 'no METRICS_SCHEMA_* constant was discovered on audit'

        for schema in sorted(declared):
            readable = schema == audit.METRICS_SCHEMA_CURRENT
            result = self._patch(
                monkeypatch,
                audit.MetricsEndTimePresence(
                    schema=schema,
                    any_phase_missing_end_time=True if readable else None,
                    phases_missing_end_time=(
                        frozenset({'6-finalize'}) if readable else None
                    ),
                ),
            )
            if readable:
                # A readable marker accounts for the zero-token phase.
                assert result['incomplete_recording'] == '', schema
            else:
                # An unreadable state explains NOTHING and must NAME itself.
                assert result['incomplete_recording'] == '6-finalize', schema
                assert any(schema in a for a in result['anomalies']), (
                    f'marker state {schema!r} is unreadable but names itself in '
                    f'no anomaly line: {result["anomalies"]}'
                )
