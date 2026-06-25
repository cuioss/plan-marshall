#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
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
import pathlib
import subprocess

import pytest

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
_marketplace_paths = load_script_module('plan-marshall', 'script-shared', 'marketplace_paths.py')


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


def _git_init_and_track(root, rel_paths: list[str]) -> None:
    """Create + git-add each repo-relative path under ``root`` as a tracked file.

    The route collector (``derive_globs_from_tree``) prunes any declared route
    whose pattern matches no git-tracked file, so the synthetic-route bridge units
    must seed a tree carrying a file for each route they expect to survive.
    """
    subprocess.run(['git', '-C', str(root), 'init', '-q'], check=True)
    subprocess.run(['git', '-C', str(root), 'config', 'user.email', 't@t'], check=True)
    subprocess.run(['git', '-C', str(root), 'config', 'user.name', 'T'], check=True)
    for rel in rel_paths:
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text('')
    subprocess.run(['git', '-C', str(root), 'add', '-A'], check=True)


# =============================================================================
# Synthetic-route bridge units
# =============================================================================


def test_bridge_returns_empty_for_no_extensions(tmp_path):
    """An empty pre-discovered extension list yields an empty collection."""
    result = _discovery.derive_build_map_globs(tmp_path, extensions=[])
    assert result == {}


_PYTHON_STUB_TREE = ['marketplace/bundles/foo.py', 'test/bar.py', 'pyproject.toml']


def test_bridge_keys_result_by_domain_key(tmp_path):
    """The bridge returns a dict keyed by each build extension's served domain key.

    A documentation-only build extension contributes no routes (documentation is
    not a build_map role), so its domain is omitted from the keyed result. The
    tree carries a file for each python route so none is pruned as dead.
    """
    _git_init_and_track(tmp_path, _PYTHON_STUB_TREE)
    extensions = [
        {'skill': 'build-pyproject', 'module': _StubPythonBuildExtension()},
        {'skill': 'build-docs', 'module': _StubDocsBuildExtension()},
    ]
    result = _discovery.derive_build_map_globs(tmp_path, extensions=extensions)
    assert set(result.keys()) == {'python'}


def test_bridge_collects_routes_present_in_tree(tmp_path):
    """The bridge collects each build extension's declared routes present in the tree."""
    _git_init_and_track(tmp_path, _PYTHON_STUB_TREE)
    extensions = [{'skill': 'build-pyproject', 'module': _StubPythonBuildExtension()}]
    result = _discovery.derive_build_map_globs(tmp_path, extensions=extensions)
    assert ('marketplace/bundles/*.py', 'production') in result['python']
    assert ('test/*.py', 'test') in result['python']
    assert ('pyproject.toml', 'config') in result['python']


def test_bridge_prunes_route_absent_from_tree(tmp_path):
    """A declared route whose pattern matches no tracked file is pruned by the bridge."""
    # Only the production glob has a matching tracked file; test/ and pyproject.toml do not.
    _git_init_and_track(tmp_path, ['marketplace/bundles/foo.py'])
    extensions = [{'skill': 'build-pyproject', 'module': _StubPythonBuildExtension()}]
    result = _discovery.derive_build_map_globs(tmp_path, extensions=extensions)
    assert result['python'] == [('marketplace/bundles/*.py', 'production')]


def test_bridge_omits_domains_with_no_routes(tmp_path):
    """A build extension whose classify_globs() returns no routes contributes nothing."""
    _git_init_and_track(tmp_path, _PYTHON_STUB_TREE)
    extensions = [
        {'skill': 'build-empty', 'module': _StubEmptyBuildExtension()},
        {'skill': 'build-pyproject', 'module': _StubPythonBuildExtension()},
    ]
    result = _discovery.derive_build_map_globs(tmp_path, extensions=extensions)
    assert set(result.keys()) == {'python'}


def test_bridge_skips_entries_with_no_module(tmp_path):
    """Entries lacking a 'module' key are filtered before the collector runs."""
    _git_init_and_track(tmp_path, _PYTHON_STUB_TREE)
    extensions = [
        {'skill': 'broken'},  # no 'module'
        {'skill': 'build-pyproject', 'module': _StubPythonBuildExtension()},
    ]
    result = _discovery.derive_build_map_globs(tmp_path, extensions=extensions)
    assert set(result.keys()) == {'python'}


