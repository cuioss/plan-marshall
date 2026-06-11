#!/usr/bin/env python3
# ruff: noqa: I001, E402
"""Tests for the extension_discovery → route-collector bridge.

``derive_build_map_globs(project_root, extensions)`` bridges BUILD-extension
discovery to the ``script-shared`` base-lib route collector
(``derive_globs_from_tree``). Each build skill's ``BuildExtensionBase`` subclass
declares its build_map as explicit ``(pattern, role)`` routes via
``classify_globs()`` — an fnmatch-style glob (e.g. ``marketplace/bundles/*.py``)
paired with one of the four resolved roles (``production`` / ``test`` /
``documentation`` / ``config``). The bridge gathers those declared routes
verbatim, keyed by each build extension's served domain key; it no longer scans
the tree to enumerate one glob per directory. When two build extensions serve the
same domain key (build-maven + build-gradle both serving ``java``), their routes
are MERGED under that key. Tree completeness is a SEPARATE concern handled by
``validate_tree_completeness``. The build_map seed aggregator (``manage-config``)
consumes this output.

Three flavours of coverage:

1. Synthetic-route units — stub build-extension modules declaring explicit
   routes, asserting the bridge collects them verbatim, keyed by served domain,
   role-filtered, de-duplicated, and merged across same-domain extensions (no
   dependency on the live marketplace tree).
2. Build-extension discovery — ``discover_build_extensions()`` loads each build
   skill's ``scripts/extension.py`` and returns the ``BuildExtension`` instances,
   each declaring its served domain key.
3. Real-tree regression — the bridge over the live worktree (discovering the real
   build extensions), asserting the 26 previously-missed production ``.py`` files
   (every ``*/skills/plan-marshall-plugin/extension.py`` and every
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
# now declare resolved roles directly. ``BuildExtensionBase`` is the Axis-B
# contract anchor the real build extensions subclass.
from extension_base import (  # type: ignore[import-not-found]
    ROLE_CONFIG,
    ROLE_PRODUCTION,
    ROLE_TEST,
    BuildExtensionBase,
)

_discovery = load_script_module('plan-marshall', 'extension-api', 'extension_discovery.py')


# =============================================================================
# Stub build extensions and helpers
# =============================================================================


class _StubPythonBuildExtension(BuildExtensionBase):
    """Minimal build extension declaring explicit python production/test/config routes."""

    def get_skill_domains(self) -> list[dict]:
        return [{'domain': {'key': 'python', 'name': 'P', 'description': 'd'}, 'profiles': {}}]

    def classify_globs(self) -> list[tuple[str, str]]:
        return [
            ('marketplace/bundles/*.py', ROLE_PRODUCTION),
            ('test/*.py', ROLE_TEST),
            ('pyproject.toml', ROLE_CONFIG),
        ]


class _StubDocsBuildExtension(BuildExtensionBase):
    """Build extension declaring ONLY a documentation route.

    Documentation is no longer a build_map role (no build owner for docs), so the
    deriver filters this extension's sole route out — the extension contributes
    NO build_map entries. Used to assert that a documentation-only build
    extension is dropped from the keyed result.
    """

    def get_skill_domains(self) -> list[dict]:
        return [{'domain': {'key': 'documentation', 'name': 'D', 'description': 'd'}, 'profiles': {}}]

    def classify_globs(self) -> list[tuple[str, str]]:
        # 'documentation' is no longer a build_map role (ROLE_DOCUMENTATION was
        # removed); the literal role string here is exactly what the deriver must
        # filter out, so this extension contributes NO build_map entries.
        return [('*.md', 'documentation')]


class _StubEmptyBuildExtension(BuildExtensionBase):
    """Minimal build extension owning no buildable file types (no routes)."""

    def get_skill_domains(self) -> list[dict]:
        return [{'domain': {'key': 'empty', 'name': 'E', 'description': 'd'}, 'profiles': {}}]

    def classify_globs(self) -> list[tuple[str, str]]:
        return []


class _StubMavenBuildExtension(BuildExtensionBase):
    """A java-domain build extension declaring maven-style routes."""

    def get_skill_domains(self) -> list[dict]:
        return [{'domain': {'key': 'java', 'name': 'J', 'description': 'd'}, 'profiles': {}}]

    def classify_globs(self) -> list[tuple[str, str]]:
        return [('src/main/*.java', ROLE_PRODUCTION), ('pom.xml', ROLE_CONFIG)]


class _StubGradleBuildExtension(BuildExtensionBase):
    """A second java-domain build extension declaring gradle-style routes.

    Shares the ``java`` domain key with the maven stub: the bridge must MERGE
    both extensions' routes under ``java`` rather than overwrite.
    """

    def get_skill_domains(self) -> list[dict]:
        return [{'domain': {'key': 'java', 'name': 'J', 'description': 'd'}, 'profiles': {}}]

    def classify_globs(self) -> list[tuple[str, str]]:
        return [('src/main/*.java', ROLE_PRODUCTION), ('build.gradle', ROLE_CONFIG)]


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
    """The bridge returns a dict keyed by each build extension's served domain key.

    A documentation-only build extension contributes no routes (documentation is
    not a build_map role), so its domain is omitted from the keyed result.
    """
    extensions = [
        {'skill': 'build-pyproject', 'module': _StubPythonBuildExtension()},
        {'skill': 'build-docs', 'module': _StubDocsBuildExtension()},
    ]
    result = _discovery.derive_build_map_globs(tmp_path, extensions=extensions)
    assert set(result.keys()) == {'python'}


def test_bridge_collects_routes_verbatim(tmp_path):
    """The bridge collects each build extension's declared routes verbatim (no tree scan)."""
    extensions = [{'skill': 'build-pyproject', 'module': _StubPythonBuildExtension()}]
    result = _discovery.derive_build_map_globs(tmp_path, extensions=extensions)
    assert ('marketplace/bundles/*.py', 'production') in result['python']
    assert ('test/*.py', 'test') in result['python']
    assert ('pyproject.toml', 'config') in result['python']


