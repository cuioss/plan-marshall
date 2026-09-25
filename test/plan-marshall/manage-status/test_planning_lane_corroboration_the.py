# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_status_planning_lane_corroboration_fixtures import evaluate_signals_pure


class TestTheConfidencePopulationIsDerivedNotMirrored:
    """The split's population comes FROM ``signals``, minus the one excluded key.

    It was a hand-maintained tuple mirroring that mapping minus
    ``planning_lane_override``. A routing signal added to ``signals`` was then
    silently omitted from ``scored_signals`` / ``null_signals`` /
    ``signals_resolved``, so the vector reported full resolution over a
    population it had never scanned, and ``signals_total`` under-published the
    size it was taken over.

    ⛔ Every expectation below is DERIVED from the returned ``signals`` mapping,
    never restated as a literal. A literal is precisely what cannot notice
    growth: the day a seventh signal is added, an expectation of ``6`` still
    passes against a split that ignores it. Derived, the same day fails here.
    """

    _VECTOR = {
        'plan_source': 'lesson',
        'scope_estimate': 'surgical',
        'change_type': 'bug_fix',
        'compatibility': 'deprecation',
        'request_concrete': True,
        'risk_prose': False,
        'override': None,
    }

    def test_the_population_is_every_signal_but_the_override(self):
        result = evaluate_signals_pure(**self._VECTOR)

        expected = set(result['signals']) - {'planning_lane_override'}
        assert result['confidence']['signals_total'] == len(expected)

    def test_exactly_one_signal_is_excluded_and_it_is_the_override(self):
        """The exclusion is a subtrahend of ONE — not an arbitrary shorter list."""
        result = evaluate_signals_pure(**self._VECTOR)

        assert len(result['signals']) - result['confidence']['signals_total'] == 1
        assert 'planning_lane_override' not in result['confidence']['null_signals']

    def test_the_split_partitions_the_population_it_publishes(self):
        """``resolved + null == total`` — no signal falls outside both buckets."""
        result = evaluate_signals_pure(**{**self._VECTOR, 'change_type': None})
        confidence = result['confidence']

        assert confidence['signals_resolved'] + confidence['signals_null'] == (confidence['signals_total'])

    def test_a_null_signal_is_named_by_the_key_the_map_uses(self):
        """The null names are read off the mapping, so they cannot drift from it."""
        result = evaluate_signals_pure(**{**self._VECTOR, 'compatibility': None})

        assert set(result['confidence']['null_signals']) <= set(result['signals'])
        assert 'compatibility' in result['confidence']['null_signals']

    def test_a_fully_resolved_vector_reports_no_null(self):
        """The control — deriving must not manufacture nulls out of the map's keys."""
        result = evaluate_signals_pure(**self._VECTOR)

        assert result['confidence']['null_signals'] == []
        assert result['confidence']['signals_null'] == 0
        assert result['confidence']['signals_resolved'] == (result['confidence']['signals_total'])