def test_bridge_separates_production_and_test_by_declared_role(tmp_path):
    """Production vs test is split by the declared route role, not a tree predicate."""
    _git_init_and_track(tmp_path, _PYTHON_STUB_TREE)
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
    _git_init_and_track(tmp_path, _PYTHON_STUB_TREE)
    extensions = [{'skill': 'build-pyproject', 'module': _StubPythonBuildExtension()}]
    result = _discovery.derive_build_map_globs(tmp_path, extensions=extensions)
    entries = result['python']
    assert entries == sorted(set(entries))


def test_bridge_is_deterministic(tmp_path):
    """Two collections over the same extensions return identical results."""
    _git_init_and_track(tmp_path, _PYTHON_STUB_TREE)
    extensions = [{'skill': 'build-pyproject', 'module': _StubPythonBuildExtension()}]
    first = _discovery.derive_build_map_globs(tmp_path, extensions=extensions)
    second = _discovery.derive_build_map_globs(tmp_path, extensions=extensions)
    assert first == second
    assert first  # non-empty: the python routes survived the tree-presence filter


def test_bridge_merges_routes_across_same_domain_build_extensions(tmp_path):
    """Two build extensions serving the same domain key MERGE their routes.

    build-maven and build-gradle both serve ``java``; the bridge must union their
    declared routes under ``java`` rather than let the second overwrite the first.
    """
    _git_init_and_track(tmp_path, ['src/main/App.java', 'pom.xml', 'build.gradle'])
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


# =============================================================================
# Frontmatter-driven manifest discovery: find_extension_path + read_implements_field
# =============================================================================
#
# find_extension_path() resolves each bundle's extension.py by reading the
# implements: frontmatter declaration from candidate skills/*/SKILL.md files and
# deriving the sibling extension.py from the matched manifest directory. There is
# NO path heuristic on the directory name plan-marshall-plugin and NO markdown-body
# discovery signal. The contract lives in ext-point-domain-bundle.md.

_DOMAIN_BUNDLE_ARCHETYPE = 'plan-marshall:extension-api/standards/ext-point-domain-bundle'

# The 10 production bundles that each ship a domain-bundle manifest. The bundle
# dir name is the manifest's bundle directory under marketplace/bundles/.
_PRODUCTION_BUNDLES = (
    'plan-marshall',
    'pm-dev-java',
    'pm-dev-java-cui',
    'pm-dev-frontend',
    'pm-dev-frontend-cui',
    'pm-dev-python',
    'pm-dev-oci',
    'pm-documents',
    'pm-plugin-development',
    'pm-requirements',
)


def _write_manifest(skill_dir, *, implements, with_extension=True):
    """Create a SKILL.md (with optional implements:) and sibling extension.py.

    Args:
        skill_dir: Path to the manifest skill directory to populate.
        implements: The implements: value to write, or None to omit the key.
        with_extension: When True, also write a sibling extension.py.
    """
    skill_dir.mkdir(parents=True, exist_ok=True)
    fm_lines = ['---', 'name: ' + skill_dir.name]
    if implements is not None:
        fm_lines.append('implements: ' + implements)
    fm_lines += ['user-invocable: false', '---', '', '# ' + skill_dir.name, '']
    (skill_dir / 'SKILL.md').write_text('\n'.join(fm_lines), encoding='utf-8')
    if with_extension:
        (skill_dir / 'extension.py').write_text('class Extension: ...\n', encoding='utf-8')


# --- read_implements_field unit coverage -------------------------------------


def test_read_implements_field_returns_value(tmp_path):
    """The reader returns the implements: declaration as a one-element list.

    ``read_implements_field`` now returns a ``list[str]`` (supporting multi-interface
    block-sequence declarations); an inline scalar normalizes to a one-element list.
    """
    skill = tmp_path / 'manifest'
    _write_manifest(skill, implements=_DOMAIN_BUNDLE_ARCHETYPE, with_extension=False)
    assert _discovery.read_implements_field(skill / 'SKILL.md') == [_DOMAIN_BUNDLE_ARCHETYPE]


def test_read_implements_field_strips_surrounding_quotes(tmp_path):
    """A double- or single-quoted implements: value resolves to the bare value (list form)."""
    skill = tmp_path / 'manifest'
    skill.mkdir()
    (skill / 'SKILL.md').write_text(
        '---\nname: m\nimplements: "' + _DOMAIN_BUNDLE_ARCHETYPE + '"\n---\n\n# m\n',
        encoding='utf-8',
    )
    assert _discovery.read_implements_field(skill / 'SKILL.md') == [_DOMAIN_BUNDLE_ARCHETYPE]


