#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Unit tests for the pure ``_test_scope_divergence`` scope/divergence helpers.

Covers the two pure functions that back the phase-6-finalize whole-tree
module-tests divergence gate (PLAN-14):

* ``resolve_test_scope`` — the scoped module-set derivation and the
  ``divergence_possible`` / ``recommended_target`` decision, across the single
  isolated module, multi-module, shared-infra, and glob-filter cases.
* ``classify_divergence`` — the scoped-vs-whole-tree truth table.

The module has no cross-skill dependencies (stdlib only) and lives on the
``script-shared/scripts/build/`` PYTHONPATH entry the root conftest sets up
for every test, so it is exercised via a plain import — no build, no
subprocess.
"""

import pytest

# Cross-skill import — PYTHONPATH is configured by the root conftest.
from _test_scope_divergence import (
    _module_for_path,
    _touches_shared_infra,
    classify_divergence,
    resolve_test_scope,
)

# The Python build extension's real build_map globs (single-``*`` fnmatch, so a
# ``*`` spans ``/``) — the same globs pre-push-quality-gate derivation filters
# the footprint against.
_GLOBS = ['marketplace/bundles/*.py', 'test/*.py', 'pyproject.toml']

_PROD_PLAN_MARSHALL = 'marketplace/bundles/plan-marshall/skills/foo/scripts/bar.py'
_PROD_PM_PYTHON = 'marketplace/bundles/pm-dev-python/skills/baz/scripts/qux.py'
_SHARED_BUILD = (
    'marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_x.py'
)
_ROOT_CONFTEST = 'test/conftest.py'
_NESTED_CONFTEST = 'test/plan-marshall/build-pyproject/conftest.py'
_DOC = 'marketplace/bundles/plan-marshall/skills/foo/SKILL.md'


@pytest.mark.parametrize(
    ('footprint', 'expected_divergence', 'expected_target'),
    [
        # Single isolated module, no shared infra → match by equivalence.
        pytest.param([_PROD_PLAN_MARSHALL], False, 'plan-marshall', id='single_isolated_module'),
        # Two distinct modules → divergence possible, no scoped target.
        pytest.param([_PROD_PLAN_MARSHALL, _PROD_PM_PYTHON], True, None, id='multi_module'),
        # Single module but touches shared build infra → divergence possible.
        pytest.param([_SHARED_BUILD], True, None, id='shared_build_infra'),
        # Root test/conftest.py is shared cross-module test infra.
        pytest.param([_ROOT_CONFTEST], True, None, id='root_conftest'),
        # Nested test/**/conftest.py is shared cross-module test infra too.
        pytest.param([_NESTED_CONFTEST], True, None, id='nested_conftest'),
        # A non-buildable doc path is filtered out by the glob set; the lone
        # production path drives the (single-module, no-divergence) result.
        pytest.param([_DOC, _PROD_PLAN_MARSHALL], False, 'plan-marshall', id='doc_filtered_out'),
        # A docs-only footprint resolves no module → no divergence, no target.
        pytest.param([_DOC], False, None, id='docs_only_empty'),
        # A root-level build-relevant file (pyproject.toml) matches a glob but
        # resolves to no module → force divergence so no invalid scoped
        # ``module-tests None`` call is emitted downstream.
        pytest.param(['pyproject.toml'], True, None, id='root_build_file_no_module'),
    ],
)
def test_resolve_test_scope_divergence_and_target(footprint, expected_divergence, expected_target):
    """resolve_test_scope classifies divergence and recommends the scoped target."""
    # Arrange / Act
    resolution = resolve_test_scope(footprint, _GLOBS)

    # Assert
    assert resolution.divergence_possible is expected_divergence
    assert resolution.recommended_target == expected_target


def test_resolve_test_scope_dedupes_and_sorts_modules():
    """Multiple paths in the same module collapse to one sorted, de-duped entry."""
    # Arrange
    footprint = [
        _PROD_PM_PYTHON,
        _PROD_PLAN_MARSHALL,
        'marketplace/bundles/plan-marshall/skills/other/scripts/y.py',
    ]

    # Act
    resolution = resolve_test_scope(footprint, _GLOBS)

    # Assert
    assert resolution.scoped_modules == ('plan-marshall', 'pm-dev-python')
    assert resolution.divergence_possible is True
    assert resolution.recommended_target is None


def test_resolve_test_scope_empty_footprint():
    """An empty footprint yields no modules, no divergence, no target."""
    # Arrange / Act
    resolution = resolve_test_scope([], _GLOBS)

    # Assert
    assert resolution.scoped_modules == ()
    assert resolution.divergence_possible is False
    assert resolution.recommended_target is None


@pytest.mark.parametrize(
    ('path', 'expected_module'),
    [
        # Nested paths resolve their owning bundle/module.
        pytest.param(_PROD_PLAN_MARSHALL, 'plan-marshall', id='nested_marketplace_resolves'),
        pytest.param(_NESTED_CONFTEST, 'plan-marshall', id='nested_test_resolves'),
        # Root-level files no longer resolve to a spurious module name.
        pytest.param('test/conftest.py', None, id='root_test_file_no_module'),
        pytest.param('marketplace/bundles/README.md', None, id='root_marketplace_file_no_module'),
        pytest.param('pyproject.toml', None, id='repo_root_file_no_module'),
    ],
)
def test_module_for_path_only_resolves_nested_paths(path, expected_module):
    """_module_for_path resolves a name only for paths nested inside a bundle/module dir."""
    # Arrange / Act / Assert
    assert _module_for_path(path) == expected_module


@pytest.mark.parametrize(
    ('path', 'expected'),
    [
        # Root and nested conftest.py are both shared cross-module test infra.
        pytest.param('test/conftest.py', True, id='root_conftest_is_shared'),
        pytest.param(_NESTED_CONFTEST, True, id='nested_conftest_is_shared'),
        # Shared build infra segment.
        pytest.param(_SHARED_BUILD, True, id='shared_build_infra'),
        # An ordinary production path is not shared infra.
        pytest.param(_PROD_PLAN_MARSHALL, False, id='ordinary_prod_path_not_shared'),
    ],
)
def test_touches_shared_infra(path, expected):
    """_touches_shared_infra still recognizes root test/conftest.py after the dead branch removal."""
    # Arrange / Act / Assert
    assert _touches_shared_infra(path) is expected


@pytest.mark.parametrize(
    ('scoped_outcome', 'whole_tree_outcome', 'expected_divergent'),
    [
        pytest.param('success', 'error', True, id='scoped_green_whole_tree_red'),
        pytest.param('success', 'success', False, id='both_green'),
        pytest.param('error', 'error', False, id='scoped_red_whole_tree_red'),
        pytest.param('error', 'success', False, id='scoped_red_whole_tree_green'),
        pytest.param('success', 'timeout', True, id='scoped_green_whole_tree_timeout'),
    ],
)
def test_classify_divergence_truth_table(scoped_outcome, whole_tree_outcome, expected_divergent):
    """classify_divergence is divergent iff scoped passed while whole-tree did not."""
    # Arrange / Act
    verdict = classify_divergence(scoped_outcome, whole_tree_outcome)

    # Assert
    assert verdict.divergent is expected_divergent
    # ``caught`` mirrors ``divergent`` — the whole-tree route is what surfaces it.
    assert verdict.caught is expected_divergent
