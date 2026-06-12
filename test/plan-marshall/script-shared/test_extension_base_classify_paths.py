#!/usr/bin/env python3
"""Tests for BuildExtensionBase.classify_paths(), classify_globs(), and the
base-lib build_map route deriver + completeness validator.

Covers three concerns of the file-to-build contract that live in the
``script-shared`` ``extension_base`` module — all now owned by the Axis-B
``BuildExtensionBase`` ABC, not ``ExtensionBase``:

1. ``classify_paths()`` — the default no-op contract and the subclass-override
   pattern (the change-set classification path).
2. ``classify_build_class()`` — the per-(path, role) build_class default map.
3. ``classify_globs()`` + ``derive_globs_from_tree()`` + the completeness
   validator ``validate_tree_completeness()`` — the explicit ``(pattern, role)``
   route accessor, the route-collection consumer the build_map seed reads, and
   the git-tracked completeness validator that reports any tracked source file no
   declared route covers **within a build-covered root** (so a production ``.py``
   the routes forgot inside a buildable-unit tree is caught, while untracked
   ``target/`` / ``.venv/`` output AND tracked source outside every build-covered
   root are ignored).

The aggregator's longest-glob-wins overlap resolution and the unclaimed-path
warning are tested separately in test_manage_execution_manifest_*.py — this
module covers only the per-extension method contract, the base route deriver,
and the validator.
"""

import fnmatch
import subprocess

from extension_base import (  # type: ignore[import-not-found]
    BUILD_CLASS_BUILD_CONFIG_FULL,
    BUILD_CLASS_NONE,
    BUILD_CLASS_PROD_COMPILE,
    BUILD_CLASS_TEST_RUN,
    BUILD_CLASSES,
    BUILD_MAP_ROLES,
    ROLE_CONFIG,
    ROLE_PRODUCTION,
    ROLE_TEST,
    BuildExtensionBase,
    derive_globs_from_tree,
    validate_tree_completeness,
)


class _MinimalExtension(BuildExtensionBase):
    """BuildExtensionBase subclass with the default Axis-B contract.

    Carries a ``get_skill_domains()`` so :func:`derive_globs_from_tree` (which
    keys collected routes by the extension's first domain key) can file the
    routes under a domain — the deriver consumes both the Axis-B routes and the
    domain key a build extension serves.
    """

    def get_skill_domains(self) -> list[dict]:
        return [{
            'domain': {'key': 'minimal', 'name': 'Minimal', 'description': 'Test only'},
            'profiles': {
                'core': {'defaults': [], 'optionals': []},
                'implementation': {'defaults': [], 'optionals': []},
                'module_testing': {'defaults': [], 'optionals': []},
                'quality': {'defaults': [], 'optionals': []},
            },
        }]


class _ClassifyingExtension(_MinimalExtension):
    """BuildExtensionBase subclass overriding classify_paths()."""

    def classify_paths(self, paths: list[str]) -> dict[str, list[str]]:
        claims: dict[str, list[str]] = {
            'production': [],
            'test': [],
            'documentation': [],
            'config': [],
        }
        for path in paths:
            if path.endswith('.py') and path.startswith('scripts/'):
                claims['production'].append(path)
            elif path.endswith('.py') and (
                path.startswith('test/') or path.startswith('tests/')
            ):
                claims['test'].append(path)
            elif path in ('pyproject.toml', 'uv.lock'):
                claims['config'].append(path)
            elif path.endswith(('.md', '.adoc')):
                claims['documentation'].append(path)
        return claims


# =============================================================================
# Default no-op contract
# =============================================================================


def test_default_classify_paths_returns_empty_four_role_dict():
    """Default classify_paths returns the empty four-role dict shape."""
    ext = _MinimalExtension()
    result = ext.classify_paths(['scripts/foo.py', 'README.md'])
    assert result == {
        'production': [],
        'test': [],
        'documentation': [],
        'config': [],
    }


def test_default_classify_paths_with_empty_input():
    """Default classify_paths handles empty path list."""
    ext = _MinimalExtension()
    assert ext.classify_paths([]) == {
        'production': [],
        'test': [],
        'documentation': [],
        'config': [],
    }


