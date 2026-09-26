# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_classify_paths_via_extensions_fixtures import (
    _PLANNING_SYSTEM_SIBLING_JSON,
    _classify_paths_via_extensions,
    _real_build_extensions,
)


def test_planning_system_recognition_is_a_basename_rule_not_a_plan_directory_rule():
    """The matched negative control that keeps the new entry anchored.

    A sibling JSON file under the SAME ``.plan/`` tree is not recognized and still
    resolves to ``unknown``. Without this case the entry would be
    indistinguishable from a ``('.plan',)`` directory-tree rule or a ``.json``
    suffix rule — either of which would additionally reclassify the git-tracked
    ``.plan/project-architecture/**/*.json`` files, which is precisely the
    collateral reach the basename anchoring was chosen to avoid.
    """
    extensions = _real_build_extensions()
    assert extensions, 'discover_build_extensions() returned no build extensions'

    bucket, unclaimed = _classify_paths_via_extensions([_PLANNING_SYSTEM_SIBLING_JSON], extensions=extensions)

    assert bucket == 'unknown'
    assert unclaimed == [_PLANNING_SYSTEM_SIBLING_JSON]
