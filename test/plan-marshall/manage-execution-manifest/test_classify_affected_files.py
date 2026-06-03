#!/usr/bin/env python3
"""Tests for the per-domain extension aggregator in manage-execution-manifest.

The legacy ``_classify_affected_files`` helper has been replaced by
``_classify_paths_via_extensions``, which dispatches to every registered
ExtensionBase.classify_paths() and resolves overlaps via longest-glob-wins.
These tests use the ``FakeExtension`` fixture from
``_execution_manifest_fixtures.py`` to exercise the aggregator's six-bucket
vocabulary, overlap resolution, and ``unknown`` branch in isolation from
real extension loading.

The six plan-wide bucket values:

- ``production_only`` — all claimed paths are production
- ``test_only`` — all claimed paths are test
- ``documentation_only`` — all claimed paths are documentation
- ``mixed_code`` — production AND test, no documentation
- ``mixed_with_docs`` — production/test AND documentation
- ``unknown`` — at least one path is unclaimed
"""

import importlib.util
from pathlib import Path

# Import the FakeExtension fixture explicitly (per the _fixtures.py
# convention — sibling conftest.py is banned). The fixture basename is
# bundle-unique to avoid a collision in the plan-marshall test namespace.
_FIXTURES_PATH = Path(__file__).parent / '_execution_manifest_fixtures.py'
_fixtures_spec = importlib.util.spec_from_file_location(
    '_execution_manifest_fixtures_classifier_tests', _FIXTURES_PATH
)
assert _fixtures_spec is not None and _fixtures_spec.loader is not None
_fixtures_mod = importlib.util.module_from_spec(_fixtures_spec)
_fixtures_spec.loader.exec_module(_fixtures_mod)
FakeExtension = _fixtures_mod.FakeExtension
fake_python_extension = _fixtures_mod.fake_python_extension
fake_documentation_extension = _fixtures_mod.fake_documentation_extension
fake_plugin_dev_extension = _fixtures_mod.fake_plugin_dev_extension

# Load the aggregator under test.
_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-execution-manifest'
    / 'scripts'
)
_manifest_spec = importlib.util.spec_from_file_location(
    '_manifest_classifier_tests', _SCRIPTS_DIR / 'manage-execution-manifest.py'
)
assert _manifest_spec is not None and _manifest_spec.loader is not None
_manifest_mod = importlib.util.module_from_spec(_manifest_spec)
_manifest_spec.loader.exec_module(_manifest_mod)
_classify = _manifest_mod._classify_paths_via_extensions


# =============================================================================
# Empty input
# =============================================================================


def test_empty_paths_returns_documentation_only():
    bucket, unclaimed = _classify([], extensions=[])
    assert bucket == 'documentation_only'
    assert unclaimed == []


# =============================================================================
# Each of the six buckets via the fake fixture
# =============================================================================


def test_production_only_bucket_via_fakes():
    py = fake_python_extension(production=['scripts/foo.py'])
    bucket, _ = _classify(['scripts/foo.py'], extensions=[py])
    assert bucket == 'production_only'


def test_test_only_bucket_via_fakes():
    py = fake_python_extension(tests=['test/foo_test.py'])
    bucket, _ = _classify(['test/foo_test.py'], extensions=[py])
    assert bucket == 'test_only'


def test_documentation_only_bucket_via_fakes():
    docs = fake_documentation_extension(documentation=['README.md'])
    bucket, _ = _classify(['README.md'], extensions=[docs])
    assert bucket == 'documentation_only'


def test_mixed_code_bucket_via_fakes():
    py = fake_python_extension(
        production=['scripts/foo.py'],
        tests=['test/foo_test.py'],
    )
    bucket, _ = _classify(['scripts/foo.py', 'test/foo_test.py'], extensions=[py])
    assert bucket == 'mixed_code'


def test_mixed_with_docs_bucket_via_fakes():
    """mixed_with_docs requires production/test AND documentation."""
    py = fake_python_extension(production=['scripts/foo.py'])
    docs = fake_documentation_extension(documentation=['README.md'])
    bucket, _ = _classify(['scripts/foo.py', 'README.md'], extensions=[py, docs])
    assert bucket == 'mixed_with_docs'


def test_unknown_bucket_via_fakes():
    py = fake_python_extension(production=['scripts/foo.py'])
    bucket, unclaimed = _classify(
        ['scripts/foo.py', 'mystery.xyz'], extensions=[py]
    )
    assert bucket == 'unknown'
    assert unclaimed == ['mystery.xyz']