def test_read_implements_field_returns_block_sequence_values(tmp_path):
    """A YAML block-sequence implements: returns every declared interface, in order.

    A step doc may declare more than one interface (e.g. a phase-6 workflow step
    that implements both ext-point-execution-context-workflow and
    ext-point-finalize-step); the reader returns each declared value.
    """
    skill = tmp_path / 'manifest'
    skill.mkdir()
    (skill / 'SKILL.md').write_text(
        '---\nname: m\nimplements:\n'
        '  - plan-marshall:extension-api/standards/ext-point-execution-context-workflow\n'
        '  - plan-marshall:extension-api/standards/ext-point-finalize-step\n'
        '---\n\n# m\n',
        encoding='utf-8',
    )
    assert _discovery.read_implements_field(skill / 'SKILL.md') == [
        'plan-marshall:extension-api/standards/ext-point-execution-context-workflow',
        'plan-marshall:extension-api/standards/ext-point-finalize-step',
    ]


def test_read_implements_field_empty_when_key_absent(tmp_path):
    """A manifest with frontmatter but no implements: key yields an empty list."""
    skill = tmp_path / 'manifest'
    _write_manifest(skill, implements=None, with_extension=False)
    assert _discovery.read_implements_field(skill / 'SKILL.md') == []


def test_read_implements_field_empty_when_no_frontmatter(tmp_path):
    """A SKILL.md with no leading --- frontmatter block yields an empty list."""
    skill = tmp_path / 'manifest'
    skill.mkdir()
    (skill / 'SKILL.md').write_text('# manifest\n\nNo frontmatter here.\n', encoding='utf-8')
    assert _discovery.read_implements_field(skill / 'SKILL.md') == []


def test_read_implements_field_empty_when_file_missing(tmp_path):
    """An unreadable / missing SKILL.md yields an empty list rather than raising."""
    assert _discovery.read_implements_field(tmp_path / 'missing' / 'SKILL.md') == []


# --- find_extension_path synthetic-tree coverage -----------------------------


def test_find_extension_path_resolves_via_frontmatter_declaration(tmp_path):
    """find_extension_path() matches the manifest by implements:, not directory name.

    The manifest lives under an arbitrarily-named skill directory (NOT
    plan-marshall-plugin) and is discovered purely by its implements: declaration.
    """
    bundle = tmp_path / 'some-bundle'
    skill = bundle / 'skills' / 'arbitrary-manifest-name'
    _write_manifest(skill, implements=_DOMAIN_BUNDLE_ARCHETYPE)
    resolved = _discovery.find_extension_path(bundle)
    assert resolved == skill / 'extension.py'


def test_find_extension_path_ignores_directory_name_without_declaration(tmp_path):
    """A plan-marshall-plugin dir WITHOUT the implements: key is NOT discovered.

    Proves the directory-name path heuristic is gone: the legacy directory name
    no longer suffices for discovery.
    """
    bundle = tmp_path / 'some-bundle'
    skill = bundle / 'skills' / 'plan-marshall-plugin'
    _write_manifest(skill, implements=None)
    assert _discovery.find_extension_path(bundle) is None


def test_find_extension_path_ignores_non_matching_declaration(tmp_path):
    """A manifest declaring a DIFFERENT implements: value is not discovered."""
    bundle = tmp_path / 'some-bundle'
    skill = bundle / 'skills' / 'plan-marshall-plugin'
    _write_manifest(skill, implements='plan-marshall:extension-api/standards/ext-point-recipe')
    assert _discovery.find_extension_path(bundle) is None


def test_find_extension_path_none_when_sibling_extension_missing(tmp_path):
    """A matching manifest with no sibling extension.py yields None."""
    bundle = tmp_path / 'some-bundle'
    skill = bundle / 'skills' / 'plan-marshall-plugin'
    _write_manifest(skill, implements=_DOMAIN_BUNDLE_ARCHETYPE, with_extension=False)
    assert _discovery.find_extension_path(bundle) is None


