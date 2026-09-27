# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_decision_rules_fixtures import (
    _RETROSPECTIVE,
    _has_declared_lane_override,
    _lane_map,
    _restore_footprint_resolver,
    pytest,
)


class TestHasDeclaredLaneOverride:
    """The predicate backing declared-lane immunity."""

    @pytest.mark.parametrize(
        'lane,expected',
        [
            ('minimal', True),
            ('full', True),
            ('off', True),
            ('ask', True),
            # ``auto`` is the DEFER value — it declares no override intent, so
            # the implicit machinery keeps its say.
            ('auto', False),
        ],
    )
    def test_non_auto_override_counts_as_declared(self, lane, expected):
        assert _has_declared_lane_override(_RETROSPECTIVE, _lane_map(_RETROSPECTIVE, lane)) is expected

    def test_absent_override_is_not_declared(self):
        assert _has_declared_lane_override(_RETROSPECTIVE, {}) is False

    def test_absent_marshal_map_is_not_declared(self):
        # CSV-fallback compose path — no declaration can exist, so nothing is immune.
        assert _has_declared_lane_override(_RETROSPECTIVE, None) is False

    def test_invalid_override_value_is_not_declared(self):
        # ``_lane_override_for`` only returns a value from the closed override
        # vocabulary, so a junk value reads as no declaration at all.
        assert _has_declared_lane_override(_RETROSPECTIVE, _lane_map(_RETROSPECTIVE, 'bogus')) is False

    def test_declaration_matches_across_default_prefix(self):
        # Marshal keys preserve prefixes while candidates are bare-normalized;
        # the lookup strips ``default:`` from the KEY before comparing.
        assert (
            _has_declared_lane_override(
                'pre-submission-self-review',
                _lane_map('default:pre-submission-self-review', 'minimal'),
            )
            is True
        )
