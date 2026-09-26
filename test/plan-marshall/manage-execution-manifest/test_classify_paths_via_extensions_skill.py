# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_classify_paths_via_extensions_fixtures import _classify_paths_via_extensions


def test_skill_md_recognized_as_documentation_generically():
    """A marketplace SKILL.md path is documentation by the generic suffix rule —
    no per-bundle extension overlap resolution is involved anymore."""
    path = 'marketplace/bundles/foo/skills/bar/SKILL.md'
    bucket, unclaimed = _classify_paths_via_extensions([path], extensions=[])
    assert bucket == 'documentation_only'
    assert unclaimed == []