def test_find_extension_path_resolves_versioned_cache_structure(tmp_path):
    """The versioned-cache branch (bundle/{version}/skills/...) still resolves."""
    bundle = tmp_path / 'some-bundle'
    skill = bundle / '1.0.0' / 'skills' / 'plan-marshall-plugin'
    _write_manifest(skill, implements=_DOMAIN_BUNDLE_ARCHETYPE)
    resolved = _discovery.find_extension_path(bundle)
    assert resolved == skill / 'extension.py'


def test_find_extension_path_prefers_source_over_versioned(tmp_path):
    """When both a source and a versioned manifest declare the archetype, the
    source-structure manifest (bundle/skills/...) wins over the versioned-cache
    one (bundle/{version}/skills/...) — the source branch is checked first."""
    bundle = tmp_path / 'some-bundle'
    source_skill = bundle / 'skills' / 'plan-marshall-plugin'
    _write_manifest(source_skill, implements=_DOMAIN_BUNDLE_ARCHETYPE)
    versioned_skill = bundle / '1.0.0' / 'skills' / 'plan-marshall-plugin'
    _write_manifest(versioned_skill, implements=_DOMAIN_BUNDLE_ARCHETYPE)
    resolved = _discovery.find_extension_path(bundle)
    assert resolved == source_skill / 'extension.py'


def test_find_extension_path_skips_hidden_version_dirs(tmp_path):
    """A hidden version directory is skipped; the valid versioned manifest wins.

    No source-structure manifest is present, so resolution falls to the
    versioned-cache branch, which must skip the dot-prefixed directory.
    """
    bundle = tmp_path / 'some-bundle'
    hidden_skill = bundle / '.hidden' / 'skills' / 'plan-marshall-plugin'
    _write_manifest(hidden_skill, implements=_DOMAIN_BUNDLE_ARCHETYPE)
    valid_skill = bundle / '1.0.0' / 'skills' / 'plan-marshall-plugin'
    _write_manifest(valid_skill, implements=_DOMAIN_BUNDLE_ARCHETYPE)
    resolved = _discovery.find_extension_path(bundle)
    assert resolved == valid_skill / 'extension.py'


# --- find_extension_path real-tree coverage: all 10 production manifests ------


def test_find_extension_path_resolves_all_10_production_manifests():
    """find_extension_path() resolves each of the 10 production bundles' manifests.

    The central regression for this deliverable: every production bundle's
    extension.py is discovered through the frontmatter declaration over the live
    marketplace tree.
    """
    resolved = {}
    for bundle in _PRODUCTION_BUNDLES:
        bundle_dir = MARKETPLACE_ROOT / bundle
        path = _discovery.find_extension_path(bundle_dir)
        assert path is not None, f'{bundle}: find_extension_path returned None'
        assert path.is_file(), f'{bundle}: resolved path is not a file: {path}'
        assert path.name == 'extension.py', f'{bundle}: resolved non-extension.py: {path}'
        resolved[bundle] = path
    assert len(resolved) == 10


def test_find_extension_path_resolved_manifests_declare_the_archetype():
    """Each resolved manifest's sibling SKILL.md declares the domain-bundle archetype.

    Confirms the resolution key really is the implements: declaration: the
    SKILL.md beside each resolved extension.py carries the canonical value.
    """
    for bundle in _PRODUCTION_BUNDLES:
        bundle_dir = MARKETPLACE_ROOT / bundle
        path = _discovery.find_extension_path(bundle_dir)
        assert path is not None, f'{bundle}: find_extension_path returned None'
        skill_md = path.parent / 'SKILL.md'
        assert _DOMAIN_BUNDLE_ARCHETYPE in _discovery.read_implements_field(skill_md), (
            f'{bundle}: resolved manifest SKILL.md does not declare the domain-bundle archetype'
        )


def test_discover_all_extensions_finds_all_production_bundles():
    """discover_all_extensions() (which calls find_extension_path per bundle)
    loads every production bundle's Extension via the frontmatter scanner."""
    extensions = _discovery.discover_all_extensions()
    found_bundles = {ext['bundle'] for ext in extensions}
    for bundle in _PRODUCTION_BUNDLES:
        assert bundle in found_bundles, f'{bundle} not discovered by discover_all_extensions()'


