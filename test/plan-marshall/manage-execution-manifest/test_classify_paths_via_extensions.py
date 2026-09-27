# SPDX-License-Identifier: FSL-1.1-ALv2
"""Behavior-cluster tests carved from test_classify_paths_via_extensions.py: empty."""

from _manage_execution_manifest_classify_paths_via_extensions_fixtures import _classify_paths_via_extensions

# =============================================================================
# Empty / boundary cases
# =============================================================================


def test_empty_paths_returns_documentation_only():
    """Empty path list defaults to documentation_only (no holistic verification needed)."""
    bucket, unclaimed = _classify_paths_via_extensions([], extensions=[])
    assert bucket == 'documentation_only'
    assert unclaimed == []
