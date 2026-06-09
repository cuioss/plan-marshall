#!/usr/bin/env python3
# ruff: noqa: I001, E402
"""Tests for the extension_discovery → tree-deriver bridge.

``derive_build_map_globs(project_root, extensions)`` bridges extension
discovery to the ``script-shared`` base-lib tree-deriver
(``derive_globs_from_tree``). Each registered extension declares a portable
``(suffix, role_heuristic)`` vocabulary via ``classify_globs()``; the bridge
hands the discovered extension modules to the deriver, which scans the real
``project_root`` tree and emits the concrete globs that cover EVERY matching
file. The build_map seed aggregator (``manage-config``) consumes this output.

Two flavours of coverage:

1. Synthetic-tree units — a small fixture tree plus stub extension modules,
   asserting the bridge's contract deterministically (no dependency on the
   live marketplace tree).
2. Real-tree regression — the bridge over the live worktree, asserting the 26
   previously-missed production ``.py`` files (every
   ``*/skills/plan-marshall-plugin/extension.py`` and every
   ``marketplace/targets/**/*.py``) are now covered by a derived production
   glob. This is the regression the build_map redesign exists to fix.
"""

from __future__ import annotations

import fnmatch

# conftest.py sets up the marketplace PYTHONPATH and exposes module loaders.
from conftest import (  # type: ignore[import-not-found]
    MARKETPLACE_ROOT,
    PROJECT_ROOT,
    load_script_module,
)

# The role-heuristic constants used to build stub vocabularies live in the
# script-shared extension module (already on sys.path via conftest).
from extension_base import (  # type: ignore[import-not-found]
    ROLE_HEURISTIC_CONFIG,
    ROLE_HEURISTIC_DOCUMENTATION,
    ROLE_HEURISTIC_PRODUCTION_BY_LOCATION,
    ROLE_HEURISTIC_TEST_BY_LOCATION,
    ExtensionBase,
)

_discovery = load_script_module('plan-marshall', 'extension-api', 'extension_discovery.py')


# =============================================================================
# Stub extensions and tree helpers
# =============================================================================


class _StubPythonExtension(ExtensionBase):
    """Minimal extension declaring the python .py production/test vocabulary."""

    def get_skill_domains(self) -> list[dict]:
        return [{'domain': {'key': 'python', 'name': 'P', 'description': 'd'}, 'profiles': {}}]

    def classify_globs(self) -> list[tuple[str, str]]:
        return [
            ('.py', ROLE_HEURISTIC_PRODUCTION_BY_LOCATION),
            ('.py', ROLE_HEURISTIC_TEST_BY_LOCATION),
            ('pyproject.toml', ROLE_HEURISTIC_CONFIG),
        ]


class _StubDocsExtension(ExtensionBase):
    """Minimal extension declaring a location-agnostic doc vocabulary."""

    def get_skill_domains(self) -> list[dict]:
        return [{'domain': {'key': 'documentation', 'name': 'D', 'description': 'd'}, 'profiles': {}}]

    def classify_globs(self) -> list[tuple[str, str]]:
        return [('.md', ROLE_HEURISTIC_DOCUMENTATION)]


def _write_tree(root, rel_paths: list[str]) -> None:
    for rel in rel_paths:
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text('')


def _matches_any(path: str, globs: list[str]) -> bool:
    return any(fnmatch.fnmatchcase(path, g) for g in globs)


def _prod_globs(entries: list[tuple[str, str]]) -> list[str]:
    return [glob for glob, role in entries if role == 'production']


# =============================================================================
# Synthetic-tree bridge units
# =============================================================================


def test_bridge_returns_empty_for_no_extensions(tmp_path):
    """An empty pre-discovered extension list yields an empty derivation."""
    _write_tree(tmp_path, ['scripts/foo.py'])
    result = _discovery.derive_build_map_globs(tmp_path, extensions=[])
    assert result == {}


def test_bridge_keys_result_by_domain_key(tmp_path):
    """The bridge returns a dict keyed by each extension's domain key."""
    _write_tree(tmp_path, ['pkg/mod.py', 'README.md'])
    extensions = [
        {'bundle': 'pm-dev-python', 'module': _StubPythonExtension()},
        {'bundle': 'pm-documents', 'module': _StubDocsExtension()},
    ]
    result = _discovery.derive_build_map_globs(tmp_path, extensions=extensions)
    assert set(result.keys()) == {'python', 'documentation'}


def test_bridge_covers_production_py_outside_scripts(tmp_path):
    """The bridge derives a production glob covering a non-scripts/ .py file."""
    _write_tree(tmp_path, ['pkg/sub/mod.py'])
    extensions = [{'bundle': 'pm-dev-python', 'module': _StubPythonExtension()}]
    result = _discovery.derive_build_map_globs(tmp_path, extensions=extensions)
    assert _matches_any('pkg/sub/mod.py', _prod_globs(result['python']))


def test_bridge_skips_entries_with_no_module(tmp_path):
    """Entries lacking a 'module' key are filtered before the deriver runs."""
    _write_tree(tmp_path, ['pkg/mod.py'])
    extensions = [
        {'bundle': 'broken'},  # no 'module'
        {'bundle': 'pm-dev-python', 'module': _StubPythonExtension()},
    ]
    result = _discovery.derive_build_map_globs(tmp_path, extensions=extensions)
    assert set(result.keys()) == {'python'}


