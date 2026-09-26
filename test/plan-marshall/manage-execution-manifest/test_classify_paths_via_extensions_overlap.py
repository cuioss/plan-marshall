# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_classify_paths_via_extensions_fixtures import (
    _classify_paths_via_extensions,
    _FakeExtension,
)


def test_overlap_resolution_higher_specificity_wins_across_roles():
    """When two extensions claim the same path under different roles, higher
    specificity wins and determines the final role for that path."""
    path = 'src/foo.py'
    py_ext = _FakeExtension(
        'python',
        claims={'production': [path], 'test': [], 'documentation': [], 'config': []},
        specificity={(path, 'production'): 1},
    )
    confused_ext = _FakeExtension(
        'confused',
        claims={'production': [], 'test': [], 'documentation': [path], 'config': []},
        specificity={(path, 'documentation'): 5},  # absurdly high
    )
    bucket, _ = _classify_paths_via_extensions([path], extensions=[py_ext, confused_ext])
    # confused_ext wins → role becomes documentation → documentation_only
    assert bucket == 'documentation_only'


def test_overlap_resolution_alphabetical_tiebreak_on_equal_specificity():
    """When two extensions tie on specificity, the alphabetically earlier
    domain key wins."""
    path = 'foo.bar'
    a_ext = _FakeExtension(
        'alpha',
        claims={'production': [path], 'test': [], 'documentation': [], 'config': []},
        specificity={(path, 'production'): 2},
    )
    z_ext = _FakeExtension(
        'zulu',
        claims={'production': [], 'test': [], 'documentation': [path], 'config': []},
        specificity={(path, 'documentation'): 2},
    )
    bucket, _ = _classify_paths_via_extensions([path], extensions=[a_ext, z_ext])
    # alpha wins alphabetically → production → production_only
    assert bucket == 'production_only'


def test_overlap_resolution_is_extension_order_independent():
    """Result must be identical regardless of extension iteration order."""
    path = 'foo.bar'
    a_ext = _FakeExtension(
        'alpha',
        claims={'production': [path], 'test': [], 'documentation': [], 'config': []},
        specificity={(path, 'production'): 5},
    )
    b_ext = _FakeExtension(
        'beta',
        claims={'production': [], 'test': [], 'documentation': [path], 'config': []},
        specificity={(path, 'documentation'): 1},
    )
    bucket_ab, _ = _classify_paths_via_extensions([path], extensions=[a_ext, b_ext])
    bucket_ba, _ = _classify_paths_via_extensions([path], extensions=[b_ext, a_ext])
    assert bucket_ab == bucket_ba == 'production_only'