def test_bridge_omits_domains_with_no_routes(tmp_path):
    """A build extension whose classify_globs() returns no routes contributes nothing."""
    extensions = [
        {'skill': 'build-empty', 'module': _StubEmptyBuildExtension()},
        {'skill': 'build-pyproject', 'module': _StubPythonBuildExtension()},
    ]
    result = _discovery.derive_build_map_globs(tmp_path, extensions=extensions)
    assert set(result.keys()) == {'python'}


def test_bridge_skips_entries_with_no_module(tmp_path):
    """Entries lacking a 'module' key are filtered before the collector runs."""
    extensions = [
        {'skill': 'broken'},  # no 'module'
        {'skill': 'build-pyproject', 'module': _StubPythonBuildExtension()},
    ]
    result = _discovery.derive_build_map_globs(tmp_path, extensions=extensions)
    assert set(result.keys()) == {'python'}


def test_bridge_separates_production_and_test_by_declared_role(tmp_path):
    """Production vs test is split by the declared route role, not a tree predicate."""
    extensions = [{'skill': 'build-pyproject', 'module': _StubPythonBuildExtension()}]
    result = _discovery.derive_build_map_globs(tmp_path, extensions=extensions)
    entries = result['python']
    prod_globs = [glob for glob, role in entries if role == 'production']
    test_globs = [glob for glob, role in entries if role == 'test']
    assert 'marketplace/bundles/*.py' in prod_globs
    assert 'test/*.py' in test_globs
    assert 'test/*.py' not in prod_globs


def test_bridge_returns_deduplicated_sorted_routes(tmp_path):
    """Collected routes are de-duplicated and returned in deterministic sorted order."""
    extensions = [{'skill': 'build-pyproject', 'module': _StubPythonBuildExtension()}]
    result = _discovery.derive_build_map_globs(tmp_path, extensions=extensions)
    entries = result['python']
    assert entries == sorted(set(entries))


def test_bridge_is_deterministic(tmp_path):
    """Two collections over the same extensions return identical results."""
    extensions = [{'skill': 'build-pyproject', 'module': _StubPythonBuildExtension()}]
    first = _discovery.derive_build_map_globs(tmp_path, extensions=extensions)
    second = _discovery.derive_build_map_globs(tmp_path, extensions=extensions)
    assert first == second


def test_bridge_merges_routes_across_same_domain_build_extensions(tmp_path):
    """Two build extensions serving the same domain key MERGE their routes.

    build-maven and build-gradle both serve ``java``; the bridge must union their
    declared routes under ``java`` rather than let the second overwrite the first.
    """
    extensions = [
        {'skill': 'build-maven', 'module': _StubMavenBuildExtension()},
        {'skill': 'build-gradle', 'module': _StubGradleBuildExtension()},
    ]
    result = _discovery.derive_build_map_globs(tmp_path, extensions=extensions)
    assert set(result.keys()) == {'java'}
    java_routes = result['java']
    # Both the shared production route and BOTH config descriptors are present.
    assert ('src/main/*.java', 'production') in java_routes
    assert ('pom.xml', 'config') in java_routes
    assert ('build.gradle', 'config') in java_routes
    # De-duplicated: the shared production route appears exactly once.
    assert java_routes.count(('src/main/*.java', 'production')) == 1


# =============================================================================
# Build-extension discovery
# =============================================================================


def test_discover_build_extensions_returns_real_build_extensions():
    """discover_build_extensions() loads each build skill's BuildExtension.

    The four build skills (build-pyproject / build-maven / build-gradle /
    build-npm) each ship a BuildExtension(BuildExtensionBase). Discovery loads
    them all and returns one entry per skill carrying the instantiated module.
    """
    discovered = _discovery.discover_build_extensions()
    skills = {entry['skill'] for entry in discovered}
    # At minimum the four build skills must be discovered.
    assert {'build-pyproject', 'build-maven', 'build-gradle', 'build-npm'} <= skills
    for entry in discovered:
        module = entry['module']
        assert isinstance(module, BuildExtensionBase)
        # Each declares routes and a served domain key.
        assert module.classify_globs()
        domains = module.get_skill_domains()
        assert domains and domains[0]['domain']['key']


