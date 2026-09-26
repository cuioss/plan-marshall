# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_classify_paths_via_extensions_fixtures import (
    _classify_paths_via_extensions,
    _FakeExtension,
)


def test_specificity_raising_is_treated_as_zero():
    """An extension whose classify_path_specificity raises is treated as score 0."""

    class _RaisingSpecExt(_FakeExtension):
        def classify_path_specificity(self, path, role):
            raise RuntimeError('boom')

    path = 'foo.bar'
    bad = _RaisingSpecExt(
        'alpha',
        claims={'production': [path], 'test': [], 'documentation': [], 'config': []},
    )
    good = _FakeExtension(
        'zulu',
        claims={'production': [], 'test': [], 'documentation': [path], 'config': []},
        specificity={(path, 'documentation'): 3},
    )
    bucket, _ = _classify_paths_via_extensions([path], extensions=[bad, good])
    # zulu specificity=3 beats bad specificity=0 → documentation_only
    assert bucket == 'documentation_only'
