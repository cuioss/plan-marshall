# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_classify_paths_via_extensions_fixtures import (
    _classify_paths_via_extensions,
    _is_template_path,
)


def test_template_membership_is_a_basename_suffix_and_nothing_wider():
    """The stage cannot widen beyond a basename ending in ``.template``.

    A path merely CONTAINING the token, or sitting under a directory named for
    it, is not a template — it stays ``unknown``, so the rule's blast radius is
    the suffix alone.
    """
    assert _is_template_path('pkg/x.py.template')
    assert not _is_template_path('pkg/x.template.py')
    assert not _is_template_path('templates/x.py')

    for path in ('pkg/mystery.template.xyz', 'templates/mystery.xyz', 'mystery.xyz'):
        bucket, unclaimed = _classify_paths_via_extensions([path], extensions=[])
        assert bucket == 'unknown', path
        assert unclaimed == [path], path
