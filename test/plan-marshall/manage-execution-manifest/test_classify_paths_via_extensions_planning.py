# SPDX-License-Identifier: FSL-1.1-ALv2

import pytest
from _manage_execution_manifest_classify_paths_via_extensions_fixtures import (
    _ARCHITECTURE_INDEX_JSON,
    _ARCHITECTURE_MODULE_JSON,
    _ARCHITECTURE_TREE_WITHOUT_PLAN_PARENT,
    _PLANNING_SYSTEM_SIBLING_JSON,
    _classify_paths_via_extensions,
    _real_build_extensions,
    _resolved_role,
)


def test_planning_system_recognition_is_a_basename_rule_not_a_plan_directory_rule():
    """The matched negative control that keeps the planning-system entries anchored.

    A sibling JSON file directly under the SAME ``.plan/`` directory, outside the
    architecture-data tree, is not recognized and still resolves to ``unknown``.
    Without this case the two planning-system entries would be indistinguishable
    from a ``('.plan',)`` directory-tree rule or a ``.json`` suffix rule — either
    of which would reach every other file under ``.plan/``.
    """
    extensions = _real_build_extensions()
    assert extensions, 'discover_build_extensions() returned no build extensions'

    bucket, unclaimed = _classify_paths_via_extensions([_PLANNING_SYSTEM_SIBLING_JSON], extensions=extensions)

    assert bucket == 'unknown'
    assert unclaimed == [_PLANNING_SYSTEM_SIBLING_JSON]


@pytest.mark.parametrize('path', [_ARCHITECTURE_INDEX_JSON, _ARCHITECTURE_MODULE_JSON])
def test_architecture_data_resolves_to_the_config_role_through_the_full_aggregator(path):
    """The tracked architecture data is configuration at every depth of its tree.

    Asserted through the FULL aggregator against the REAL discovered extension
    set, because two facts have to hold and only one is the predicate's: that no
    shipped build extension claims the path first (so it reaches the stage-3
    fallback at all), and that the role it emerges with is ``config``.
    """
    # Arrange
    extensions = _real_build_extensions()
    assert extensions, 'discover_build_extensions() returned no build extensions'

    # Act
    bucket, unclaimed = _classify_paths_via_extensions([path], extensions=extensions)

    # Assert
    assert unclaimed == [], f'{path} must not reach the unclaimed set'
    assert bucket != 'unknown'
    assert _resolved_role(path, extensions=extensions) == 'config'


def test_a_footprint_of_only_architecture_data_resolves_documentation_only():
    """A footprint of exactly the two architecture-data files owes no code build.

    The ``config`` role is excluded from the plan-wide bucket collapse, so a
    change that touches nothing else collapses to ``documentation_only``.
    """
    # Arrange
    extensions = _real_build_extensions()
    assert extensions, 'discover_build_extensions() returned no build extensions'

    # Act
    bucket, unclaimed = _classify_paths_via_extensions(
        [_ARCHITECTURE_INDEX_JSON, _ARCHITECTURE_MODULE_JSON], extensions=extensions
    )

    # Assert
    assert bucket == 'documentation_only'
    assert unclaimed == []


def test_the_architecture_tree_name_without_its_plan_parent_stays_unknown():
    """The second negative control: the tree entry is a TWO-segment run.

    A ``project-architecture/`` directory that does not sit under ``.plan`` is
    not the planning system's data. Without this case the entry would be
    indistinguishable from a one-segment ``('project-architecture',)`` rule.
    """
    # Arrange
    extensions = _real_build_extensions()
    assert extensions, 'discover_build_extensions() returned no build extensions'

    # Act
    bucket, unclaimed = _classify_paths_via_extensions([_ARCHITECTURE_TREE_WITHOUT_PLAN_PARENT], extensions=extensions)

    # Assert
    assert bucket == 'unknown'
    assert unclaimed == [_ARCHITECTURE_TREE_WITHOUT_PLAN_PARENT]