def test_default_classify_paths_contains_all_four_roles():
    """Default return must include all four canonical role keys."""
    ext = _MinimalExtension()
    result = ext.classify_paths(['anything.txt'])
    assert set(result.keys()) == {'production', 'test', 'documentation', 'config'}


def test_default_classify_paths_all_values_are_lists():
    """Default return values must all be list type (not None, not tuple)."""
    ext = _MinimalExtension()
    result = ext.classify_paths(['anything.txt'])
    for role, paths in result.items():
        assert isinstance(paths, list), f"role {role!r} value is not a list"


def test_default_classify_path_specificity_returns_zero():
    """Default classify_path_specificity returns 0 for every role/path."""
    ext = _MinimalExtension()
    assert ext.classify_path_specificity('scripts/foo.py', 'production') == 0
    assert ext.classify_path_specificity('README.md', 'documentation') == 0
    assert ext.classify_path_specificity('', 'config') == 0


def test_default_classify_paths_does_not_raise_on_unknown_paths():
    """Default no-op must accept arbitrary paths without raising."""
    ext = _MinimalExtension()
    # Should not raise even on weird inputs
    result = ext.classify_paths(['', '../etc/passwd', '/abs/path', 'é'])
    assert result['production'] == []


# =============================================================================
# Subclass override contract
# =============================================================================


def test_subclass_override_produces_correct_production_claim():
    """Subclass override classifies production source under scripts/."""
    ext = _ClassifyingExtension()
    result = ext.classify_paths(['scripts/foo.py', 'scripts/bar/baz.py'])
    assert result['production'] == ['scripts/foo.py', 'scripts/bar/baz.py']
    assert result['test'] == []
    assert result['documentation'] == []
    assert result['config'] == []


def test_subclass_override_produces_correct_test_claim():
    """Subclass override classifies test sources under test/ or tests/."""
    ext = _ClassifyingExtension()
    result = ext.classify_paths(['test/foo_test.py', 'tests/bar_test.py'])
    assert result['test'] == ['test/foo_test.py', 'tests/bar_test.py']
    assert result['production'] == []


def test_subclass_override_produces_correct_config_claim():
    """Subclass override classifies pyproject.toml / uv.lock as config."""
    ext = _ClassifyingExtension()
    result = ext.classify_paths(['pyproject.toml', 'uv.lock'])
    assert result['config'] == ['pyproject.toml', 'uv.lock']
    assert result['production'] == []


def test_subclass_override_produces_correct_documentation_claim():
    """Subclass override classifies .md and .adoc as documentation."""
    ext = _ClassifyingExtension()
    result = ext.classify_paths(['README.md', 'docs/foo.adoc'])
    assert result['documentation'] == ['README.md', 'docs/foo.adoc']


def test_subclass_override_omits_unclaimed_paths():
    """Subclass override omits paths none of its predicates match.

    The aggregator handles unclaimed paths via the `unknown` bucket — extensions
    must NOT add unclaimed paths to any of the four roles.
    """
    ext = _ClassifyingExtension()
    # mystery.xyz matches no predicate
    result = ext.classify_paths(['scripts/foo.py', 'mystery.xyz'])
    assert result['production'] == ['scripts/foo.py']
    assert 'mystery.xyz' not in result['production']
    assert 'mystery.xyz' not in result['test']
    assert 'mystery.xyz' not in result['documentation']
    assert 'mystery.xyz' not in result['config']


def test_subclass_override_mixed_input():
    """Subclass override handles a mixed input list correctly."""
    ext = _ClassifyingExtension()
    result = ext.classify_paths([
        'scripts/foo.py',
        'test/foo_test.py',
        'README.md',
        'pyproject.toml',
    ])
    assert result == {
        'production': ['scripts/foo.py'],
        'test': ['test/foo_test.py'],
        'documentation': ['README.md'],
        'config': ['pyproject.toml'],
    }


# =============================================================================
# build_class vocabulary
# =============================================================================


