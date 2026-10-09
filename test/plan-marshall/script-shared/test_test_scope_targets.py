#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for ``_test_scope_targets`` - the registered-target derivation.

A registered target is a name a scoped ``module-tests`` run may be pointed at:
a bundle, or a top-level test tree that holds tests. The cases below build a
synthetic checkout under the test's temporary directory and assert WHICH names
are registered, so the derivation is pinned independently of whatever trees this
repository happens to carry. One further case runs the real resolver against
this repository, so the synthetic cases cannot agree with a derivation that no
longer finds a marketplace at all.

In the synthetic cases the marketplace-root resolution is held at the synthetic
``marketplace/bundles`` directory. That seam decides only WHERE the checkout
is; the bundle walk and the test-tree walk both run for real over the tree
built here.
"""

from pathlib import Path

# Cross-skill import - PYTHONPATH is configured by the root conftest.
import _test_scope_targets as targets
import pytest

from conftest import PROJECT_ROOT

# ---------------------------------------------------------------------------
# Synthetic checkout
# ---------------------------------------------------------------------------


def _add_bundle(root: Path, name: str) -> None:
    """Create a bundle directory the marketplace walk recognises."""
    manifest_dir = root / 'marketplace' / 'bundles' / name / '.claude-plugin'
    manifest_dir.mkdir(parents=True)
    (manifest_dir / 'plugin.json').write_text('{}', encoding='utf-8')


def _add_file(root: Path, relative: str) -> None:
    """Create ``relative`` under ``root``, with its parent directories."""
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('', encoding='utf-8')


@pytest.fixture
def checkout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A synthetic checkout whose marketplace root resolves to itself."""
    bundles_root = tmp_path / 'marketplace' / 'bundles'
    bundles_root.mkdir(parents=True)
    monkeypatch.setattr(targets, 'find_marketplace_path', lambda _project_dir: bundles_root)
    return tmp_path


# ---------------------------------------------------------------------------
# Which names are registered
# ---------------------------------------------------------------------------


def test_bundles_and_test_trees_holding_tests_are_registered(checkout):
    """The set is the bundles united with the test trees that hold tests."""
    # A bundle with a test tree of its own, and a bundle with none.
    _add_bundle(checkout, 'alpha')
    _add_file(checkout, 'test/alpha/some-skill/test_alpha.py')
    _add_bundle(checkout, 'beta')
    # A non-bundle tree holding tests, with its only test file several levels down.
    _add_file(checkout, 'test/standalone/nested/deeper/test_standalone.py')
    # The bundle-neutral helper home: excluded by name even though it holds a
    # file that matches the test glob.
    _add_file(checkout, 'test/_shared/_helpers.py')
    _add_file(checkout, 'test/_shared/test_helper_selfcheck.py')
    # A directory with no tests: fixtures and a helper, nothing to collect.
    _add_file(checkout, 'test/fixtures-only/data.json')
    _add_file(checkout, 'test/fixtures-only/helper.py')

    registered = targets.resolve_registered_targets(str(checkout))

    assert registered == frozenset({'alpha', 'beta', 'standalone'})


def test_a_non_bundle_test_tree_is_registered_without_any_bundle(checkout):
    """A test tree needs no bundle of the same name to be a target."""
    _add_file(checkout, 'test/standalone/test_standalone.py')

    assert targets.resolve_registered_targets(str(checkout)) == frozenset({'standalone'})


@pytest.mark.parametrize(
    ('relative', 'reason'),
    [
        pytest.param('test/_shared/test_x.py', 'the helper home starts with an underscore', id='shared_helper_home'),
        pytest.param('test/__pycache__/test_x.py', 'a cache directory starts with an underscore', id='pycache'),
        pytest.param('test/no-tests/conftest.py', 'a conftest alone is not a test file', id='conftest_only'),
        pytest.param('test/no-tests/fixture_test.py', 'the name does not start with test_', id='suffix_named_file'),
        pytest.param('test/test_top_level.py', 'a file at the test root is not a tree', id='file_at_the_root'),
    ],
)
def test_names_that_are_not_registered(checkout, relative, reason):
    """NEGATIVE CONTROLS: each of these contributes no target.

    Matched against the positive cases above - the same walk registers
    ``standalone`` from one ``test_*.py``, so an empty result here comes from
    the rule under test and not from a walk that finds nothing at all.
    """
    _add_file(checkout, relative)
    _add_file(checkout, 'test/standalone/test_standalone.py')

    registered = targets.resolve_registered_targets(str(checkout))

    assert registered == frozenset({'standalone'}), f'{relative!r} registered a target although {reason}'


def test_both_test_roots_contribute(checkout):
    """The ``tests/`` sibling root contributes exactly as ``test/`` does."""
    _add_file(checkout, 'test/under-test/test_a.py')
    _add_file(checkout, 'tests/under-tests/test_b.py')

    assert targets.resolve_registered_targets(str(checkout)) == frozenset({'under-test', 'under-tests'})


def test_a_checkout_without_test_roots_registers_its_bundles_only(checkout):
    """A missing test root contributes nothing and is not an error."""
    _add_bundle(checkout, 'alpha')

    assert targets.resolve_registered_targets(str(checkout)) == frozenset({'alpha'})


# ---------------------------------------------------------------------------
# The two empty returns
# ---------------------------------------------------------------------------


def test_unresolvable_marketplace_root_registers_nothing(tmp_path, monkeypatch):
    """No marketplace root means no checkout to walk - the set is empty."""
    _add_file(tmp_path, 'test/standalone/test_standalone.py')
    monkeypatch.setattr(targets, 'find_marketplace_path', lambda _project_dir: None)

    assert targets.resolve_registered_targets(str(tmp_path)) == frozenset()


def test_a_walk_that_raises_oserror_registers_nothing(checkout, monkeypatch):
    """An unreadable directory empties the set instead of escaping as a crash."""
    _add_bundle(checkout, 'alpha')

    def _unreadable(_project_root):
        raise OSError('permission denied')

    monkeypatch.setattr(targets, '_test_tree_names', _unreadable)

    assert targets.resolve_registered_targets(str(checkout)) == frozenset()


def test_an_unforeseen_error_is_not_relabelled_as_an_empty_set(checkout, monkeypatch):
    """Only ``OSError`` is absorbed; anything else stays loud."""

    def _broken(_project_root):
        raise ValueError('a bug, not an unreadable directory')

    monkeypatch.setattr(targets, '_test_tree_names', _broken)

    with pytest.raises(ValueError, match='a bug'):
        targets.resolve_registered_targets(str(checkout))


# ---------------------------------------------------------------------------
# The real resolver, against this repository
# ---------------------------------------------------------------------------


def test_this_repository_registers_its_bundles_and_its_non_bundle_test_trees():
    """End to end, with nothing patched: bundles and non-bundle trees both appear."""
    registered = targets.resolve_registered_targets(str(PROJECT_ROOT))

    # Bundles.
    assert 'plan-marshall' in registered
    assert 'pm-dev-python' in registered
    # Test trees that belong to no bundle.
    for tree in (
        'default',
        'finalize-step-deploy-target',
        'finalize-step-sync-plugin-cache',
        'marketplace',
        'sync-harnesses',
    ):
        assert not (PROJECT_ROOT / 'marketplace' / 'bundles' / tree).exists(), (
            f'{tree!r} is a bundle now, so it no longer proves the non-bundle half of the derivation'
        )
        assert tree in registered, f'the non-bundle test tree {tree!r} is not a registered target'
    # The helper home is never a target.
    assert '_shared' not in registered
