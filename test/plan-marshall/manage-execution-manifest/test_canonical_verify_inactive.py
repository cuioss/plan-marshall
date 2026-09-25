# SPDX-License-Identifier: FSL-1.1-ALv2
"""Behavior-cluster tests carved from test_canonical_verify_inactive.py: footprint."""

#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_canonical_verify_inactive_fixtures import (
    _FOOTPRINT_GATED_CANONICAL_ROLES,
    _footprint_has_role,
)


class TestFootprintHasRole:
    """``_footprint_has_role`` is a lowercased substring test over the footprint."""

    def test_matches_integration_marker_in_path(self):
        markers = _FOOTPRINT_GATED_CANONICAL_ROLES['integration']
        assert _footprint_has_role(['src/test/FooIT.java'], markers) is True

    def test_matches_e2e_marker_in_path(self):
        markers = _FOOTPRINT_GATED_CANONICAL_ROLES['e2e']
        assert _footprint_has_role(['tests/e2e/test_flow.py'], markers) is True

    def test_no_match_returns_false(self):
        markers = _FOOTPRINT_GATED_CANONICAL_ROLES['integration']
        assert _footprint_has_role(['src/main/Foo.java', 'README.md'], markers) is False

    def test_match_is_case_insensitive(self):
        markers = _FOOTPRINT_GATED_CANONICAL_ROLES['integration']
        # The marker ``it.java`` is lowercased; an uppercase path still matches.
        assert _footprint_has_role(['SRC/TEST/BARIT.JAVA'], markers) is True

    def test_empty_footprint_returns_false(self):
        markers = _FOOTPRINT_GATED_CANONICAL_ROLES['integration']
        assert _footprint_has_role([], markers) is False