def test_discover_build_extensions_serves_expected_domain_keys():
    """Each real build extension is filed under its expected served domain key."""
    discovered = _discovery.discover_build_extensions()
    by_skill = {entry['skill']: entry['module'] for entry in discovered}

    def _key(skill: str) -> str:
        return by_skill[skill].get_skill_domains()[0]['domain']['key']

    assert _key('build-pyproject') == 'python'
    assert _key('build-maven') == 'java'
    assert _key('build-gradle') == 'java'
    assert _key('build-npm') == 'javascript'


# =============================================================================
# Real-tree regression: the 26 previously-missed production .py files
# =============================================================================
#
# The build_map redesign's central regression: the python build system's old
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

    The bridge discovers the live build extensions and collects their declared
    routes over the real worktree. The python build system's production routes
    must match every extension.py and every marketplace/targets/**/*.py — the exact
    set the old static scripts/-anchored globs silently dropped.
    """
    derived = _discovery.derive_build_map_globs(PROJECT_ROOT)
    assert 'python' in derived, 'python domain must contribute build_map routes'
    prod_globs = _prod_globs(derived['python'])

    corpus = _real_production_py_outside_scripts()
    uncovered = [p for p in corpus if not _matches_any(p, prod_globs)]
    assert not uncovered, f'declared production routes miss {len(uncovered)} files: {uncovered[:10]}'


def test_real_tree_routes_cover_a_sample_extension_py():
    """Spot-check: the python build system covers pm-dev-python's own extension.py."""
    derived = _discovery.derive_build_map_globs(PROJECT_ROOT)
    prod_globs = _prod_globs(derived['python'])
    sample = 'marketplace/bundles/pm-dev-python/skills/plan-marshall-plugin/extension.py'
    assert _matches_any(sample, prod_globs)


def test_real_tree_routes_cover_marketplace_targets_generate():
    """Spot-check: the python build system covers marketplace/targets/generate.py."""
    derived = _discovery.derive_build_map_globs(PROJECT_ROOT)
    prod_globs = _prod_globs(derived['python'])
    assert _matches_any('marketplace/targets/generate.py', prod_globs)


# =============================================================================
# plan-marshall-plugin skill-domains: the vestigial build domain is retired
# =============================================================================
#
# The plan-marshall-plugin extension once declared an empty-profiles ``build``
# skill-domain alongside ``general-dev``. ADR-004 moved the file-to-build
# contract to the build-system extensions, so the vestigial ``build`` domain was
# removed — get_skill_domains() now returns ONLY general-dev. Removing it also
# dissolves the name collision with the new top-level ``build`` config block.

def _load_plan_marshall_plugin_extension():
    """Load the plan-marshall-plugin ``extension.py`` from the skill ROOT.

    The plan-marshall-plugin extension lives at
    ``skills/plan-marshall-plugin/extension.py`` (skill root), NOT under a
    ``scripts/`` subdirectory — so the conftest ``load_script_module`` helper
    (which resolves ``.../skills/<skill>/scripts/<file>``) cannot load it.
    This mirrors the proven ``load_extension`` helper in
    ``test_extension_implementations.py``.
    """
    import importlib.util

    extension_path = (
        MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'plan-marshall-plugin' / 'extension.py'
    )
    if not extension_path.is_file():
        raise FileNotFoundError(f'Extension not found: {extension_path}')
    spec = importlib.util.spec_from_file_location(
        'plan_marshall_plugin_extension', extension_path
    )
    if spec is None or spec.loader is None:
        raise ImportError(f'Could not load module from {extension_path}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_PLAN_MARSHALL_PLUGIN_EXTENSION = _load_plan_marshall_plugin_extension()


def _plan_marshall_plugin_domain_keys() -> list[str]:
    """Return the domain keys the plan-marshall-plugin extension declares."""
    extension = _PLAN_MARSHALL_PLUGIN_EXTENSION.Extension()
    return [entry['domain']['key'] for entry in extension.get_skill_domains()]


def test_plan_marshall_plugin_get_skill_domains_returns_only_general_dev():
    """get_skill_domains() returns exactly the general-dev domain — nothing else.

    The list must contain general-dev and no other domain entry, proving the
    vestigial build skill-domain is gone.
    """
    keys = _plan_marshall_plugin_domain_keys()
    assert keys == ['general-dev'], (
        f'plan-marshall-plugin must declare only general-dev, got {keys}'
    )


def test_plan_marshall_plugin_get_skill_domains_omits_build_domain():
    """The retired build skill-domain must be absent from the returned list."""
    keys = _plan_marshall_plugin_domain_keys()
    assert 'build' not in keys, (
        'the vestigial build skill-domain must not be declared by plan-marshall-plugin'
    )
