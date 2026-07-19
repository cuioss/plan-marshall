#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Unit tests for the pure ``_test_scope_divergence`` scope/divergence helpers.

Covers the two pure functions that back the phase-6-finalize whole-tree
module-tests divergence gate (PLAN-14):

* ``resolve_test_scope`` — the scoped module-set derivation and the
  ``divergence_possible`` / ``recommended_target`` decision, across the single
  isolated module, multi-module, shared-infra, and glob-filter cases.
* ``classify_divergence`` — the scoped-vs-whole-tree truth table.

The module has no cross-skill dependencies (stdlib only), so it is loaded by
absolute path and exercised in isolation — no build, no subprocess.
"""

import importlib.util
from pathlib import Path

import pytest

_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
)
_MODULE_PATH = (
    _SCRIPTS_DIR / 'script-shared' / 'scripts' / 'build' / '_test_scope_divergence.py'
)


def _load(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_mod = _load('_test_scope_divergence', _MODULE_PATH)
resolve_test_scope = _mod.resolve_test_scope
classify_divergence = _mod.classify_divergence

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
    assert resolution.scoped_modules == ('pm-dev-python', 'plan-marshall')
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
