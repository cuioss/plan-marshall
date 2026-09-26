# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_manage_execution_manifest_compose_fixtures import _effective_lane_tier, pytest

# --- Pure resolution helpers -------------------------------------------------


@pytest.mark.parametrize(
    'lane,override,expected',
    [
        ({'class': 'core'}, None, ('minimal', False)),  # class default
        ({'class': 'adversarial'}, None, ('standard', False)),  # class default
        ({'class': 'adversarial', 'tier': 'full'}, None, ('full', False)),  # declared tier
        ({'class': 'core'}, 'full', ('full', False)),  # override wins
        ({'class': 'core'}, 'off', ('minimal', False)),  # immune floor: off ignored → class default
        ({'class': 'derived-state'}, 'off', ('minimal', False)),  # immune floor: off ignored → class default
        ({'class': 'adversarial'}, 'off', (None, True)),  # non-floor off drops (real opt-out)
        ({'class': 'prunable'}, 'off', (None, True)),  # non-floor off drops (real opt-out)
        ({'class': 'prunable'}, 'ask', ('ask', False)),  # ask sentinel
    ],
)
def test_effective_lane_tier_precedence(lane, override, expected):
    """Effective tier resolves override ▸ declared tier ▸ class default.

    A weakening ``off`` on a ``core`` / ``derived-state`` floor class is immune —
    the ``off`` is ignored and resolution falls through to the class default.
    """
    assert _effective_lane_tier(lane, override) == expected
