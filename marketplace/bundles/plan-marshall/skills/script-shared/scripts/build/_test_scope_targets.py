# SPDX-License-Identifier: FSL-1.1-ALv2
"""The single registered-target derivation for test-scope resolution.

A *registered target* is a name a scoped ``module-tests`` run may be pointed at.
Two populations qualify, and this module unites them:

* **Bundles** - every bundle the marketplace carries, enumerated through the
  existing ``marketplace_bundles.find_bundles()`` + ``extract_bundle_name()``
  seam.
* **Test trees holding tests** - every top-level directory under a test root
  that holds at least one ``test_*.py`` at any depth and whose name does not
  start with ``_``. Such a tree need not belong to any bundle: a ``test/{name}``
  tree is a returnable target even when no ``marketplace/bundles/{name}``
  exists.

The second population mirrors the path-acceptance rule of the ``module-tests``
build command (``build.py``'s ``require_test_path``), which resolves its
positional argument to ``test/{name}`` and requires only that the directory
exists. It does NOT mirror ``compile``, ``quality-gate``, ``coverage`` or
``verify``, which resolve the same argument to a bundle directory - so a
non-bundle test tree is a valid target for ``module-tests`` ONLY.

The walk ranges over every root the pure derivation recognises (``test/`` and
its ``tests/`` sibling), which is one root wider than ``build.py`` runs. The
width is deliberate: a name the pure half can derive must be checkable here.
A target registered from a root ``build.py`` does not run is refused by
``require_test_path`` with a named error, never run against the wrong tree.

Beside the registered targets this module enumerates the second-level test
directories (:func:`resolve_test_directories`): the existing ``{tree}/{directory}``
names the pure half needs in order to return a narrow unit only for a skill that
actually has a test directory.

This module performs I/O (a directory walk) on purpose. It is the I/O half of
the pair whose pure half is ``_test_scope_divergence``: that module receives the
set computed here as an argument and never reads the filesystem itself.
"""

from __future__ import annotations

from pathlib import Path

from _test_scope_divergence import _TEST_ROOTS
from marketplace_bundles import extract_bundle_name, find_bundles
from marketplace_paths import find_marketplace_path

#: The filename glob that makes a directory a test tree *holding tests*. A tree
#: of fixtures or helpers with no ``test_*.py`` is not a target: a scoped run
#: pointed at it would collect nothing.
_TEST_FILE_GLOB = 'test_*.py'

#: Name prefix that excludes a top-level test directory from the target set.
#: It covers the bundle-neutral helper home ``_shared`` and ``__pycache__`` -
#: neither of which is a suite a scoped run should target.
_EXCLUDED_NAME_PREFIX = '_'


def _holds_tests(directory: Path) -> bool:
    """Return True when ``directory`` holds at least one ``test_*.py`` at any depth."""
    return next(directory.rglob(_TEST_FILE_GLOB), None) is not None


def _test_tree_names(project_root: Path) -> set[str]:
    """Return the top-level directory names under each test root that hold tests.

    Ranges over every entry of ``_test_scope_divergence._TEST_ROOTS`` so the set
    of roots that can CONTRIBUTE a target here is exactly the set of roots the
    pure derivation can DERIVE a candidate name from. A test root that does not
    exist contributes nothing.
    """
    names: set[str] = set()
    for root in _TEST_ROOTS:
        root_dir = project_root / root
        if not root_dir.is_dir():
            continue
        for child in root_dir.iterdir():
            if child.name.startswith(_EXCLUDED_NAME_PREFIX) or not child.is_dir():
                continue
            if _holds_tests(child):
                names.add(child.name)
    return names


def resolve_registered_targets(project_dir: str | None) -> frozenset[str]:
    """Enumerate the registered targets for ``project_dir``'s marketplace.

    The result is the union of the bundle names and the names of the top-level
    test trees that hold tests (see the module docstring for both populations).
    The marketplace root is resolved by ``find_marketplace_path()`` from
    ``project_dir``; the test roots are looked up beside it, under the checkout
    that carries ``marketplace/bundles``.

    Returns an EMPTY frozenset in exactly two cases: the marketplace root does
    not resolve (``find_marketplace_path`` returns ``None``), or the walk raises
    ``OSError`` (an unreadable or vanished directory). The caller reads
    emptiness as "targets not resolvable" and fails toward the whole tree
    rather than silently disabling the registered-target check.

    The guard is deliberately no wider than that. Every name here is derived
    from a directory name, and the filesystem is touched only through calls
    whose failure mode is ``OSError``, so ``OSError`` is the walk's only
    expected failure. Anything else escapes as a crash, which is loud rather
    than a false "resolvable"; do NOT widen the ``except`` to a bare
    ``Exception``, which would relabel an unforeseen bug as a routine-looking
    empty set.

    Args:
        project_dir: The checkout to enumerate, or ``None`` to resolve the
            marketplace by ``find_marketplace_path``'s own fallback order.
    """
    try:
        bundles_root = find_marketplace_path(Path(project_dir) if project_dir else None)
        if bundles_root is None:
            return frozenset()
        bundle_names = {extract_bundle_name(bundle_dir) for bundle_dir in find_bundles(bundles_root)}
        # ``bundles_root`` is ``{checkout}/marketplace/bundles``; the test roots
        # live at the checkout root, two levels up.
        return frozenset(bundle_names | _test_tree_names(bundles_root.parent.parent))
    except OSError:
        return frozenset()


def _test_directory_names(project_root: Path) -> set[str]:
    """Return the second-level test directories that hold tests, as ``{tree}/{directory}``.

    One level below :func:`_test_tree_names`: for every top-level tree under a
    test root, each child directory that holds at least one ``test_*.py`` at any
    depth. The same underscore exclusion applies at both levels, so neither a
    helper home nor a ``__pycache__`` is ever a unit.
    """
    names: set[str] = set()
    for root in _TEST_ROOTS:
        root_dir = project_root / root
        if not root_dir.is_dir():
            continue
        for tree in root_dir.iterdir():
            if tree.name.startswith(_EXCLUDED_NAME_PREFIX) or not tree.is_dir():
                continue
            for child in tree.iterdir():
                if child.name.startswith(_EXCLUDED_NAME_PREFIX) or not child.is_dir():
                    continue
                if _holds_tests(child):
                    names.add(f'{tree.name}/{child.name}')
    return names


def resolve_test_directories(project_dir: str | None) -> frozenset[str]:
    """Enumerate the existing second-level test directories for ``project_dir``.

    Each name is relative to its test root - ``{tree}/{directory}``, the form a
    ``module-tests`` run accepts as a narrow target. This is the set the pure
    resolver needs to tell a skill that HAS a test directory from one that does
    not, without reading the filesystem itself.

    Returns an EMPTY frozenset in the same two cases as
    :func:`resolve_registered_targets`, for the same reason and under the same
    deliberately narrow ``OSError`` guard. The pure resolver reads an empty set
    as "no directory exists", so every skill path it is asked about is named in
    ``narrow_units_unresolved`` rather than turned into a unit nothing backs.

    Args:
        project_dir: The checkout to enumerate, or ``None`` to resolve the
            marketplace by ``find_marketplace_path``'s own fallback order.
    """
    try:
        bundles_root = find_marketplace_path(Path(project_dir) if project_dir else None)
        if bundles_root is None:
            return frozenset()
        return frozenset(_test_directory_names(bundles_root.parent.parent))
    except OSError:
        return frozenset()
