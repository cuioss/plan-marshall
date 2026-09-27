# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_classify_paths_via_extensions_fixtures import (
    _classify_paths_via_extensions,
    _resolved_role,
)


def test_documentation_only_bucket_recognized_generically():
    """A *.md path is recognized as documentation by the generic suffix rule with
    NO extension claiming it — documentation has no build owner."""
    bucket, unclaimed = _classify_paths_via_extensions(['README.md'], extensions=[])
    assert bucket == 'documentation_only'
    assert unclaimed == []


def test_documentation_suffixes_all_recognized_generically():
    """Every documentation suffix (.md / .adoc / .asciidoc) is recognized
    generically without any extension."""
    for path in ('README.md', 'doc/guide.adoc', 'doc/spec.asciidoc'):
        bucket, unclaimed = _classify_paths_via_extensions([path], extensions=[])
        assert bucket == 'documentation_only'
        assert unclaimed == []


def test_documentation_render_target_wins_by_delegation():
    """A ``.md`` render target delegates to the doc predicate, not the terminal."""
    assert _resolved_role('docs/guide.md.template') == 'documentation'