def test_bridge_splits_production_and_test(tmp_path):
    """The .py vocabulary splits production vs test by the test-root predicate."""
    _write_tree(tmp_path, ['pkg/mod.py', 'test/pkg/test_mod.py'])
    extensions = [{'bundle': 'pm-dev-python', 'module': _StubPythonExtension()}]
    result = _discovery.derive_build_map_globs(tmp_path, extensions=extensions)
    entries = result['python']
    prod_globs = [glob for glob, role in entries if role == 'production']
    test_globs = [glob for glob, role in entries if role == 'test']
    assert _matches_any('pkg/mod.py', prod_globs)
    assert _matches_any('test/pkg/test_mod.py', test_globs)
    assert not _matches_any('test/pkg/test_mod.py', prod_globs)


def test_bridge_is_deterministic(tmp_path):
    """Two runs over the same tree return identical derivations."""
    _write_tree(tmp_path, ['z/mod.py', 'a/mod.py'])
    extensions = [{'bundle': 'pm-dev-python', 'module': _StubPythonExtension()}]
    first = _discovery.derive_build_map_globs(tmp_path, extensions=extensions)
    second = _discovery.derive_build_map_globs(tmp_path, extensions=extensions)
    assert first == second


# =============================================================================
# Real-tree regression: the 26 previously-missed production .py files
# =============================================================================
#
# The build_map redesign's central regression: the python domain's old
# scripts/-anchored static globs missed every production .py file living
# outside a scripts/ directory. There are exactly 26 such files in the
# marketplace tree:
#   - 10 × marketplace/bundles/<bundle>/skills/plan-marshall-plugin/extension.py
#   - 16 × marketplace/targets/**/*.py
# The tree-derived vocabulary now covers all of them because the deriver scans
# the real tree and emits a glob anchored at each file's parent directory.


def _real_production_py_outside_scripts() -> list[str]:
    """Enumerate every repo-relative production .py under marketplace/ that
    lives outside a scripts/ directory and outside any test root.

    Mirrors the set the deriver must cover: the extension.py files and the
    marketplace/targets/ package. Resolved from the live tree so the test
    tracks the real corpus rather than a frozen literal list.
    """
    paths: list[str] = []
    # MARKETPLACE_ROOT is marketplace/bundles/ — production .py outside scripts/.
    for py in MARKETPLACE_ROOT.rglob('*.py'):
        rel = py.relative_to(PROJECT_ROOT).as_posix()
        segments = rel.split('/')
        if '__pycache__' in segments or 'test' in segments or 'tests' in segments:
            continue
        if 'scripts' in segments:
            continue
        paths.append(rel)
    # marketplace/targets/ lives beside marketplace/bundles/ — its whole package
    # is production .py outside any scripts/ directory.
    targets_root = PROJECT_ROOT / 'marketplace' / 'targets'
    for py in targets_root.rglob('*.py'):
        rel = py.relative_to(PROJECT_ROOT).as_posix()
        if '__pycache__' in rel.split('/'):
            continue
        paths.append(rel)
    return sorted(set(paths))


def test_real_tree_corpus_has_the_expected_out_of_scripts_files():
    """The real-tree corpus contains the extension.py + targets/ production files.

    A guard on the corpus enumerator itself: if it ever returns an empty or
    suspiciously-small set, the coverage assertion below would pass vacuously.
    """
    corpus = _real_production_py_outside_scripts()
    extension_files = [p for p in corpus if p.endswith('/plan-marshall-plugin/extension.py')]
    targets_files = [p for p in corpus if p.startswith('marketplace/targets/')]
    # 10 production bundles each ship one extension.py; targets/ ships its package.
    assert len(extension_files) >= 10
    assert len(targets_files) >= 10
    assert len(corpus) >= 26


def test_real_tree_derivation_covers_every_out_of_scripts_production_py():
    """Every out-of-scripts production .py is covered by a derived production glob.

    The bridge discovers the live extensions and derives globs over the real
    worktree. The python domain's tree-derived production globs must match
    every extension.py and every marketplace/targets/**/*.py — the exact set
    the old static scripts/-anchored globs silently dropped.
    """
    derived = _discovery.derive_build_map_globs(PROJECT_ROOT)
    assert 'python' in derived, 'python domain must contribute tree-derived globs'
    prod_globs = _prod_globs(derived['python'])

    corpus = _real_production_py_outside_scripts()
    uncovered = [p for p in corpus if not _matches_any(p, prod_globs)]
    assert not uncovered, f'derived production globs miss {len(uncovered)} files: {uncovered[:10]}'


def test_real_tree_derivation_covers_a_sample_extension_py():
    """Spot-check: the python domain covers pm-dev-python's own extension.py."""
    derived = _discovery.derive_build_map_globs(PROJECT_ROOT)
    prod_globs = _prod_globs(derived['python'])
    sample = 'marketplace/bundles/pm-dev-python/skills/plan-marshall-plugin/extension.py'
    assert _matches_any(sample, prod_globs)


def test_real_tree_derivation_covers_marketplace_targets_generate():
    """Spot-check: the python domain covers marketplace/targets/generate.py."""
    derived = _discovery.derive_build_map_globs(PROJECT_ROOT)
    prod_globs = _prod_globs(derived['python'])
    assert _matches_any('marketplace/targets/generate.py', prod_globs)
