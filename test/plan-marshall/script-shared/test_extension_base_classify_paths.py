#!/usr/bin/env python3
"""Tests for ExtensionBase.classify_paths(), classify_globs(), and the
base-lib build_map route deriver + completeness validator.

Covers three concerns of the file-to-build contract that live in the
``script-shared`` ``extension_base`` module:

1. ``classify_paths()`` — the default no-op contract and the subclass-override
   pattern (the change-set classification path).
2. ``classify_build_class()`` — the per-(path, role) build_class default map.
3. ``classify_globs()`` + ``derive_globs_from_tree()`` + the completeness
   validator ``validate_tree_completeness()`` — the explicit ``(pattern, role)``
   route accessor, the route-collection consumer the build_map seed reads, and
   the git-tracked completeness validator that reports any tracked source file no
   declared route covers (so a production ``.py`` outside the obvious roots is
   caught, while untracked ``target/`` / ``.venv/`` output is ignored).

The aggregator's longest-glob-wins overlap resolution and the unclaimed-path
warning are tested separately in test_manage_execution_manifest_*.py — this
module covers only the per-extension method contract, the base route deriver,
and the validator.
"""

import fnmatch
import subprocess

from extension_base import (  # type: ignore[import-not-found]
    BUILD_CLASS_BUILD_CONFIG_FULL,
    BUILD_CLASS_DOCS_VALIDATE,
    BUILD_CLASS_NONE,
    BUILD_CLASS_PROD_COMPILE,
    BUILD_CLASS_TEST_RUN,
    BUILD_CLASSES,
    BUILD_MAP_ROLES,
    ROLE_CONFIG,
    ROLE_DOCUMENTATION,
    ROLE_PRODUCTION,
    ROLE_TEST,
    ExtensionBase,
    derive_globs_from_tree,
    validate_tree_completeness,
)


class _MinimalExtension(ExtensionBase):
    """ExtensionBase subclass with only the abstract method implemented."""

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
    """ExtensionBase subclass overriding classify_paths()."""

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


def test_build_classes_is_the_closed_five_value_set():
    """BUILD_CLASSES is exactly the closed 5-value enum, no more, no less.

    Each value NAMES the canonical command directly (no name-to-name
    indirection): ``compile`` / ``module-tests`` / ``verify`` for the buildable
    classes, plus ``docs-validate`` and ``none``.
    """
    assert BUILD_CLASSES == frozenset({
        'compile',
        'module-tests',
        'docs-validate',
        'verify',
        'none',
    })
    assert len(BUILD_CLASSES) == 5