def test_build_classes_is_the_closed_four_value_set():
    """BUILD_CLASSES is exactly the closed 4-value enum, no more, no less.

    Each value NAMES the canonical command directly (no name-to-name
    indirection): ``compile`` / ``module-tests`` / ``verify`` for the buildable
    classes, plus ``none``. ``docs-validate`` was retired — documentation has no
    build owner.
    """
    assert BUILD_CLASSES == frozenset({
        'compile',
        'module-tests',
        'verify',
        'none',
    })
    assert len(BUILD_CLASSES) == 4


def test_docs_validate_is_not_a_build_class():
    """The retired ``docs-validate`` build_class must be absent from BUILD_CLASSES."""
    assert 'docs-validate' not in BUILD_CLASSES


def test_build_class_named_constants_are_members():
    """Each named BUILD_CLASS_* constant is a member of BUILD_CLASSES."""
    for value in (
        BUILD_CLASS_PROD_COMPILE,
        BUILD_CLASS_TEST_RUN,
        BUILD_CLASS_BUILD_CONFIG_FULL,
        BUILD_CLASS_NONE,
    ):
        assert value in BUILD_CLASSES


# =============================================================================
# Default classify_build_class role mapping
# =============================================================================


def test_default_classify_build_class_production_maps_to_compile():
    """role=production derives compile by default."""
    ext = _MinimalExtension()
    assert ext.classify_build_class('scripts/foo.py', 'production') == BUILD_CLASS_PROD_COMPILE


def test_default_classify_build_class_test_maps_to_module_tests():
    """role=test derives module-tests by default."""
    ext = _MinimalExtension()
    assert ext.classify_build_class('test/foo_test.py', 'test') == BUILD_CLASS_TEST_RUN


def test_default_classify_build_class_documentation_falls_back_to_none():
    """role=documentation has no build_class — documentation is not a build_map
    role and has no build owner, so the default mapping treats it as an unmatched
    role and derives none."""
    ext = _MinimalExtension()
    assert ext.classify_build_class('README.md', 'documentation') == BUILD_CLASS_NONE


def test_default_classify_build_class_config_maps_to_verify():
    """role=config derives verify by default."""
    ext = _MinimalExtension()
    assert ext.classify_build_class('pyproject.toml', 'config') == BUILD_CLASS_BUILD_CONFIG_FULL


def test_default_classify_build_class_unmatched_role_falls_back_to_none():
    """An unmatched role derives the none fallback."""
    ext = _MinimalExtension()
    assert ext.classify_build_class('whatever', 'unknown-role') == BUILD_CLASS_NONE
    assert ext.classify_build_class('whatever', '') == BUILD_CLASS_NONE


def test_default_classify_build_class_returns_a_member_for_every_role():
    """Every declared build_map role resolves to a BUILD_CLASSES member.

    documentation is NOT a build_map role and is deliberately excluded — it has
    no build owner and resolves to the none fallback like any unmatched role.
    """
    ext = _MinimalExtension()
    for role in ('production', 'test', 'config'):
        assert ext.classify_build_class('any/path', role) in BUILD_CLASSES


def test_default_classify_build_class_ignores_path_for_role_mapping():
    """The default mapping is keyed on role only — the path arg is ignored.

    Two different production paths resolve to the same build_class because the
    default implementation discriminates on role, never on path.
    """
    ext = _MinimalExtension()
    assert (
        ext.classify_build_class('scripts/foo.py', 'production')
        == ext.classify_build_class('generated/bar.py', 'production')
        == BUILD_CLASS_PROD_COMPILE
    )


# =============================================================================
# Subclass override of classify_build_class (path-discriminating)
# =============================================================================


class _PathDiscriminatingExtension(_MinimalExtension):
    """Override classify_build_class to derive `none` for generated production paths."""

    def classify_build_class(self, path: str, role: str) -> str:
        if role == 'production' and path.startswith('generated/'):
            return BUILD_CLASS_NONE
        return super().classify_build_class(path, role)


def test_subclass_build_class_override_discriminates_on_path():
    """A domain may override classify_build_class to key on the path.

    A generated production file derives `none` despite the `production` role,
    while a regular production file still inherits the `compile` default.
    """
    ext = _PathDiscriminatingExtension()
    assert ext.classify_build_class('generated/bar.py', 'production') == BUILD_CLASS_NONE
    assert ext.classify_build_class('scripts/foo.py', 'production') == BUILD_CLASS_PROD_COMPILE


