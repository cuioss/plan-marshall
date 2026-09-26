# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_manage_execution_manifest_compose_fixtures import _parse_cost_magnitude, pytest


@pytest.mark.parametrize(
    'raw,expected',
    [('5K', 5000), ('130K', 130000), ('520K', 520000), ('1.3M', 1300000), ('garbage', 0)],
)
def test_parse_cost_magnitude(raw, expected):
    """Cost magnitudes parse K/M suffixes; an unparseable value degrades to 0."""
    assert _parse_cost_magnitude(raw) == expected
