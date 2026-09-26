# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_classify_paths_via_extensions_fixtures import _classify_paths_via_extensions


def test_no_extensions_produces_unknown_when_paths_nonempty():
    """With no extensions registered, every path is unclaimed → unknown bucket."""
    bucket, unclaimed = _classify_paths_via_extensions(['scripts/foo.py'], extensions=[])
    assert bucket == 'unknown'
    assert unclaimed == ['scripts/foo.py']