def test_subclass_build_class_override_falls_through_for_other_roles():
    """The override delegates to the default for roles it does not special-case."""
    ext = _PathDiscriminatingExtension()
    assert ext.classify_build_class('test/foo_test.py', 'test') == BUILD_CLASS_TEST_RUN
    assert ext.classify_build_class('README.md', 'documentation') == BUILD_CLASS_NONE
    assert ext.classify_build_class('pyproject.toml', 'config') == BUILD_CLASS_BUILD_CONFIG_FULL


# =============================================================================
# build_map role vocabulary constants
# =============================================================================


def test_build_map_roles_is_the_closed_three_value_set():
    """BUILD_MAP_ROLES is exactly production / test / config — no documentation.

    Documentation is not a build_map route role (no build owner for docs), so the
    ``documentation`` role is deliberately absent from the set.
    """
    assert BUILD_MAP_ROLES == frozenset({
        'production',
        'test',
        'config',
    })
    assert len(BUILD_MAP_ROLES) == 3


def test_build_map_role_named_constants_are_members():
    """Each build_map role constant is a member; documentation is NOT."""
    for value in (ROLE_PRODUCTION, ROLE_TEST, ROLE_CONFIG):
        assert value in BUILD_MAP_ROLES
    assert 'documentation' not in BUILD_MAP_ROLES


# =============================================================================
# classify_globs() accessor — explicit (pattern, role) routes
# =============================================================================


class _RouteExtension(_MinimalExtension):
    """BuildExtensionBase subclass declaring explicit (pattern, role) build_map routes.

    Routes use single-``*`` fnmatch globs (the matcher the build_map consumer
    uses) where a ``*`` matches across ``/`` — so ``scripts/*.py`` covers
    ``scripts/foo.py`` and any file beneath ``scripts/``.
    """

    def classify_globs(self) -> list[tuple[str, str]]:
        return [
            ('scripts/*.py', ROLE_PRODUCTION),
            ('test/*.py', ROLE_TEST),
            ('pyproject.toml', ROLE_CONFIG),
        ]


def test_default_classify_globs_returns_empty_list():
    """The base default classify_globs returns an empty list (domain claims nothing)."""
    ext = _MinimalExtension()
    assert ext.classify_globs() == []


def test_classify_paths_override_does_not_imply_globs_override():
    """A classify_paths override alone leaves classify_globs at the empty default.

    classify_globs is a separate accessor — overriding classify_paths does not
    auto-populate the routes.
    """
    ext = _ClassifyingExtension()
    assert ext.classify_globs() == []


def test_subclass_classify_globs_returns_routes_verbatim():
    """A classify_globs override returns the (pattern, role) routes verbatim."""
    ext = _RouteExtension()
    assert ext.classify_globs() == [
        ('scripts/*.py', 'production'),
        ('test/*.py', 'test'),
        ('pyproject.toml', 'config'),
    ]


def test_classify_globs_returns_resolved_roles():
    """Each route's second element is a resolved BUILD_MAP_ROLES member.

    The route carries a resolved role (``production`` / ``test`` / ...), NOT a
    by-location heuristic name — there is no heuristic indirection left.
    """
    ext = _RouteExtension()
    for _pattern, role in ext.classify_globs():
        assert role in BUILD_MAP_ROLES


# =============================================================================
# derive_globs_from_tree() — explicit-route collection consumer
# =============================================================================


def _matches_any(path: str, globs: list[str]) -> bool:
    """Return True when ``path`` matches at least one collected route pattern."""
    return any(fnmatch.fnmatchcase(path, g) for g in globs)


def test_derive_globs_returns_empty_dict_for_no_extensions():
    """No registered extensions ⇒ no collected routes."""
    assert derive_globs_from_tree('/irrelevant', []) == {}


def test_derive_globs_skips_extension_with_no_routes():
    """An extension whose classify_globs() is empty contributes nothing."""
    # _MinimalExtension keeps the base empty-route default.
    assert derive_globs_from_tree('/irrelevant', [_MinimalExtension()]) == {}


