#!/usr/bin/env python3
# ruff: noqa: I001, E402
"""Tests for the extension_discovery → route-collector bridge.

``derive_build_map_globs(project_root, extensions)`` bridges extension
discovery to the ``script-shared`` base-lib route collector
(``derive_globs_from_tree``). Each registered extension declares its build_map
as explicit ``(pattern, role)`` routes via ``classify_globs()`` — an
fnmatch-style glob (e.g. ``marketplace/bundles/*.py``) paired with one of the
four resolved roles (``production`` / ``test`` / ``documentation`` /
``config``). The bridge gathers those declared routes verbatim, keyed by each
extension's domain key; it no longer scans the tree to enumerate one glob per
directory. Tree completeness is a SEPARATE concern handled by
``validate_tree_completeness``. The build_map seed aggregator (``manage-config``)
consumes this output.

Two flavours of coverage:

1. Synthetic-route units — stub extension modules declaring explicit routes,
   asserting the bridge collects them verbatim, keyed by domain, role-filtered,
   and de-duplicated (no dependency on the live marketplace tree).
2. Real-tree regression — the bridge over the live worktree, asserting the 26
   previously-missed production ``.py`` files (every
   ``*/skills/plan-marshall-plugin/extension.py`` and every
   ``marketplace/targets/**/*.py``) are now covered by a declared python
   production route. This is the regression the build_map redesign exists to fix.
"""

from __future__ import annotations

import fnmatch

# conftest.py sets up the marketplace PYTHONPATH and exposes module loaders.
from conftest import (  # type: ignore[import-not-found]
    MARKETPLACE_ROOT,
    PROJECT_ROOT,
    load_script_module,
)

# The resolved-role constants used to build stub route sets live in the
# script-shared extension module (already on sys.path via conftest). The old
# ROLE_HEURISTIC_* constants were removed by the build_map redesign — routes
# now declare resolved roles directly.
from extension_base import (  # type: ignore[import-not-found]
    ROLE_CONFIG,
    ROLE_DOCUMENTATION,
    ROLE_PRODUCTION,
    ROLE_TEST,
    ExtensionBase,
)

_discovery = load_script_module('plan-marshall', 'extension-api', 'extension_discovery.py')


# =============================================================================
# Stub extensions and helpers
# =============================================================================


class _StubPythonExtension(ExtensionBase):
    """Minimal extension declaring explicit python production/test/config routes."""

    def get_skill_domains(self) -> list[dict]:
        return [{'domain': {'key': 'python', 'name': 'P', 'description': 'd'}, 'profiles': {}}]

    def classify_globs(self) -> list[tuple[str, str]]:
        return [
            ('marketplace/bundles/*.py', ROLE_PRODUCTION),
            ('test/*.py', ROLE_TEST),
            ('pyproject.toml', ROLE_CONFIG),
        ]


class _StubDocsExtension(ExtensionBase):
    """Minimal extension declaring a broad documentation route."""

    def get_skill_domains(self) -> list[dict]:
        return [{'domain': {'key': 'documentation', 'name': 'D', 'description': 'd'}, 'profiles': {}}]

    def classify_globs(self) -> list[tuple[str, str]]:
        return [('*.md', ROLE_DOCUMENTATION)]


class _StubEmptyExtension(ExtensionBase):
    """Minimal extension owning no buildable file types (no routes)."""

    def get_skill_domains(self) -> list[dict]:
        return [{'domain': {'key': 'empty', 'name': 'E', 'description': 'd'}, 'profiles': {}}]

    def classify_globs(self) -> list[tuple[str, str]]:
        return []


def _matches_any(path: str, globs: list[str]) -> bool:
    return any(fnmatch.fnmatchcase(path, g) for g in globs)


def _prod_globs(entries: list[tuple[str, str]]) -> list[str]:
    return [glob for glob, role in entries if role == 'production']


# =============================================================================
# Synthetic-route bridge units
# =============================================================================


def test_bridge_returns_empty_for_no_extensions(tmp_path):
    """An empty pre-discovered extension list yields an empty collection."""
    result = _discovery.derive_build_map_globs(tmp_path, extensions=[])
    assert result == {}


def test_bridge_keys_result_by_domain_key(tmp_path):
    """The bridge returns a dict keyed by each extension's domain key."""
    extensions = [
        {'bundle': 'pm-dev-python', 'module': _StubPythonExtension()},
        {'bundle': 'pm-documents', 'module': _StubDocsExtension()},
    ]
    result = _discovery.derive_build_map_globs(tmp_path, extensions=extensions)
    assert set(result.keys()) == {'python', 'documentation'}