# =============================================================================
# Gap 5 — deployed-bundle cache discovery routes through the layout op
# =============================================================================
# extension_discovery.get_plugin_cache_path() and the marketplace_paths
# bundle-cache resolvers route through the platform-runtime
# ``layout bundle-cache-root`` op rather than a hardcoded
# ``~/.claude/plugins/cache/plan-marshall`` literal. These tests assert the
# Claude single-root and OpenCode multi-root layouts both resolve, the per-process
# memoisation holds, and the env override / fallback paths still work.


@pytest.fixture(autouse=True)
def _reset_bundle_cache_roots_cache():
    """Clear the per-process bundle-cache memoisation before and after each test."""
    _marketplace_paths._BUNDLE_CACHE_ROOTS_CACHE = None
    yield
    _marketplace_paths._BUNDLE_CACHE_ROOTS_CACHE = None


def test_claude_bundle_cache_root_is_the_dot_claude_plugin_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """On Claude, the bundle-cache root is ~/.claude/plugins/cache/plan-marshall."""
    monkeypatch.setattr(_marketplace_paths, '_read_runtime_target', lambda: 'claude')
    roots = _marketplace_paths.get_bundle_cache_roots()
    assert len(roots) == 1
    assert roots[0].endswith('/.claude/plugins/cache/plan-marshall')