def test_derive_globs_keys_result_by_domain_key(tmp_path):
    """The collected dict is keyed by the extension's first domain key.

    The tree carries a file matching each of _RouteExtension's routes so none is
    pruned by the tree-presence filter.
    """
    _git_init_and_track(tmp_path, ['scripts/foo.py', 'test/bar.py', 'pyproject.toml'])
    derived = derive_globs_from_tree(str(tmp_path), [_RouteExtension()])
    assert set(derived.keys()) == {'minimal'}


def test_derive_globs_returns_declared_routes_present_in_tree(tmp_path):
    """The collected routes are the declared (pattern, role) tuples present in the tree, sorted.

    No per-directory enumeration — the compact declared route set seeds directly,
    filtered to routes whose pattern matches at least one tracked file.
    """
    _git_init_and_track(tmp_path, ['scripts/foo.py', 'test/bar.py', 'pyproject.toml'])
    derived = derive_globs_from_tree(str(tmp_path), [_RouteExtension()])
    assert derived['minimal'] == sorted([
        ('scripts/*.py', 'production'),
        ('test/*.py', 'test'),
        ('pyproject.toml', 'config'),
    ])


def test_derive_globs_is_compact_not_per_directory(tmp_path):
    """A single production route stays one entry regardless of tree breadth.

    The regression this fixes: the old deriver emitted one glob per matched
    directory (167 globs); the explicit-route contract keeps the declared route
    count compact even when many files match the single route.
    """
    _git_init_and_track(
        tmp_path,
        ['scripts/a.py', 'scripts/b.py', 'scripts/sub/c.py', 'test/bar.py', 'pyproject.toml'],
    )
    derived = derive_globs_from_tree(str(tmp_path), [_RouteExtension()])
    prod = [(p, r) for p, r in derived['minimal'] if r == 'production']
    assert prod == [('scripts/*.py', 'production')]


def test_derive_globs_prunes_route_absent_from_tree(tmp_path):
    """A declared route whose pattern matches no tracked file is pruned.

    The tree carries only ``scripts/foo.py`` — the ``test/*.py`` and
    ``pyproject.toml`` routes match nothing and are pruned, while the live
    ``scripts/*.py`` route survives. This is the dead-glob fix.
    """
    _git_init_and_track(tmp_path, ['scripts/foo.py'])
    derived = derive_globs_from_tree(str(tmp_path), [_RouteExtension()])
    assert derived['minimal'] == [('scripts/*.py', 'production')]


def test_derive_globs_omits_domain_whose_every_route_is_dead(tmp_path):
    """A domain left with no surviving routes is omitted entirely.

    An empty tracked-file set prunes every route, so the extension's domain key
    does not appear in the result.
    """
    _git_init_and_track(tmp_path, ['README.md'])
    derived = derive_globs_from_tree(str(tmp_path), [_RouteExtension()])
    assert derived == {}


def test_derive_globs_empty_tree_prunes_all_routes(tmp_path):
    """An empty git-tracked file set prunes all routes (returns empty)."""
    _git_init_and_track(tmp_path, [])
    derived = derive_globs_from_tree(str(tmp_path), [_RouteExtension()])
    assert derived == {}


def test_derive_globs_deduplicates_routes(tmp_path):
    """Duplicate declared routes collapse to one entry."""

    class _DupRouteExtension(_MinimalExtension):
        def classify_globs(self) -> list[tuple[str, str]]:
            return [
                ('scripts/*.py', ROLE_PRODUCTION),
                ('scripts/*.py', ROLE_PRODUCTION),
            ]

    _git_init_and_track(tmp_path, ['scripts/foo.py'])
    derived = derive_globs_from_tree(str(tmp_path), [_DupRouteExtension()])
    assert derived['minimal'] == [('scripts/*.py', 'production')]


