# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_classify_paths_via_extensions_fixtures import (
    _classify_paths_via_extensions,
    _FakeExtension,
)


def test_unknown_bucket_for_partially_unclaimed():
    """At least one unclaimed path forces the entire plan-wide bucket to unknown."""
    py_ext = _FakeExtension(
        'python',
        claims={
            'production': ['scripts/foo.py'],
            'test': [],
            'documentation': [],
            'config': [],
        },
    )
    bucket, unclaimed = _classify_paths_via_extensions(['scripts/foo.py', 'mystery.xyz'], extensions=[py_ext])
    assert bucket == 'unknown'
    assert unclaimed == ['mystery.xyz']


# =============================================================================
# Unclaimed-path warning emission
# =============================================================================


def test_unknown_returns_unclaimed_paths_list():
    """The aggregator returns the unclaimed-paths list so callers can route the
    warning to the appropriate decision-log surface."""
    py_ext = _FakeExtension(
        'python',
        claims={
            'production': ['scripts/foo.py'],
            'test': [],
            'documentation': [],
            'config': [],
        },
    )
    bucket, unclaimed = _classify_paths_via_extensions(
        ['scripts/foo.py', 'mystery1.xyz', 'mystery2.xyz'], extensions=[py_ext]
    )
    assert bucket == 'unknown'
    assert set(unclaimed) == {'mystery1.xyz', 'mystery2.xyz'}