def test_bridge_collects_routes_verbatim(tmp_path):
    """The bridge collects each extension's declared routes verbatim (no tree scan)."""
    extensions = [{'bundle': 'pm-dev-python', 'module': _StubPythonExtension()}]
    result = _discovery.derive_build_map_globs(tmp_path, extensions=extensions)
    assert ('marketplace/bundles/*.py', 'production') in result['python']
    assert ('test/*.py', 'test') in result['python']
    assert ('pyproject.toml', 'config') in result['python']


def test_bridge_omits_domains_with_no_routes(tmp_path):
    """An extension whose classify_globs() returns no routes contributes nothing."""
    extensions = [
        {'bundle': 'empty', 'module': _StubEmptyExtension()},
        {'bundle': 'pm-dev-python', 'module': _StubPythonExtension()},
    ]
    result = _discovery.derive_build_map_globs(tmp_path, extensions=extensions)
    assert set(result.keys()) == {'python'}


def test_bridge_skips_entries_with_no_module(tmp_path):
    """Entries lacking a 'module' key are filtered before the collector runs."""
    extensions = [
        {'bundle': 'broken'},  # no 'module'
        {'bundle': 'pm-dev-python', 'module': _StubPythonExtension()},
    ]
    result = _discovery.derive_build_map_globs(tmp_path, extensions=extensions)
    assert set(result.keys()) == {'python'}


def test_bridge_separates_production_and_test_by_declared_role(tmp_path):
    """Production vs test is split by the declared route role, not a tree predicate."""
    extensions = [{'bundle': 'pm-dev-python', 'module': _StubPythonExtension()}]
    result = _discovery.derive_build_map_globs(tmp_path, extensions=extensions)
    entries = result['python']
    prod_globs = [glob for glob, role in entries if role == 'production']
    test_globs = [glob for glob, role in entries if role == 'test']
    assert 'marketplace/bundles/*.py' in prod_globs
    assert 'test/*.py' in test_globs
    assert 'test/*.py' not in prod_globs


def test_bridge_returns_deduplicated_sorted_routes(tmp_path):
    """Collected routes are de-duplicated and returned in deterministic sorted order."""
    extensions = [{'bundle': 'pm-dev-python', 'module': _StubPythonExtension()}]
    result = _discovery.derive_build_map_globs(tmp_path, extensions=extensions)
    entries = result['python']
    assert entries == sorted(set(entries))


def test_bridge_is_deterministic(tmp_path):
    """Two collections over the same extensions return identical results."""
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
# The explicit python production routes (marketplace/bundles/*.py and
# marketplace/targets/*.py — a single * spans /) now cover all of them.


def _real_production_py_outside_scripts() -> list[str]:
    """Enumerate every repo-relative production .py under marketplace/ that
    lives outside a scripts/ directory and outside any test root.

    Mirrors the set the declared routes must cover: the extension.py files and
    the marketplace/targets/ package. Resolved from the live tree so the test
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


def test_real_tree_routes_cover_every_out_of_scripts_production_py():
    """Every out-of-scripts production .py is covered by a declared python production route.

    The bridge discovers the live extensions and collects their declared routes
    over the real worktree. The python domain's production routes must match
    every extension.py and every marketplace/targets/**/*.py — the exact set the
    old static scripts/-anchored globs silently dropped.
    """
    derived = _discovery.derive_build_map_globs(PROJECT_ROOT)
    assert 'python' in derived, 'python domain must contribute build_map routes'
    prod_globs = _prod_globs(derived['python'])

    corpus = _real_production_py_outside_scripts()
    uncovered = [p for p in corpus if not _matches_any(p, prod_globs)]
    assert not uncovered, f'declared production routes miss {len(uncovered)} files: {uncovered[:10]}'


def test_real_tree_routes_cover_a_sample_extension_py():
    """Spot-check: the python domain covers pm-dev-python's own extension.py."""
    derived = _discovery.derive_build_map_globs(PROJECT_ROOT)
    prod_globs = _prod_globs(derived['python'])
    sample = 'marketplace/bundles/pm-dev-python/skills/plan-marshall-plugin/extension.py'
    assert _matches_any(sample, prod_globs)


def test_real_tree_routes_cover_marketplace_targets_generate():
    """Spot-check: the python domain covers marketplace/targets/generate.py."""
    derived = _discovery.derive_build_map_globs(PROJECT_ROOT)
    prod_globs = _prod_globs(derived['python'])
    assert _matches_any('marketplace/targets/generate.py', prod_globs)