def test_derive_globs_entries_are_sorted_and_deterministic(tmp_path):
    """The per-domain entries are emitted in deterministic sorted order."""

    class _UnsortedRouteExtension(_MinimalExtension):
        def classify_globs(self) -> list[tuple[str, str]]:
            return [
                ('z/*.py', ROLE_PRODUCTION),
                ('a/*.py', ROLE_PRODUCTION),
                ('m/*.py', ROLE_PRODUCTION),
            ]

    _git_init_and_track(tmp_path, ['z/x.py', 'a/x.py', 'm/x.py'])
    first = derive_globs_from_tree(str(tmp_path), [_UnsortedRouteExtension()])
    second = derive_globs_from_tree(str(tmp_path), [_UnsortedRouteExtension()])
    assert first == second
    assert first['minimal'] == sorted(first['minimal'])


def test_derive_globs_skips_extension_without_domain_key():
    """An extension with routes but no resolvable domain key is omitted."""

    class _NoDomainKeyExtension(_RouteExtension):
        def get_skill_domains(self) -> list[dict]:
            return []

    derived = derive_globs_from_tree('/irrelevant', [_NoDomainKeyExtension()])
    assert derived == {}


def test_derive_globs_ignores_route_with_unknown_role():
    """A route tuple with a non-BUILD_MAP_ROLES role contributes nothing."""

    class _BadRoleExtension(_MinimalExtension):
        def classify_globs(self) -> list[tuple[str, str]]:
            return [('scripts/*.py', 'not-a-real-role')]

    derived = derive_globs_from_tree('/irrelevant', [_BadRoleExtension()])
    assert derived == {}


def test_derive_globs_survives_extension_raising_in_classify_globs(tmp_path):
    """A broken extension is skipped, not allowed to abort the whole derivation."""

    class _RaisingExtension(_MinimalExtension):
        def classify_globs(self) -> list[tuple[str, str]]:
            raise RuntimeError('boom')

    _git_init_and_track(tmp_path, ['scripts/foo.py', 'test/bar.py', 'pyproject.toml'])
    derived = derive_globs_from_tree(str(tmp_path), [_RaisingExtension(), _RouteExtension()])
    # The raising extension is skipped; the well-behaved one still contributes.
    assert 'minimal' in derived


def test_derive_globs_every_entry_role_resolves_to_a_build_class(tmp_path):
    """Each (pattern, role) route resolves to a BUILD_CLASSES member.

    This is exactly the per-entry lookup the build_map seed aggregator performs.
    """
    ext = _RouteExtension()
    _git_init_and_track(tmp_path, ['scripts/foo.py', 'test/bar.py', 'pyproject.toml'])
    derived = derive_globs_from_tree(str(tmp_path), [ext])
    for _pattern, role in derived['minimal']:
        assert ext.classify_build_class(_pattern, role) in BUILD_CLASSES


# =============================================================================
# validate_tree_completeness() — git-tracked completeness validator
# =============================================================================


def _git_init_and_track(root, rel_paths: list[str]) -> None:
    """Create + git-add each repo-relative path under ``root`` as a tracked file."""
    subprocess.run(['git', '-C', str(root), 'init', '-q'], check=True)
    subprocess.run(['git', '-C', str(root), 'config', 'user.email', 't@t'], check=True)
    subprocess.run(['git', '-C', str(root), 'config', 'user.name', 'T'], check=True)
    for rel in rel_paths:
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text('')
    subprocess.run(['git', '-C', str(root), 'add', '-A'], check=True)


def test_validate_completeness_returns_empty_when_all_covered(tmp_path):
    """Every tracked source file matched by a declared route ⇒ no uncovered paths."""
    _git_init_and_track(tmp_path, ['scripts/foo.py', 'test/test_foo.py'])
    uncovered = validate_tree_completeness(str(tmp_path), [_RouteExtension()])
    assert uncovered == []


class _SubrootRouteExtension(_MinimalExtension):
    """Build extension whose production route is narrower than its buildable root.

    The route ``src/*/main.py`` claims the directory root ``src/`` (the leading
    non-wildcard prefix) but only matches a ``main.py`` one level under it. So a
    sibling ``.py`` under ``src/`` IS a buildable unit (inside the build-covered
    root) yet uncovered by the route — exactly the in-root-but-missed case the
    completeness validator must still surface.
    """

    def classify_globs(self) -> list[tuple[str, str]]:
        return [('src/*/main.py', ROLE_PRODUCTION)]


