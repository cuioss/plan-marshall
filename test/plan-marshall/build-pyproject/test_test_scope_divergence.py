#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Unit tests for the pure ``_test_scope_divergence`` scope/divergence helpers.

Covers the two pure functions that back the phase-6-finalize whole-tree
module-tests divergence gate (PLAN-14):

* ``resolve_test_scope`` - the scoped module-set derivation and the
  ``divergence_possible`` / ``recommended_target`` / ``unresolved_paths``
  decision, across the single isolated module, multi-module, shared-infra,
  unmapped-path and mixed cases.
* ``classify_divergence`` - the scoped-vs-whole-tree truth table.

The module has no cross-skill dependencies (stdlib only) and lives on the
``script-shared/scripts/build/`` PYTHONPATH entry the root conftest sets up
for every test, so it is exercised via a plain import - no build, no
subprocess.

``resolve_test_scope`` takes the registered-module names as a third argument
(the purity contract: the set is supplied, never read from an inventory inside
the pure module), so every call below passes ``_REGISTERED_MODULES``.

A dedicated section covers the ``tests/`` sibling root. Both root-sensitive
seams -- ``_module_for_path`` and ``_touches_shared_infra`` -- must recognise
the SAME roots, and the tests pin that jointly rather than one at a time: a
``tests/{module}/conftest.py`` resolves to a module AND is shared infra, so
widening only the first seam would turn a whole-tree verdict into a confident
scoped one. The negative controls pin the other half of the contract: widening
WHICH roots are recognised changed nothing about what happens to a name that
resolves to no registered module.
"""

import fnmatch
from typing import NamedTuple

import _test_scope_divergence
import pytest

# Cross-skill import - PYTHONPATH is configured by the root conftest.
from _test_scope_divergence import (
    _TEST_ROOTS,
    _module_for_path,
    _touches_shared_infra,
    classify_divergence,
    resolve_test_scope,
)

from conftest import load_script_module

# The Python build extension's real build_map globs (single-``*`` fnmatch, so a
# ``*`` spans ``/``) - the same globs pre-push-quality-gate derivation filters
# the footprint against.
_GLOBS = ['marketplace/bundles/*.py', 'test/*.py', 'pyproject.toml']

#: The caller-enumerated registered module names. In production the handler
#: derives this from ``find_bundles()`` + ``extract_bundle_name()``; here it is
#: injected directly so the pure function stays deterministic.
_REGISTERED_MODULES = frozenset({'plan-marshall', 'pm-dev-python', 'pm-plugin-development'})

_PROD_PLAN_MARSHALL = 'marketplace/bundles/plan-marshall/skills/foo/scripts/bar.py'
_PROD_PM_PYTHON = 'marketplace/bundles/pm-dev-python/skills/baz/scripts/qux.py'
_SHARED_BUILD = 'marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_x.py'
_ROOT_CONFTEST = 'test/conftest.py'
_NESTED_CONFTEST = 'test/plan-marshall/build-pyproject/conftest.py'
_DOC = 'marketplace/bundles/plan-marshall/skills/foo/SKILL.md'
#: A non-``.py`` file owned by a DIFFERENT bundle. It matches no build_map glob,
#: so a glob-filtered module derivation drops the bundle entirely - the exact
#: shape that under-reported this plan's own two-bundle footprint as one module.
_CROSS_BUNDLE_DOC = 'marketplace/bundles/pm-plugin-development/skills/plugin-doctor/references/rule-catalog.md'
#: Neither build-map-matched nor module-owning: the shape that used to be
#: silently discarded and reported as ``divergence_possible: false``.
_UNMAPPED_DOC = 'doc/developer/build.adoc'
_UNMAPPED_WORKFLOW = '.github/workflows/python-verify.yml'
#: Beside ``marketplace/bundles/`` but outside it in module terms: the multi-target
#: generator owns no bundle. The declared source-to-test mapping names a test
#: target for it, but ``_REGISTERED_MODULES`` does not carry that target, so
#: against THIS set the path stays unresolved — the registered-name guard applies
#: to a mapped name exactly as to a segment-derived one.
_UNMAPPED_TARGETS = 'marketplace/targets/generate.py'
#: The bundle-neutral cross-bundle test-helper root. Its first path segment is
#: ``_shared``, which is not a registered module - taking it verbatim invented a
#: phantom module a scoped run could never target.
_SHARED_TEST_HELPER = 'test/_shared/_build_class_roster.py'
#: A well-formed bundle path whose bundle token names no registered module.
_UNREGISTERED_BUNDLE = 'marketplace/bundles/not-a-real-bundle/skills/foo/scripts/bar.py'


def _load_pyproject_extension():
    """Load the build-pyproject extension module under a distinct name.

    All four build skills ship an ``extension.py`` sharing the module basename
    ``extension``, so ``import extension`` resolves to whichever sys.path entry
    comes first. The shared loader is given an explicit module name instead, so
    the cross-check below reads the intended declaration.

    That name is REGISTERED in ``sys.modules`` — ``load_script_module`` always
    registers. ``pyproject_extension_for_root_crosscheck`` is used nowhere else
    in the tree and nothing imports it by name, so the registration displaces no
    other module's copy; it is a distinct entry rather than a shared one.
    """
    return load_script_module(
        'plan-marshall',
        'build-pyproject',
        'extension.py',
        'pyproject_extension_for_root_crosscheck',
    )


@pytest.mark.parametrize(
    ('footprint', 'expected_divergence', 'expected_target'),
    [
        # Single isolated module, no shared infra, nothing unresolved -> match by
        # equivalence. This is the POSITIVE CONTROL for the fail-closed change:
        # without it, a fix that simply made every verdict divergent would pass.
        pytest.param([_PROD_PLAN_MARSHALL], False, 'plan-marshall', id='single_isolated_module'),
        # Two distinct modules -> divergence possible, no scoped target.
        pytest.param([_PROD_PLAN_MARSHALL, _PROD_PM_PYTHON], True, None, id='multi_module'),
        # Single module but touches shared build infra -> divergence possible.
        pytest.param([_SHARED_BUILD], True, None, id='shared_build_infra'),
        # Root test/conftest.py is shared cross-module test infra.
        pytest.param([_ROOT_CONFTEST], True, None, id='root_conftest'),
        # Nested test/**/conftest.py is shared cross-module test infra too.
        pytest.param([_NESTED_CONFTEST], True, None, id='nested_conftest'),
        # A doc path in the SAME module as the production path collapses to one
        # module - no divergence, scoped target unchanged.
        pytest.param([_DOC, _PROD_PLAN_MARSHALL], False, 'plan-marshall', id='doc_same_module'),
        # A docs-only footprint still owns its bundle: module ownership is
        # independent of the build_map glob filter, so the bundle is the scoped
        # target rather than a None that would render `module-tests None`.
        pytest.param([_DOC], False, 'plan-marshall', id='docs_only_owns_its_bundle'),
        # REGRESSION (observed on this plan's own finalize): a cross-bundle
        # footprint whose second bundle is reached only by a NON-`.py` file. The
        # doc matches no build_map glob, so a glob-filtered module derivation
        # reported a single module and scoped the gate to `plan-marshall` alone -
        # while `pm-plugin-development`'s tests assert on that very catalogue.
        # That is the scoped-green / whole-tree-red class the gate exists to
        # catch, so the span must be two modules and the run whole-tree.
        pytest.param(
            [_PROD_PLAN_MARSHALL, _CROSS_BUNDLE_DOC],
            True,
            None,
            id='cross_bundle_via_non_py_doc',
        ),
        # A root-level file resolves to no module -> force divergence so no
        # invalid scoped ``module-tests None`` call is emitted downstream. It
        # happens to match a build_map glob, but that is no longer what makes it
        # fail closed (see the unmapped cases below).
        pytest.param(['pyproject.toml'], True, None, id='root_build_file_no_module'),
        # REPRODUCED SHAPE 1: an unmapped-only footprint. Neither build-map-matched
        # nor module-owning; previously reported as `divergence_possible: false`.
        pytest.param([_UNMAPPED_DOC], True, None, id='unmapped_doc_only'),
        pytest.param(
            [_UNMAPPED_DOC, _UNMAPPED_WORKFLOW, _UNMAPPED_TARGETS],
            True,
            None,
            id='unmapped_population_only',
        ),
        # REPRODUCED SHAPE 3: a test/_shared/ path must not yield a phantom module.
        pytest.param([_SHARED_TEST_HELPER], True, None, id='shared_test_helper'),
        # A bundle token that names no registered module is not a module either.
        pytest.param([_UNREGISTERED_BUNDLE], True, None, id='unregistered_bundle_token'),
    ],
)
def test_resolve_test_scope_divergence_and_target(footprint, expected_divergence, expected_target):
    """resolve_test_scope classifies divergence and recommends the scoped target."""
    # Arrange / Act
    resolution = resolve_test_scope(footprint, _GLOBS, _REGISTERED_MODULES)

    # Assert
    assert resolution.divergence_possible is expected_divergence
    assert resolution.recommended_target == expected_target


def test_single_module_footprint_is_the_positive_control():
    """A genuine single-module footprint still resolves confidently.

    The explicit counter-case to the fail-closed change: the fix must not
    degenerate into "every verdict is divergent". Asserts the FULL resolution,
    including that nothing landed in ``unresolved_paths``.
    """
    # Arrange / Act
    resolution = resolve_test_scope([_PROD_PLAN_MARSHALL, _DOC], _GLOBS, _REGISTERED_MODULES)

    # Assert
    assert resolution.scoped_modules == ('plan-marshall',)
    assert resolution.divergence_possible is False
    assert resolution.recommended_target == 'plan-marshall'
    assert resolution.unresolved_paths == ()


def test_unmapped_only_footprint_fails_closed_without_a_build_relevance_prefilter():
    """An unmapped-only footprint fails closed, and the old rule would not have.

    Mutation guard for the PRIMARY fix. The removed third disjunct was
    ``has_matching_files and len(scoped_modules) == 0``, so a footprint whose
    paths matched no ``build.map`` glob escaped the whole-tree fallback entirely.
    Reconstructing that pre-fix predicate inline proves the case below is not
    vacuous: it really did report the benign verdict before.
    """
    # Arrange
    footprint = [_UNMAPPED_DOC, _UNMAPPED_WORKFLOW]

    # Act - the pre-fix three-condition disjunction, reconstructed inline.
    pre_fix_has_matching_files = any(fnmatch.fnmatch(path, glob) for path in footprint for glob in _GLOBS)
    pre_fix_modules: set[str] = set()  # neither path owns a module
    pre_fix_divergence = (
        len(pre_fix_modules) > 1
        or any(_touches_shared_infra(path) for path in footprint)
        or (pre_fix_has_matching_files and len(pre_fix_modules) == 0)
    )

    # Assert - the pre-fix rule said "no divergence possible", which is the defect.
    assert pre_fix_divergence is False, (
        'The reconstructed pre-fix predicate no longer reproduces the observed '
        'defect, so the fail-closed case below proves nothing'
    )

    # And the live resolver must NOT agree with it.
    resolution = resolve_test_scope(footprint, _GLOBS, _REGISTERED_MODULES)
    assert resolution.scoped_modules == ()
    assert resolution.divergence_possible is True
    assert resolution.recommended_target is None
    assert resolution.unresolved_paths == (_UNMAPPED_DOC, _UNMAPPED_WORKFLOW)


def test_mixed_footprint_discloses_unresolved_paths_instead_of_a_confident_target():
    """The mixed shape: a real bundle path plus paths that map to no module.

    Today's worst shape. The unmapped paths used to be dropped silently while a
    CONFIDENT ``recommended_target`` was returned that did not cover them. They
    must now be enumerated (ADR-014) and must force the whole-tree verdict.
    """
    # Arrange
    footprint = [_DOC, _UNMAPPED_DOC, _UNMAPPED_WORKFLOW]

    # Act
    resolution = resolve_test_scope(footprint, _GLOBS, _REGISTERED_MODULES)

    # Assert - the bundle is still recognised, but no confident target is claimed.
    assert resolution.scoped_modules == ('plan-marshall',)
    assert resolution.divergence_possible is True
    assert resolution.recommended_target is None
    assert resolution.unresolved_paths == (_UNMAPPED_DOC, _UNMAPPED_WORKFLOW)


def test_shared_test_helper_yields_no_phantom_module_and_is_shared_infra():
    """``test/_shared/...`` must not yield the phantom module ``_shared``.

    Both halves matter: the derived name is rejected (so it never reaches
    ``scoped_modules`` and never becomes a scoped pytest target that resolves to
    nothing), AND the path is recognised as cross-module test infrastructure.
    """
    # Arrange / Act
    resolution = resolve_test_scope([_SHARED_TEST_HELPER], _GLOBS, _REGISTERED_MODULES)

    # Assert
    assert '_shared' not in resolution.scoped_modules
    assert resolution.scoped_modules == ()
    assert resolution.unresolved_paths == (_SHARED_TEST_HELPER,)
    assert resolution.divergence_possible is True
    assert resolution.recommended_target is None
    assert _touches_shared_infra(_SHARED_TEST_HELPER) is True


def test_module_span_is_independent_of_the_build_map_glob_filter():
    """Mutation guard: module ownership must not be gated on the glob filter.

    Reconstructs the pre-fix derivation (filter by ``build_map_globs`` FIRST,
    then take the owning module) and asserts it produces the WRONG single-module
    answer on the cross-bundle footprint. Without this, the regression case above
    would still pass if the glob filter were reintroduced in a form that happened
    to match the fixture doc - the assertion would be vacuous.
    """
    # Arrange
    footprint = [_PROD_PLAN_MARSHALL, _CROSS_BUNDLE_DOC]

    # Act - the pre-fix derivation, reconstructed inline.
    pre_fix_modules = set()
    for path in footprint:
        if not any(fnmatch.fnmatch(path, glob) for glob in _GLOBS):
            continue
        segments = path.split('/')
        if path.startswith('marketplace/bundles/') and len(segments) > 3:
            pre_fix_modules.add(segments[2])

    # Assert - the pre-fix rule drops pm-plugin-development, which is the defect.
    assert pre_fix_modules == {'plan-marshall'}, (
        'The reconstructed pre-fix derivation no longer reproduces the observed '
        'defect, so the regression case above proves nothing'
    )

    # And the live resolver must NOT agree with it.
    resolution = resolve_test_scope(footprint, _GLOBS, _REGISTERED_MODULES)
    assert resolution.scoped_modules == ('plan-marshall', 'pm-plugin-development')
    assert resolution.divergence_possible is True


def test_resolve_test_scope_dedupes_and_sorts_modules():
    """Multiple paths in the same module collapse to one sorted, de-duped entry."""
    # Arrange
    footprint = [
        _PROD_PM_PYTHON,
        _PROD_PLAN_MARSHALL,
        'marketplace/bundles/plan-marshall/skills/other/scripts/y.py',
    ]

    # Act
    resolution = resolve_test_scope(footprint, _GLOBS, _REGISTERED_MODULES)

    # Assert
    assert resolution.scoped_modules == ('plan-marshall', 'pm-dev-python')
    assert resolution.divergence_possible is True
    assert resolution.recommended_target is None
    assert resolution.unresolved_paths == ()


def test_resolve_test_scope_empty_footprint():
    """An empty footprint is the ONE legitimate benign verdict.

    It genuinely has nothing to test, so it alone keeps ``divergence_possible:
    False`` with ``recommended_target: None``. Collapsing it into the fail-closed
    branch would force a whole-tree pytest run on every no-op footprint.
    """
    # Arrange / Act
    resolution = resolve_test_scope([], _GLOBS, _REGISTERED_MODULES)

    # Assert
    assert resolution.scoped_modules == ()
    assert resolution.divergence_possible is False
    assert resolution.recommended_target is None
    assert resolution.unresolved_paths == ()


def test_empty_registered_module_set_resolves_nothing():
    """With no registered modules supplied, no derived name can be confirmed.

    The pure-function half of the caller's ``modules_resolvable`` fail-closed
    branch: a footprint that would otherwise resolve confidently instead reports
    every entry as unresolved and routes to the whole tree.
    """
    # Arrange / Act
    resolution = resolve_test_scope([_PROD_PLAN_MARSHALL], _GLOBS, frozenset())

    # Assert
    assert resolution.scoped_modules == ()
    assert resolution.divergence_possible is True
    assert resolution.recommended_target is None
    assert resolution.unresolved_paths == (_PROD_PLAN_MARSHALL,)


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
        # A well-formed segment that names no registered module is rejected.
        pytest.param(_SHARED_TEST_HELPER, None, id='shared_test_helper_no_phantom_module'),
        pytest.param(_UNREGISTERED_BUNDLE, None, id='unregistered_bundle_token_rejected'),
        # A path outside both roots that no declared mapping covers derives nothing.
        pytest.param(_UNMAPPED_DOC, None, id='doc_root_no_module'),
        # A mapped path whose target is not in the registered set is rejected by
        # the same guard as an unregistered segment.
        pytest.param(_UNMAPPED_TARGETS, None, id='marketplace_targets_target_not_registered'),
    ],
)
def test_module_for_path_only_resolves_registered_nested_paths(path, expected_module):
    """_module_for_path resolves a name only for a REGISTERED module nested inside its dir."""
    # Arrange / Act / Assert
    assert _module_for_path(path, _REGISTERED_MODULES) == expected_module


@pytest.mark.parametrize(
    ('path', 'expected'),
    [
        # Root and nested conftest.py are both shared cross-module test infra.
        pytest.param('test/conftest.py', True, id='root_conftest_is_shared'),
        pytest.param(_NESTED_CONFTEST, True, id='nested_conftest_is_shared'),
        # Shared build infra segment.
        pytest.param(_SHARED_BUILD, True, id='shared_build_infra'),
        # The bundle-neutral cross-bundle test-helper root.
        pytest.param(_SHARED_TEST_HELPER, True, id='shared_test_helper_root_is_shared'),
        pytest.param('test/_shared/conftest.py', True, id='shared_test_helper_nested_is_shared'),
        # Negative controls: an ordinary production path and an ordinary test path
        # under a real bundle are NOT shared infra, so the new prefix does not
        # over-claim every ``test/`` path.
        pytest.param(_PROD_PLAN_MARSHALL, False, id='ordinary_prod_path_not_shared'),
        pytest.param(
            'test/plan-marshall/build-pyproject/test_pyproject_build.py',
            False,
            id='ordinary_test_path_not_shared',
        ),
    ],
)
def test_touches_shared_infra(path, expected):
    """_touches_shared_infra recognizes conftest, shared build infra, and test/_shared/."""
    # Arrange / Act / Assert
    assert _touches_shared_infra(path) is expected


# =============================================================================
# The `tests/` sibling root: recognised symmetrically, still fail-closed
# =============================================================================

#: A ``tests/``-rooted path whose segment 1 IS a registered module. Under the
#: ``test/``-only derivation this resolved to no module at all.
_TESTS_ROOT_REGISTERED = 'tests/plan-marshall/build-pyproject/test_x.py'
#: The ``tests/`` sibling of the cross-bundle test-helper root.
_TESTS_SHARED_HELPER = 'tests/_shared/_build_class_roster.py'
#: A ``tests/``-rooted conftest under a registered module. This is the path that
#: makes the two-seam symmetry load-bearing: it resolves to a module, so if the
#: shared-infra predicate did NOT also recognise the root it would yield a
#: confident single-module verdict for a change that can break every suite.
_TESTS_NESTED_CONFTEST = 'tests/plan-marshall/build-pyproject/conftest.py'
#: A ``tests/``-rooted path whose segment 1 names no registered module.
_TESTS_UNREGISTERED = 'tests/not-a-real-bundle/test_y.py'


def test_module_for_path_resolves_a_tests_rooted_path():
    """Segment 1 under the ``tests/`` sibling root resolves exactly as under ``test/``.

    The asymmetry this closes: ``_TEST_ROOTS`` declared both roots while the
    derivation prefix-matched ``test/`` alone, so a ``tests/``-rooted path owned
    no module.
    """
    assert _module_for_path(_TESTS_ROOT_REGISTERED, _REGISTERED_MODULES) == 'plan-marshall'
    # Matched control: the original root is unchanged.
    assert _module_for_path(_NESTED_CONFTEST, _REGISTERED_MODULES) == 'plan-marshall'


@pytest.mark.parametrize(
    ('path', 'case'),
    [
        pytest.param(_TESTS_UNREGISTERED, 'segment 1 names no registered module', id='tests_unregistered'),
        pytest.param(_TESTS_SHARED_HELPER, 'the phantom _shared name', id='tests_shared_helper'),
        pytest.param('tests/conftest.py', 'a root-level file owns no module', id='tests_root_file'),
        pytest.param(_UNREGISTERED_BUNDLE, 'an unregistered bundle token', id='marketplace_unregistered'),
    ],
)
def test_unmappable_paths_under_either_root_still_fail_closed(path, case):
    """NEGATIVE CONTROL: widening WHICH roots are recognised widened nothing else.

    The edit changed which roots yield a candidate name. It must NOT change what
    happens to a name that resolves to no registered module: the path is still
    reported in ``unresolved_paths``, still forces ``divergence_possible``, and
    still yields no confident ``recommended_target``. Without this control, a
    widening that also relaxed the registered-module guard would pass the
    positive cases above while reintroducing the fail-open.
    """
    assert _module_for_path(path, _REGISTERED_MODULES) is None, (
        f'{path!r} ({case}) resolved to a module; the registered-module guard was widened along with the root set.'
    )

    resolution = resolve_test_scope([path], _GLOBS, _REGISTERED_MODULES)

    assert resolution.scoped_modules == ()
    assert resolution.unresolved_paths == (path,), (
        'the unresolved-paths disclosure was weakened; an unmappable path must stay visible to the consumer (ADR-014).'
    )
    assert resolution.divergence_possible is True
    assert resolution.recommended_target is None


@pytest.mark.parametrize(
    ('path', 'expected'),
    [
        pytest.param(_TESTS_NESTED_CONFTEST, True, id='tests_nested_conftest_is_shared'),
        pytest.param('tests/conftest.py', True, id='tests_root_conftest_is_shared'),
        pytest.param(_TESTS_SHARED_HELPER, True, id='tests_shared_helper_is_shared'),
        # Negative control: an ordinary tests/-rooted module test is NOT shared
        # infra, so mirroring the root did not make every tests/ path shared.
        pytest.param(_TESTS_ROOT_REGISTERED, False, id='ordinary_tests_path_not_shared'),
    ],
)
def test_touches_shared_infra_mirrors_every_test_root(path, expected):
    """The shared-infra predicate recognises the same roots the derivation does.

    Mirroring BOTH seams together is what keeps the widening fail-closed. A
    ``tests/{module}/conftest.py`` now resolves to a module; had only
    ``_module_for_path`` been widened, this path would have produced
    ``divergence_possible: False`` with a confident single-module target — a
    conftest change scoped to one module's suite when it can break them all.
    """
    assert _touches_shared_infra(path) is expected


def test_a_tests_rooted_conftest_still_forces_the_whole_tree():
    """End to end: the newly-resolvable ``tests/`` conftest does NOT go scoped.

    The two unit assertions above compose here into the verdict that matters.
    Its matched positive control is
    :func:`test_module_for_path_resolves_a_tests_rooted_path` plus the
    ``ordinary_tests_path_not_shared`` case — together they prove the whole-tree
    verdict comes from the shared-infra recognition, not from the path having
    failed to resolve at all.
    """
    resolution = resolve_test_scope([_TESTS_NESTED_CONFTEST], _GLOBS, _REGISTERED_MODULES)

    assert resolution.scoped_modules == ('plan-marshall',), (
        'the conftest no longer resolves to its module, so the whole-tree verdict below '
        'would hold for the wrong reason.'
    )
    assert resolution.unresolved_paths == ()
    assert resolution.divergence_possible is True
    assert resolution.recommended_target is None


def test_an_ordinary_tests_rooted_path_can_still_resolve_confidently():
    """POSITIVE CONTROL: the widening did not degenerate into "always divergent".

    A single ``tests/``-rooted module path, touching no shared infra and leaving
    nothing unresolved, still yields the confident scoped target -- which is the
    whole point of recognising the root.
    """
    resolution = resolve_test_scope([_TESTS_ROOT_REGISTERED], _GLOBS, _REGISTERED_MODULES)

    assert resolution.scoped_modules == ('plan-marshall',)
    assert resolution.unresolved_paths == ()
    assert resolution.divergence_possible is False
    assert resolution.recommended_target == 'plan-marshall'


# =============================================================================
# Non-bundle test trees: a registered target that no bundle carries
# =============================================================================

#: The test trees in this repository that hold tests and belong to no bundle.
#: The pure function takes whatever set its caller enumerated; these are the
#: names the I/O sibling ``_test_scope_targets`` registers beside the bundles.
_NON_BUNDLE_TEST_TREES = (
    'default',
    'finalize-step-deploy-target',
    'finalize-step-sync-plugin-cache',
    'marketplace',
    'sync-harnesses',
)

#: The registered set a caller hands in once test trees are registered too. The
#: bundle cases above keep ``_REGISTERED_MODULES`` unchanged.
_REGISTERED_TARGETS = _REGISTERED_MODULES | frozenset(_NON_BUNDLE_TEST_TREES)


@pytest.mark.parametrize('tree', _NON_BUNDLE_TEST_TREES)
def test_a_changed_path_in_a_non_bundle_test_tree_resolves_that_tree(tree):
    """One changed path under a registered non-bundle tree targets that tree."""
    path = f'test/{tree}/test_something.py'

    resolution = resolve_test_scope([path], _GLOBS, _REGISTERED_TARGETS)

    assert resolution.scoped_modules == (tree,)
    assert resolution.unresolved_paths == ()
    assert resolution.divergence_possible is False
    assert resolution.recommended_target == tree


@pytest.mark.parametrize('tree', _NON_BUNDLE_TEST_TREES)
def test_a_non_bundle_test_tree_is_unresolved_until_it_is_registered(tree):
    """NEGATIVE CONTROL: the same path resolves nothing against the bundle-only set.

    Proves the confident target above comes from the tree being REGISTERED, not
    from the derivation returning segment 1 of any ``test/`` path verbatim.
    """
    path = f'test/{tree}/test_something.py'

    resolution = resolve_test_scope([path], _GLOBS, _REGISTERED_MODULES)

    assert resolution.scoped_modules == ()
    assert resolution.unresolved_paths == (path,)
    assert resolution.divergence_possible is True
    assert resolution.recommended_target is None


def test_the_shared_helper_home_stays_unresolved_when_test_trees_are_registered():
    """Registering test trees does not make ``test/_shared/`` a target.

    ``_shared`` is not in the registered set, so the path is still unresolved,
    still shared infrastructure, and still forces the whole tree.
    """
    resolution = resolve_test_scope([_SHARED_TEST_HELPER], _GLOBS, _REGISTERED_TARGETS)

    assert resolution.scoped_modules == ()
    assert resolution.unresolved_paths == (_SHARED_TEST_HELPER,)
    assert resolution.divergence_possible is True
    assert resolution.recommended_target is None


def test_a_non_bundle_test_tree_beside_a_bundle_spans_two_targets():
    """A footprint in a non-bundle tree and in a bundle is a two-target span."""
    footprint = ['test/marketplace/test_something.py', _PROD_PLAN_MARSHALL]

    resolution = resolve_test_scope(footprint, _GLOBS, _REGISTERED_TARGETS)

    assert resolution.scoped_modules == ('marketplace', 'plan-marshall')
    assert resolution.divergence_possible is True
    assert resolution.recommended_target is None


# =============================================================================
# The declared source-to-test mapping: source outside the bundles
# =============================================================================


class DeclaredMappingFixture(NamedTuple):
    """One footprint-plus-registered-set fixture for the declared mapping.

    Shared, by import, between the pure-function cases here and the
    ``resolve-test-scope`` handler cases in ``test_pyproject_build.py``, so both
    levels assert on the same inputs and cannot drift apart.

    Attributes:
        mapped_path: A source path the declared mapping covers.
        mapped_target: The test target that path resolves to.
        unmapped_path: A source path no declared mapping covers.
        registered: The registered-target set both paths are resolved against.
    """

    mapped_path: str
    mapped_target: str
    unmapped_path: str
    registered: frozenset[str]


DECLARED_MAPPING_FIXTURE = DeclaredMappingFixture(
    mapped_path='marketplace/targets/sync.py',
    mapped_target='marketplace',
    unmapped_path='tools/x.py',
    registered=_REGISTERED_TARGETS,
)


def test_a_mapped_source_path_resolves_its_declared_test_target():
    """A source path the declared mapping covers resolves confidently."""
    fixture = DECLARED_MAPPING_FIXTURE

    resolution = resolve_test_scope([fixture.mapped_path], _GLOBS, fixture.registered)

    assert resolution.scoped_modules == (fixture.mapped_target,)
    assert resolution.unresolved_paths == ()
    assert resolution.divergence_possible is False
    assert resolution.recommended_target == fixture.mapped_target


def test_an_unmapped_source_path_stays_unresolved():
    """NEGATIVE CONTROL: a source path with no declared mapping fails closed.

    Proves the confident target above comes from the declared entry, not from
    the fallback branch resolving every out-of-tree path to something.
    """
    fixture = DECLARED_MAPPING_FIXTURE

    resolution = resolve_test_scope([fixture.unmapped_path], _GLOBS, fixture.registered)

    assert resolution.scoped_modules == ()
    assert resolution.unresolved_paths == (fixture.unmapped_path,)
    assert resolution.divergence_possible is True
    assert resolution.recommended_target is None


def test_a_mapped_target_is_returned_only_when_it_is_registered():
    """The registered-name guard applies to a mapped name too.

    The same mapped path against a set that lacks its target resolves nothing,
    so a mapping entry naming a target no tree carries cannot invent one.
    """
    fixture = DECLARED_MAPPING_FIXTURE
    without_target = fixture.registered - {fixture.mapped_target}

    resolution = resolve_test_scope([fixture.mapped_path], _GLOBS, without_target)

    assert resolution.scoped_modules == ()
    assert resolution.unresolved_paths == (fixture.mapped_path,)
    assert resolution.divergence_possible is True
    assert resolution.recommended_target is None


def test_the_longest_declared_prefix_wins(monkeypatch):
    """Two overlapping entries resolve by prefix length, not declaration order.

    The broader entry is declared FIRST, so a first-match lookup would return
    its target for the nested path.
    """
    monkeypatch.setattr(
        _test_scope_divergence,
        'SOURCE_TO_TEST_TARGET',
        (('marketplace/targets/', 'marketplace'), ('marketplace/targets/nested/', 'default')),
    )

    assert _module_for_path('marketplace/targets/nested/x.py', _REGISTERED_TARGETS) == 'default'
    assert _module_for_path('marketplace/targets/x.py', _REGISTERED_TARGETS) == 'marketplace'


def test_a_declared_prefix_matches_a_directory_not_a_name_prefix():
    """A sibling whose name merely starts like a mapped directory is not mapped."""
    assert _module_for_path('marketplace/targets_other/x.py', _REGISTERED_TARGETS) is None


# =============================================================================
# Narrow units: module-tests targets narrower than the module
# =============================================================================


class NarrowUnitCase(NamedTuple):
    """One narrow-unit footprint with the two lists it must read.

    Shared, by import, with the ``resolve-test-scope`` handler cases in
    ``test_pyproject_build.py``.

    Attributes:
        footprint: The changed paths.
        narrow_units: The expected ``narrow_units``, in sorted order.
        narrow_units_unresolved: The expected ``narrow_units_unresolved``, in
            footprint order.
    """

    footprint: tuple[str, ...]
    narrow_units: tuple[str, ...]
    narrow_units_unresolved: tuple[str, ...]


#: The existing test directories the narrow-unit cases are resolved against.
#: ``no-test-dir`` is deliberately absent: it is the skill with no test directory.
NARROW_UNIT_TEST_DIRECTORIES = frozenset(
    {
        'plan-marshall/build-server',
        'plan-marshall/manage-tasks',
        'plan-marshall/manage-status',
    }
)

_SKILL_BUILD_SERVER = 'marketplace/bundles/plan-marshall/skills/build-server/scripts/server.py'
_SKILL_BUILD_SERVER_DOC = 'marketplace/bundles/plan-marshall/skills/build-server/SKILL.md'
_SKILL_MANAGE_TASKS = 'marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/manage-tasks.py'
_SKILL_MANAGE_STATUS = 'marketplace/bundles/plan-marshall/skills/manage-status/scripts/manage_status.py'
_SKILL_WITHOUT_TEST_DIR = 'marketplace/bundles/plan-marshall/skills/no-test-dir/scripts/x.py'
_CHANGED_TEST_FILE = 'test/plan-marshall/build-server/test_server.py'

#: The footprints the deliverable names, keyed by case id.
NARROW_UNIT_CASES: dict[str, NarrowUnitCase] = {
    'one_skill': NarrowUnitCase(
        footprint=(_SKILL_BUILD_SERVER, _SKILL_BUILD_SERVER_DOC),
        narrow_units=('plan-marshall/build-server',),
        narrow_units_unresolved=(),
    ),
    'three_skills': NarrowUnitCase(
        footprint=(_SKILL_MANAGE_TASKS, _SKILL_BUILD_SERVER, _SKILL_MANAGE_STATUS),
        narrow_units=(
            'plan-marshall/build-server',
            'plan-marshall/manage-status',
            'plan-marshall/manage-tasks',
        ),
        narrow_units_unresolved=(),
    ),
    'skill_without_test_directory': NarrowUnitCase(
        footprint=(_SKILL_WITHOUT_TEST_DIR, _SKILL_BUILD_SERVER),
        narrow_units=('plan-marshall/build-server',),
        narrow_units_unresolved=(_SKILL_WITHOUT_TEST_DIR,),
    ),
    'changed_test_file': NarrowUnitCase(
        footprint=(_CHANGED_TEST_FILE,),
        narrow_units=('plan-marshall/build-server/test_server.py',),
        narrow_units_unresolved=(),
    ),
}

_NARROW_UNIT_PARAMS = [pytest.param(case, id=case_id) for case_id, case in NARROW_UNIT_CASES.items()]


@pytest.mark.parametrize('case', _NARROW_UNIT_PARAMS)
def test_narrow_units_for_a_single_module_footprint(case):
    """Each named footprint reads its narrow units and names what contributed none."""
    resolution = resolve_test_scope(
        list(case.footprint),
        _GLOBS,
        _REGISTERED_MODULES,
        test_directories=NARROW_UNIT_TEST_DIRECTORIES,
    )

    assert resolution.narrow_units == case.narrow_units
    assert resolution.narrow_units_unresolved == case.narrow_units_unresolved


@pytest.mark.parametrize('case', _NARROW_UNIT_PARAMS)
def test_supplying_the_directory_set_changes_no_other_field(case):
    """The module-level answer is identical with and without the directory set.

    The call WITHOUT the parameter is the pre-change call, so comparing the two
    pins "identical before and after" directly instead of against a copied
    expectation. The matched control is the case above: the same supplied set
    does produce narrow units, so equality here is not two no-op calls agreeing.
    """
    without = resolve_test_scope(list(case.footprint), _GLOBS, _REGISTERED_MODULES)
    supplied = resolve_test_scope(
        list(case.footprint),
        _GLOBS,
        _REGISTERED_MODULES,
        test_directories=NARROW_UNIT_TEST_DIRECTORIES,
    )

    assert supplied.recommended_target == without.recommended_target == 'plan-marshall'
    assert supplied.scoped_modules == without.scoped_modules
    assert supplied.divergence_possible is without.divergence_possible
    assert supplied.unresolved_paths == without.unresolved_paths


def test_a_call_without_the_directory_set_reads_both_narrow_lists_empty():
    """The default means "no set supplied": no narrow list, every other field as before.

    The expected values are the ones the same call returned before the two
    fields existed (see ``test_single_module_footprint_is_the_positive_control``,
    which asserts them on this footprint and was not edited).
    """
    resolution = resolve_test_scope([_PROD_PLAN_MARSHALL, _DOC], _GLOBS, _REGISTERED_MODULES)

    assert resolution.narrow_units == ()
    assert resolution.narrow_units_unresolved == ()
    assert resolution.scoped_modules == ('plan-marshall',)
    assert resolution.divergence_possible is False
    assert resolution.recommended_target == 'plan-marshall'
    assert resolution.unresolved_paths == ()


def test_an_empty_directory_set_is_not_the_same_as_none():
    """A supplied-but-empty set names every skill path instead of staying silent.

    ``None`` says nobody looked; an empty set says somebody looked and no test
    directory exists. Collapsing the two would report an unenumerable tree as
    "nothing to narrow" with no path named.
    """
    resolution = resolve_test_scope([_SKILL_BUILD_SERVER], _GLOBS, _REGISTERED_MODULES, test_directories=frozenset())

    assert resolution.narrow_units == ()
    assert resolution.narrow_units_unresolved == (_SKILL_BUILD_SERVER,)


@pytest.mark.parametrize(
    'footprint',
    [
        pytest.param([_PROD_PLAN_MARSHALL, _PROD_PM_PYTHON], id='two_modules'),
        pytest.param([_UNMAPPED_DOC], id='no_module'),
        pytest.param([], id='empty_footprint'),
    ],
)
def test_a_footprint_that_is_not_single_module_reads_no_narrow_list(footprint):
    """Both lists are empty unless the footprint resolves to exactly one module."""
    directories = NARROW_UNIT_TEST_DIRECTORIES | {'plan-marshall/foo', 'pm-dev-python/baz'}

    resolution = resolve_test_scope(footprint, _GLOBS, _REGISTERED_MODULES, test_directories=directories)

    assert resolution.narrow_units == ()
    assert resolution.narrow_units_unresolved == ()


def test_narrow_units_survive_a_whole_tree_verdict_for_one_module():
    """One module plus a path owning none: whole tree warranted, narrow unit still named.

    The narrow unit is a faster first signal, not a verdict. The whole-tree
    answer is unchanged, and the path that owns no module is named in BOTH
    disclosure lists - it is covered by neither a scoped nor a narrow run.
    """
    footprint = [_SKILL_BUILD_SERVER, _UNMAPPED_DOC]

    resolution = resolve_test_scope(
        footprint, _GLOBS, _REGISTERED_MODULES, test_directories=NARROW_UNIT_TEST_DIRECTORIES
    )

    assert resolution.divergence_possible is True
    assert resolution.recommended_target is None
    assert resolution.unresolved_paths == (_UNMAPPED_DOC,)
    assert resolution.narrow_units == ('plan-marshall/build-server',)
    assert resolution.narrow_units_unresolved == (_UNMAPPED_DOC,)


@pytest.mark.parametrize(
    ('path', 'reason'),
    [
        pytest.param(
            'marketplace/bundles/plan-marshall/.claude-plugin/plugin.json',
            'the path is not inside a skill',
            id='bundle_file_outside_skills',
        ),
        pytest.param(
            'test/plan-marshall/build-server/conftest.py',
            'a conftest is not a test file',
            id='conftest',
        ),
        pytest.param(
            'test/plan-marshall/build-server/_fixtures.py',
            'a helper is not a test file',
            id='test_helper',
        ),
    ],
)
def test_paths_that_contribute_no_narrow_unit_are_named(path, reason):
    """NEGATIVE CONTROLS: a path of no narrow shape is named, never dropped."""
    resolution = resolve_test_scope(
        [path, _SKILL_BUILD_SERVER], _GLOBS, _REGISTERED_MODULES, test_directories=NARROW_UNIT_TEST_DIRECTORIES
    )

    assert resolution.narrow_units == ('plan-marshall/build-server',)
    assert resolution.narrow_units_unresolved == (path,), f'{path!r} was not named although {reason}'


def test_a_test_file_outside_the_resolved_module_is_not_a_narrow_unit():
    """A changed test file under an unregistered tree is no unit of another module."""
    foreign_test = 'test/not-a-real-bundle/test_y.py'

    resolution = resolve_test_scope(
        [_SKILL_BUILD_SERVER, foreign_test],
        _GLOBS,
        _REGISTERED_MODULES,
        test_directories=NARROW_UNIT_TEST_DIRECTORIES,
    )

    assert resolution.scoped_modules == ('plan-marshall',)
    assert resolution.narrow_units == ('plan-marshall/build-server',)
    assert resolution.narrow_units_unresolved == (foreign_test,)


# =============================================================================
# Cross-check: the two independently-declared root sets must agree
# =============================================================================


def test_test_roots_agree_with_the_build_extension_declaration():
    """The pure module's root set equals the Python build extension's.

    The two are deliberately separate declarations -- this module's purity
    contract forbids importing a build extension, and the dependency would run
    the wrong way -- so nothing structural keeps them equal. This cross-check is
    what does: it reads both real definitions and pins them identical, so a root
    added to one and not the other is a red here rather than a silent asymmetry
    between module-ownership derivation and the Axis-B build_map tables.

    The extension is loaded by explicit file path, never ``import extension``:
    all four build skills ship an ``extension.py`` sharing that module basename,
    so a bare import resolves to whichever sys.path entry happens to come first.
    """
    _EXTENSION_TEST_ROOTS = _load_pyproject_extension()._TEST_ROOTS

    assert set(_TEST_ROOTS) == set(_EXTENSION_TEST_ROOTS), (
        f'_test_scope_divergence declares {sorted(_TEST_ROOTS)!r} while the Python build '
        f'extension declares {sorted(_EXTENSION_TEST_ROOTS)!r}. One seam now recognises a '
        'test root the other does not -- exactly the drift this pair was reconciled to remove.'
    )
    assert _TEST_ROOTS, 'the root set is empty, so this cross-check compares nothing.'


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
    # ``caught`` mirrors ``divergent`` - the whole-tree route is what surfaces it.
    assert verdict.caught is expected_divergent