# =============================================================================
# mixed_code vs mixed_with_docs discrimination
# =============================================================================


def test_mixed_code_does_not_include_documentation():
    """mixed_code must NOT contain documentation paths — adding any docs path
    upgrades the bucket to mixed_with_docs."""
    py = fake_python_extension(
        production=['scripts/foo.py'], tests=['test/foo_test.py']
    )
    bucket_no_docs, _ = _classify(
        ['scripts/foo.py', 'test/foo_test.py'], extensions=[py]
    )
    assert bucket_no_docs == 'mixed_code'

    docs = fake_documentation_extension(documentation=['README.md'])
    bucket_with_docs, _ = _classify(
        ['scripts/foo.py', 'test/foo_test.py', 'README.md'], extensions=[py, docs]
    )
    assert bucket_with_docs == 'mixed_with_docs'


def test_mixed_with_docs_when_only_test_and_docs():
    """mixed_with_docs requires production OR test, plus documentation."""
    py = fake_python_extension(tests=['test/foo_test.py'])
    docs = fake_documentation_extension(documentation=['README.md'])
    bucket, _ = _classify(['test/foo_test.py', 'README.md'], extensions=[py, docs])
    assert bucket == 'mixed_with_docs'


# =============================================================================
# Overlap resolution: longest-glob-wins
# =============================================================================


def test_plugin_dev_wins_marketplace_skill_md_via_specificity():
    """When both pm-documents and pm-plugin-development claim the same
    marketplace skill markdown path, pm-plugin-development's higher
    specificity wins and the path is routed under documentation."""
    path = 'marketplace/bundles/foo/skills/bar/SKILL.md'
    docs = fake_documentation_extension(documentation=[path])
    plugin = fake_plugin_dev_extension(documentation=[path])
    bucket, unclaimed = _classify([path], extensions=[docs, plugin])
    assert bucket == 'documentation_only'
    assert unclaimed == []


def test_alphabetical_tiebreak_on_equal_specificity():
    """Equal specificity → alphabetically earlier domain key wins."""
    path = 'foo.bar'
    a = FakeExtension(
        'alpha',
        claims={'production': [path], 'test': [], 'documentation': [], 'config': []},
        specificity={(path, 'production'): 2},
    )
    z = FakeExtension(
        'zulu',
        claims={'production': [], 'test': [], 'documentation': [path], 'config': []},
        specificity={(path, 'documentation'): 2},
    )
    bucket, _ = _classify([path], extensions=[a, z])
    # alpha wins → production → production_only
    assert bucket == 'production_only'


def test_overlap_resolution_is_extension_order_independent():
    """Aggregator output must NOT depend on extension iteration order."""
    path = 'marketplace/bundles/foo/skills/bar/SKILL.md'
    docs = fake_documentation_extension(documentation=[path])
    plugin = fake_plugin_dev_extension(documentation=[path])
    bucket_docs_first, _ = _classify([path], extensions=[docs, plugin])
    bucket_plugin_first, _ = _classify([path], extensions=[plugin, docs])
    assert bucket_docs_first == bucket_plugin_first == 'documentation_only'


# =============================================================================
# Unknown bucket — at least one unclaimed path forces the entire plan bucket
# =============================================================================


def test_single_unclaimed_path_forces_unknown_for_entire_plan():
    """A single unclaimed path upgrades the bucket to unknown regardless of
    how many paths are otherwise claimed."""
    py = fake_python_extension(production=['scripts/a.py', 'scripts/b.py', 'scripts/c.py'])
    bucket, unclaimed = _classify(
        ['scripts/a.py', 'scripts/b.py', 'scripts/c.py', 'mystery.xyz'],
        extensions=[py],
    )
    assert bucket == 'unknown'
    assert unclaimed == ['mystery.xyz']


def test_no_extensions_with_paths_returns_unknown():
    bucket, unclaimed = _classify(['scripts/foo.py'], extensions=[])
    assert bucket == 'unknown'
    assert unclaimed == ['scripts/foo.py']


# =============================================================================
# Config role does NOT influence the plan-wide bucket
# =============================================================================


def test_config_only_collapses_to_documentation_only():
    py = fake_python_extension(config=['pyproject.toml'])
    bucket, _ = _classify(['pyproject.toml'], extensions=[py])
    assert bucket == 'documentation_only'


def test_production_plus_config_is_production_only():
    py = fake_python_extension(production=['scripts/foo.py'], config=['pyproject.toml'])
    bucket, _ = _classify(['scripts/foo.py', 'pyproject.toml'], extensions=[py])
    assert bucket == 'production_only'