def test_validate_completeness_flags_uncovered_tracked_source_inside_build_root(tmp_path):
    """An uncovered .py INSIDE a build-covered root still surfaces (31fed0).

    ``src/a/main.py`` is matched by the route (covered); ``src/a/orphan.py`` lives
    under the same build-covered root ``src/`` but no route matches it — so it is
    a buildable unit the routes forgot and is reported uncovered.
    """
    _git_init_and_track(tmp_path, ['src/a/main.py', 'src/a/orphan.py'])
    uncovered = validate_tree_completeness(str(tmp_path), [_SubrootRouteExtension()])
    assert 'src/a/orphan.py' in uncovered
    assert 'src/a/main.py' not in uncovered


def test_validate_completeness_ignores_source_outside_every_build_root(tmp_path):
    """A tracked .py OUTSIDE every build-covered root is NOT reported (31fed0).

    The buildable-units denominator: ``_RouteExtension``'s production/test routes
    establish the roots ``scripts/`` and ``test/``. A one-off
    ``marketplace/targets/generate.py`` lives under neither root, so it is not a
    buildable unit and the validator stays silent on it — even though no route
    covers it.
    """
    _git_init_and_track(tmp_path, ['scripts/foo.py', 'marketplace/targets/generate.py'])
    uncovered = validate_tree_completeness(str(tmp_path), [_RouteExtension()])
    assert 'marketplace/targets/generate.py' not in uncovered
    assert 'scripts/foo.py' not in uncovered
    assert uncovered == []


def test_validate_completeness_ignores_untracked_paths(tmp_path):
    """Untracked target/ and .venv/ output is never flagged (tracked-only scan)."""
    _git_init_and_track(tmp_path, ['scripts/foo.py'])
    # Create untracked source files under build/dependency output dirs.
    for untracked in ('target/built.py', '.venv/lib/dep.py'):
        target = tmp_path / untracked
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text('')
    uncovered = validate_tree_completeness(str(tmp_path), [_RouteExtension()])
    assert 'target/built.py' not in uncovered
    assert '.venv/lib/dep.py' not in uncovered
    assert uncovered == []


def test_validate_completeness_ignores_non_source_suffixes(tmp_path):
    """Tracked docs / config (.md, .toml) are not source files and not flagged."""
    _git_init_and_track(tmp_path, ['scripts/foo.py', 'README.md', 'extra.toml'])
    uncovered = validate_tree_completeness(str(tmp_path), [_RouteExtension()])
    # README.md / extra.toml are non-source — only .py is validated for coverage.
    assert uncovered == []


def test_validate_completeness_returns_empty_outside_git_repo(tmp_path):
    """A non-repo root yields no uncovered paths (validator fails soft, not loud)."""
    (tmp_path / 'scripts').mkdir()
    (tmp_path / 'scripts' / 'foo.py').write_text('')
    uncovered = validate_tree_completeness(str(tmp_path), [_RouteExtension()])
    assert uncovered == []


def test_validate_completeness_only_production_and_test_routes_cover(tmp_path):
    """Only production/test routes count toward coverage — a config route does not.

    A config route does not make a tracked .py covered; the .py must be matched by
    a production or test route. The production route ``src/*/main.py`` establishes
    the build-covered root ``src/`` (so ``src/a/foo.py`` IS a buildable unit),
    while the config route ``src/*.py`` does not count as coverage — so the in-root
    ``src/a/foo.py`` it only config-matches still surfaces.
    """

    class _ConfigRouteWithBuildRootExtension(_MinimalExtension):
        def classify_globs(self) -> list[tuple[str, str]]:
            return [
                ('src/*/main.py', ROLE_PRODUCTION),  # establishes build root src/
                ('src/*.py', ROLE_CONFIG),  # does NOT count toward coverage
            ]

    _git_init_and_track(tmp_path, ['src/a/main.py', 'src/a/foo.py'])
    uncovered = validate_tree_completeness(str(tmp_path), [_ConfigRouteWithBuildRootExtension()])
    # src/a/foo.py is inside the build-covered root but matched only by a
    # config route, so it is still uncovered. src/a/main.py is covered.
    assert 'src/a/foo.py' in uncovered
    assert 'src/a/main.py' not in uncovered