def test_build_class_named_constants_are_members():
    """Each named BUILD_CLASS_* constant is a member of BUILD_CLASSES."""
    for value in (
        BUILD_CLASS_PROD_COMPILE,
        BUILD_CLASS_TEST_RUN,
        BUILD_CLASS_DOCS_VALIDATE,
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


def test_default_classify_build_class_documentation_maps_to_docs_validate():
    """role=documentation derives docs-validate by default."""
    ext = _MinimalExtension()
    assert ext.classify_build_class('README.md', 'documentation') == BUILD_CLASS_DOCS_VALIDATE


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
    """Every declared role resolves to a BUILD_CLASSES member."""
    ext = _MinimalExtension()
    for role in ('production', 'test', 'documentation', 'config'):
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
    assert ext.classify_build_class('README.md', 'documentation') == BUILD_CLASS_DOCS_VALIDATE
    assert ext.classify_build_class('pyproject.toml', 'config') == BUILD_CLASS_BUILD_CONFIG_FULL


# =============================================================================
# build_map role vocabulary constants
# =============================================================================


def test_build_map_roles_is_the_closed_four_value_set():
    """BUILD_MAP_ROLES is exactly the four resolved roles, no more, no less."""
    assert BUILD_MAP_ROLES == frozenset({
        'production',
        'test',
        'documentation',
        'config',
    })
    assert len(BUILD_MAP_ROLES) == 4


def test_build_map_role_named_constants_are_members():
    """Each named role constant is a member of BUILD_MAP_ROLES."""
    for value in (ROLE_PRODUCTION, ROLE_TEST, ROLE_DOCUMENTATION, ROLE_CONFIG):
        assert value in BUILD_MAP_ROLES


# =============================================================================
# classify_globs() accessor — explicit (pattern, role) routes
# =============================================================================


class _RouteExtension(_MinimalExtension):
    """ExtensionBase subclass declaring explicit (pattern, role) build_map routes.

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


def test_derive_globs_keys_result_by_domain_key():
    """The collected dict is keyed by the extension's first domain key."""
    derived = derive_globs_from_tree('/irrelevant', [_RouteExtension()])
    assert set(derived.keys()) == {'minimal'}


def test_derive_globs_returns_declared_routes_verbatim():
    """The collected routes are the declared (pattern, role) tuples, sorted.

    No tree scan, no per-directory enumeration — the compact declared route set
    seeds directly.
    """
    derived = derive_globs_from_tree('/irrelevant', [_RouteExtension()])
    assert derived['minimal'] == sorted([
        ('scripts/*.py', 'production'),
        ('test/*.py', 'test'),
        ('pyproject.toml', 'config'),
    ])


def test_derive_globs_is_compact_not_per_directory():
    """A single production route stays one entry regardless of tree breadth.

    The regression this fixes: the old deriver emitted one glob per matched
    directory (167 globs); the explicit-route contract keeps the declared route
    count compact.
    """
    derived = derive_globs_from_tree('/irrelevant', [_RouteExtension()])
    prod = [(p, r) for p, r in derived['minimal'] if r == 'production']
    assert prod == [('scripts/*.py', 'production')]


def test_derive_globs_does_not_read_project_root(tmp_path):
    """Route collection ignores the tree — project_root is signature parity only."""
    # An empty tmp_path tree must not change the collected routes.
    derived = derive_globs_from_tree(str(tmp_path), [_RouteExtension()])
    assert ('scripts/*.py', 'production') in derived['minimal']


def test_derive_globs_deduplicates_routes():
    """Duplicate declared routes collapse to one entry."""

    class _DupRouteExtension(_MinimalExtension):
        def classify_globs(self) -> list[tuple[str, str]]:
            return [
                ('scripts/*.py', ROLE_PRODUCTION),
                ('scripts/*.py', ROLE_PRODUCTION),
            ]

    derived = derive_globs_from_tree('/irrelevant', [_DupRouteExtension()])
    assert derived['minimal'] == [('scripts/*.py', 'production')]


def test_derive_globs_entries_are_sorted_and_deterministic():
    """The per-domain entries are emitted in deterministic sorted order."""

    class _UnsortedRouteExtension(_MinimalExtension):
        def classify_globs(self) -> list[tuple[str, str]]:
            return [
                ('z/*.py', ROLE_PRODUCTION),
                ('a/*.py', ROLE_PRODUCTION),
                ('m/*.py', ROLE_PRODUCTION),
            ]

    first = derive_globs_from_tree('/irrelevant', [_UnsortedRouteExtension()])
    second = derive_globs_from_tree('/irrelevant', [_UnsortedRouteExtension()])
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


def test_derive_globs_survives_extension_raising_in_classify_globs():
    """A broken extension is skipped, not allowed to abort the whole derivation."""

    class _RaisingExtension(_MinimalExtension):
        def classify_globs(self) -> list[tuple[str, str]]:
            raise RuntimeError('boom')

    derived = derive_globs_from_tree('/irrelevant', [_RaisingExtension(), _RouteExtension()])
    # The raising extension is skipped; the well-behaved one still contributes.
    assert 'minimal' in derived


def test_derive_globs_every_entry_role_resolves_to_a_build_class():
    """Each (pattern, role) route resolves to a BUILD_CLASSES member.

    This is exactly the per-entry lookup the build_map seed aggregator performs.
    """
    ext = _RouteExtension()
    derived = derive_globs_from_tree('/irrelevant', [ext])
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


def test_validate_completeness_flags_uncovered_tracked_source(tmp_path):
    """A tracked production .py outside every declared route is reported uncovered.

    The regression this fixes: a production module the routes forgot (here
    ``marketplace/targets/generate.py``, outside ``scripts/``) surfaces as an
    uncovered path instead of being silently missed.
    """
    _git_init_and_track(tmp_path, ['scripts/foo.py', 'marketplace/targets/generate.py'])
    uncovered = validate_tree_completeness(str(tmp_path), [_RouteExtension()])
    assert 'marketplace/targets/generate.py' in uncovered
    assert 'scripts/foo.py' not in uncovered


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
    """Only production/test routes count toward coverage — a doc/config route does not.

    A documentation route does not make a tracked .py covered; the .py must be
    matched by a production or test route.
    """

    class _DocOnlyRouteExtension(_MinimalExtension):
        def classify_globs(self) -> list[tuple[str, str]]:
            return [('scripts/*.py', ROLE_DOCUMENTATION)]

    _git_init_and_track(tmp_path, ['scripts/foo.py'])
    uncovered = validate_tree_completeness(str(tmp_path), [_DocOnlyRouteExtension()])
    # The .py is matched only by a documentation route, so it is still uncovered.
    assert 'scripts/foo.py' in uncovered