def test_opencode_bundle_cache_roots_are_the_user_global_skill_roots(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """On OpenCode, the bundle-cache roots are the ~-anchored user-global skill roots."""
    monkeypatch.delenv('OPENCODE_CONFIG_DIR', raising=False)
    monkeypatch.setattr(_marketplace_paths, '_read_runtime_target', lambda: 'opencode')
    roots = _marketplace_paths.get_bundle_cache_roots()
    # OpenCode has no single plugin cache — discovery falls back to the user-global
    # skill roots, in priority order.
    assert any(r.endswith('/.config/opencode/skills') for r in roots)
    assert any(r.endswith('/.claude/skills') for r in roots)
    assert any(r.endswith('/.agents/skills') for r in roots)


def test_bundle_cache_roots_is_memoised(monkeypatch: pytest.MonkeyPatch) -> None:
    """The bundle-cache layout op is invoked at most once per process (memoised)."""
    calls: list[str] = []

    def _fake_invoke(target: str, method_name: str = 'layout_skill_roots'):
        calls.append(method_name)
        return ('/fake/cache',)

    monkeypatch.setattr(_marketplace_paths, '_read_runtime_target', lambda: 'claude')
    monkeypatch.setattr(_marketplace_paths, '_invoke_layout_op', _fake_invoke)

    first = _marketplace_paths.get_bundle_cache_roots()
    second = _marketplace_paths.get_bundle_cache_roots()
    assert first == second == ('/fake/cache',)
    assert calls == ['layout_bundle_cache_root'], 'op must be invoked once via the bundle-cache method'


def test_bundle_cache_roots_falls_back_to_claude_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """When the layout op is unreachable, the Claude default cache root is used."""
    monkeypatch.setattr(_marketplace_paths, '_invoke_layout_op', lambda target, method_name=None: None)
    roots = _marketplace_paths.get_bundle_cache_roots()
    assert len(roots) == 1
    assert roots[0].endswith('/.claude/plugins/cache/plan-marshall')


def test_extension_discovery_plugin_cache_routes_through_layout_op(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """extension_discovery.get_plugin_cache_path resolves via the routed roots."""
    monkeypatch.delenv('PLUGIN_CACHE_PATH', raising=False)
    monkeypatch.setattr(
        _discovery, 'get_bundle_cache_roots', lambda: ('/routed/cache/root',)
    )
    assert _discovery.get_plugin_cache_path() == pathlib.Path('/routed/cache/root')


def test_extension_discovery_plugin_cache_honours_env_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An explicit PLUGIN_CACHE_PATH env var outranks the layout op."""
    monkeypatch.setenv('PLUGIN_CACHE_PATH', '/explicit/override')
    assert _discovery.get_plugin_cache_path() == pathlib.Path('/explicit/override')


# =============================================================================
# find_implementors — the reusable ext-point implementor discovery query
# =============================================================================
#
# find_implementors(ext_point) is the SOLE finalize-step discovery path. It scans
# three real surfaces (phase-6-finalize/{workflow,standards}/*.md, every bundle's
# skills/*/SKILL.md, and project-local .claude/skills/finalize-step-*/SKILL.md)
# anchored on the marketplace tree, returning one record per implementor with
# name / order / default_on / presets / description / source / path.

_FINALIZE_STEP_EXT_POINT = 'plan-marshall:extension-api/standards/ext-point-finalize-step'


def _finalize_implementors() -> dict[str, dict]:
    """Return the discovered finalize-step implementors keyed by step id.

    Asserts step-id uniqueness BEFORE collapsing the records into a name-keyed
    dict: a dict comprehension silently drops a duplicate (last write wins), so
    a regression that re-emits the same ``bundle:skill`` twice — e.g. the cache
    + source dedup breaking — would be invisible if we keyed without checking.
    """
    records = _discovery.find_implementors(_FINALIZE_STEP_EXT_POINT)
    names = [rec['name'] for rec in records]
    assert len(names) == len(set(names)), (
        f'duplicate implementor step ids must not occur: {sorted(names)}'
    )
    return {rec['name']: rec for rec in records}


def test_find_implementors_returns_records_sorted_by_order():
    """find_implementors returns implementor records sorted ascending by (order, name)."""
    records = _discovery.find_implementors(_FINALIZE_STEP_EXT_POINT)

    assert records, 'Expected at least one finalize-step implementor'
    # Assert the FULL (order, name) sort contract, not just the primary key:
    # records sharing an ``order`` must be tie-broken ascending by ``name``.
    sort_keys = [(rec['order'], rec['name']) for rec in records]
    assert sort_keys == sorted(sort_keys), (
        f'records must be ascending by (order, name): {sort_keys}'
    )


def test_find_implementors_record_carries_all_contract_fields():
    """Each implementor record carries the five-field contract plus source / path."""
    records = _discovery.find_implementors(_FINALIZE_STEP_EXT_POINT)

    expected_keys = {'name', 'order', 'default_on', 'presets', 'description', 'source', 'path'}
    for rec in records:
        assert expected_keys <= set(rec.keys()), (
            f'record {rec.get("name")!r} missing contract fields: '
            f'{expected_keys - set(rec.keys())}'
        )
        assert isinstance(rec['order'], int)
        assert isinstance(rec['default_on'], bool)
        assert isinstance(rec['presets'], list)


def test_find_implementors_surfaces_each_source_kind():
    """Discovery surfaces built-in, bundle-optional, and project finalize steps."""
    sources = {rec['source'] for rec in _discovery.find_implementors(_FINALIZE_STEP_EXT_POINT)}

    assert 'built-in' in sources, 'phase-6-finalize built-in steps must be discovered'
    assert 'bundle-optional' in sources, 'opt-in bundle steps must be discovered'
    assert 'project' in sources, 'project-local finalize-step skills must be discovered'


def test_find_implementors_built_in_push_record():
    """The built-in default:push step is discovered with its declared frontmatter."""
    by_name = _finalize_implementors()

    assert 'default:push' in by_name, 'default:push must be a discovered built-in step'
    push = by_name['default:push']
    assert push['source'] == 'built-in'
    assert push['order'] == 10
    assert push['default_on'] is True
    # push ships in every named preset (the local/standard/full ladder)
    assert set(push['presets']) == {'local', 'standard', 'full'}


def test_find_implementors_bundle_optional_retrospective_record():
    """plan-marshall:plan-retrospective is discovered as a bundle-optional step."""
    by_name = _finalize_implementors()

    assert 'plan-marshall:plan-retrospective' in by_name
    retro = by_name['plan-marshall:plan-retrospective']
    assert retro['source'] == 'bundle-optional'
    assert retro['default_on'] is False
    assert retro['order'] == 995
    # retrospective is a member of the full preset only
    assert retro['presets'] == ['full']


def test_find_implementors_project_step_record():
    """A project-local finalize-step skill is discovered with source: project."""
    by_name = _finalize_implementors()

    assert 'project:finalize-step-plugin-doctor' in by_name
    doctor = by_name['project:finalize-step-plugin-doctor']
    assert doctor['source'] == 'project'
    assert doctor['default_on'] is False
    # project steps carry presets: [] (presets ship to consumers without them)
    assert doctor['presets'] == []


def test_find_implementors_empty_for_unknown_ext_point():
    """find_implementors returns an empty list for an ext-point no doc declares."""
    records = _discovery.find_implementors('plan-marshall:extension-api/standards/ext-point-nonexistent')

    assert records == []


def test_find_implementors_finalize_records_carry_empty_canonicals():
    """Finalize-step records carry the verify-step ``canonicals`` key, defaulting to [].

    ``canonicals`` was added to the shared implementor record so verify-step
    discovery can expose it. A finalize-step doc declares no ``canonicals``, so
    every finalize record must carry the key with an empty-list default — proving
    the cross-ext-point record union does not break the finalize archetype.
    """
    records = _discovery.find_implementors(_FINALIZE_STEP_EXT_POINT)

    assert records, 'Expected at least one finalize-step implementor'
    for rec in records:
        assert 'canonicals' in rec, f'{rec.get("name")!r} missing canonicals key'
        assert rec['canonicals'] == [], (
            f'{rec.get("name")!r} finalize record must default canonicals to []'
        )


# =============================================================================
# find_implementors — verify-step discovery (phase-5-execute standards surface)
# =============================================================================
#
# The verify-step ext-point adds a fourth scan surface
# (phase-5-execute/standards/*.md) and a ``canonicals`` list field. The sole
# built-in implementor is canonical_verify.md, whose canonicals list the
# discovery consumer expands into default:verify:{canonical} step ids. The
# contract lives in ext-point-verify-step.md.

_VERIFY_STEP_EXT_POINT = 'plan-marshall:extension-api/standards/ext-point-verify-step'


def test_find_implementors_discovers_canonical_verify():
    """find_implementors(VERIFY_STEP_EXT_POINT) discovers the canonical_verify.md doc.

    The central regression for this deliverable: the phase-5-execute standards
    scan surface surfaces the verify-step implementor over the live tree.
    """
    records = _discovery.find_implementors(_VERIFY_STEP_EXT_POINT)

    assert records, 'Expected the canonical_verify verify-step implementor'
    paths = [rec['path'] for rec in records]
    assert any(p.endswith('phase-5-execute/standards/canonical_verify.md') for p in paths), (
        f'canonical_verify.md must be discovered; got paths {paths}'
    )


def test_find_implementors_verify_record_carries_canonicals_list():
    """The discovered verify-step record exposes a ``canonicals`` list field.

    The canonicals list enumerates the canonical command names the parameterized
    step backs (quality-gate / module-tests / coverage), which the discovery
    consumer expands into default:verify:{canonical} step ids.
    """
    records = _discovery.find_implementors(_VERIFY_STEP_EXT_POINT)
    by_name = {rec['name']: rec for rec in records}

    assert 'default:verify' in by_name, (
        f'the parameterized verify step must be discovered; got {sorted(by_name)}'
    )
    verify = by_name['default:verify']
    assert verify['source'] == 'built-in'
    assert isinstance(verify['canonicals'], list)
    # The list enumerates exactly the built-in canonical set, in execution order.
    assert verify['canonicals'] == ['quality-gate', 'module-tests', 'coverage']


def test_find_implementors_verify_surface_does_not_leak_finalize_steps():
    """A verify-step query surfaces ONLY verify steps — no finalize-step records.

    The per-ext-point implements: match must keep the phase-5 and phase-6 surfaces
    disjoint: querying the verify ext-point must not return any phase-6 finalize
    step, and vice versa.
    """
    verify_records = _discovery.find_implementors(_VERIFY_STEP_EXT_POINT)
    verify_paths = [rec['path'] for rec in verify_records]
    assert not any('phase-6-finalize' in p for p in verify_paths), (
        f'verify-step query must not surface phase-6 docs; got {verify_paths}'
    )


def test_find_implementors_finalize_unaffected_by_phase5_surface():
    """Adding the phase-5 scan surface leaves finalize-step discovery unchanged.

    A finalize-step query must surface no phase-5-execute doc — the new scan
    surface only contributes records when the queried ext-point matches the
    phase-5 doc's implements: declaration.
    """
    finalize_records = _discovery.find_implementors(_FINALIZE_STEP_EXT_POINT)
    finalize_paths = [rec['path'] for rec in finalize_records]
    assert not any('phase-5-execute' in p for p in finalize_paths), (
        f'finalize-step query must not surface phase-5 docs; got {finalize_paths}'
    )
    # The finalize surfaces (built-in / bundle-optional / project) are all still present.
    sources = {rec['source'] for rec in finalize_records}
    assert {'built-in', 'bundle-optional', 'project'} <= sources
