# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_classify_paths_via_extensions_fixtures import (
    _classify_paths_via_extensions,
    _FakeExtension,
)

# =============================================================================
# Overlap resolution: longest-glob-wins
# =============================================================================


def test_doc_path_is_recognized_generically_before_any_extension():
    """A doc path is tagged documentation by the generic suffix rule and is never
    handed to an extension — so a build extension that would (wrongly) try to
    claim it under another role has no effect.

    This is the post-refactor replacement for the old pm-plugin-dev-beats-
    pm-documents longest-glob test: doc recognition no longer flows through
    extensions at all, so there is no extension overlap to resolve for docs.
    """
    path = 'marketplace/bundles/foo/skills/bar/SKILL.md'
    # An extension that absurdly tries to claim the SKILL.md as production must
    # not win — the generic doc rule fires first and removes the path from the
    # set the extension sees.
    rogue_ext = _FakeExtension(
        'rogue',
        claims={'production': [path], 'test': [], 'documentation': [], 'config': []},
        specificity={(path, 'production'): 99},
    )
    bucket, unclaimed = _classify_paths_via_extensions([path], extensions=[rogue_ext])
    assert bucket == 'documentation_only'
    assert unclaimed == []
