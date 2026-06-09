#!/usr/bin/env python3
"""Tests for ExtensionBase.classify_paths(), classify_globs(), and the
base-lib tree-glob deriver ``derive_globs_from_tree``.

Covers three concerns of the file-to-build contract that live in the
``script-shared`` ``extension_base`` module:

1. ``classify_paths()`` — the default no-op contract and the subclass-override
   pattern (the change-set classification path).
2. ``classify_build_class()`` — the per-(path, role) build_class default map.
3. ``classify_globs()`` + ``derive_globs_from_tree()`` — the portable
   ``(suffix, role_heuristic)`` vocabulary accessor and the base-lib tree
   deriver that scans the real project tree and emits concrete, complete-by-
   construction globs (so production ``.py`` files outside ``scripts/`` are
   covered because they exist in the tree, not because an author guessed a
   glob).

The aggregator's longest-glob-wins overlap resolution and the unclaimed-path
warning are tested separately in test_manage_execution_manifest_*.py — this
module covers only the per-extension method contract and the base deriver.
"""

import fnmatch

from extension_base import (  # type: ignore[import-not-found]
    BUILD_CLASS_BUILD_CONFIG_FULL,
    BUILD_CLASS_DOCS_VALIDATE,
    BUILD_CLASS_NONE,
    BUILD_CLASS_PROD_COMPILE,
    BUILD_CLASS_TEST_RUN,
    BUILD_CLASSES,
    ROLE_HEURISTIC_CONFIG,
    ROLE_HEURISTIC_DOCUMENTATION,
    ROLE_HEURISTIC_PRODUCTION_BY_LOCATION,
    ROLE_HEURISTIC_TEST_BY_LOCATION,
    ROLE_HEURISTICS,
    ExtensionBase,
    derive_globs_from_tree,
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
# Role-heuristic vocabulary constants
# =============================================================================


def test_role_heuristics_is_the_closed_four_value_set():
    """ROLE_HEURISTICS is exactly the four heuristic names, no more, no less."""
    assert ROLE_HEURISTICS == frozenset({
        'production-by-location',
        'test-by-location',
        'documentation',
        'config',
    })
    assert len(ROLE_HEURISTICS) == 4


def test_role_heuristic_named_constants_are_members():
    """Each named ROLE_HEURISTIC_* constant is a member of ROLE_HEURISTICS."""
    for value in (
        ROLE_HEURISTIC_PRODUCTION_BY_LOCATION,
        ROLE_HEURISTIC_TEST_BY_LOCATION,
        ROLE_HEURISTIC_DOCUMENTATION,
        ROLE_HEURISTIC_CONFIG,
    ):
        assert value in ROLE_HEURISTICS


# =============================================================================
# classify_globs() accessor — portable (suffix, role_heuristic) vocabulary
# =============================================================================


class _VocabularyExtension(_MinimalExtension):
    """ExtensionBase subclass overriding classify_globs() with a portable vocabulary."""

    def classify_globs(self) -> list[tuple[str, str]]:
        return [
            ('.py', ROLE_HEURISTIC_PRODUCTION_BY_LOCATION),
            ('.py', ROLE_HEURISTIC_TEST_BY_LOCATION),
            ('pyproject.toml', ROLE_HEURISTIC_CONFIG),
        ]


def test_default_classify_globs_returns_empty_list():
    """The base default classify_globs returns an empty list (domain claims nothing)."""
    ext = _MinimalExtension()
    assert ext.classify_globs() == []


def test_classify_paths_override_does_not_imply_globs_override():
    """A classify_paths override alone leaves classify_globs at the empty default.

    classify_globs is a separate accessor — overriding classify_paths does not
    auto-populate the vocabulary.
    """
    ext = _ClassifyingExtension()
    assert ext.classify_globs() == []


def test_subclass_classify_globs_returns_vocabulary_verbatim():
    """A classify_globs override returns the (suffix, role_heuristic) vocabulary verbatim."""
    ext = _VocabularyExtension()
    assert ext.classify_globs() == [
        ('.py', 'production-by-location'),
        ('.py', 'test-by-location'),
        ('pyproject.toml', 'config'),
    ]


def test_classify_globs_returns_role_heuristics_not_resolved_roles():
    """The vocabulary uses role-heuristic names, NOT the resolved four roles.

    A vocabulary tuple's second element is a ROLE_HEURISTICS member
    (``production-by-location`` etc.), never a bare ``production`` /
    ``test`` resolved-role string — the deriver resolves the heuristic to a
    role, the vocabulary does not pre-resolve it.
    """
    ext = _VocabularyExtension()
    for _suffix, role_heuristic in ext.classify_globs():
        assert role_heuristic in ROLE_HEURISTICS


# =============================================================================
# derive_globs_from_tree() — base-lib tree deriver
# =============================================================================


def _write_tree(root, rel_paths: list[str]) -> None:
    """Create each repo-relative path under ``root`` as an empty file."""
    for rel in rel_paths:
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text('')


def _matches_any(path: str, globs: list[str]) -> bool:
    """Return True when ``path`` matches at least one derived glob."""
    return any(fnmatch.fnmatchcase(path, g) for g in globs)


def test_derive_globs_returns_empty_dict_for_no_extensions(tmp_path):
    """No registered extensions ⇒ no derived globs."""
    _write_tree(tmp_path, ['scripts/foo.py'])
    assert derive_globs_from_tree(str(tmp_path), []) == {}


def test_derive_globs_skips_extension_with_empty_vocabulary(tmp_path):
    """An extension whose classify_globs() is empty contributes nothing."""
    _write_tree(tmp_path, ['scripts/foo.py'])
    # _MinimalExtension keeps the base empty-vocabulary default.
    assert derive_globs_from_tree(str(tmp_path), [_MinimalExtension()]) == {}


def test_derive_globs_keys_result_by_domain_key(tmp_path):
    """The derived dict is keyed by the extension's first domain key."""
    _write_tree(tmp_path, ['scripts/foo.py'])
    derived = derive_globs_from_tree(str(tmp_path), [_VocabularyExtension()])
    assert set(derived.keys()) == {'minimal'}


def test_derive_globs_covers_production_py_outside_scripts(tmp_path):
    """A production .py outside scripts/ is covered — the regression this fixes.

    The vocabulary is portable (``.py`` + production-by-location); the deriver
    scans the real tree and emits a glob anchored at the file's parent dir, so
    a production file the author never anticipated (``pkg/sub/mod.py``) is
    caught because it exists in the tree.
    """
    _write_tree(tmp_path, ['pkg/sub/mod.py'])
    derived = derive_globs_from_tree(str(tmp_path), [_VocabularyExtension()])
    prod_globs = [glob for glob, role in derived['minimal'] if role == 'production']
    assert _matches_any('pkg/sub/mod.py', prod_globs)


def test_derive_globs_splits_production_and_test_by_location(tmp_path):
    """The .py vocabulary splits production vs test by the test-root predicate."""
    _write_tree(tmp_path, ['pkg/mod.py', 'test/pkg/test_mod.py'])
    derived = derive_globs_from_tree(str(tmp_path), [_VocabularyExtension()])
    entries = derived['minimal']
    prod_globs = [glob for glob, role in entries if role == 'production']
    test_globs = [glob for glob, role in entries if role == 'test']
    assert _matches_any('pkg/mod.py', prod_globs)
    assert not _matches_any('pkg/mod.py', test_globs)
    assert _matches_any('test/pkg/test_mod.py', test_globs)
    assert not _matches_any('test/pkg/test_mod.py', prod_globs)


def test_derive_globs_emits_exact_path_for_config_basename(tmp_path):
    """An exact-name config entry derives the exact path (not a *suffix glob)."""
    _write_tree(tmp_path, ['pyproject.toml', 'sub/pyproject.toml'])
    derived = derive_globs_from_tree(str(tmp_path), [_VocabularyExtension()])
    config_globs = [glob for glob, role in derived['minimal'] if role == 'config']
    assert 'pyproject.toml' in config_globs
    assert 'sub/pyproject.toml' in config_globs


def test_derive_globs_prunes_vcs_and_cache_dirs(tmp_path):
    """The deriver never descends into pruned dirs (.git, __pycache__, target, ...)."""
    _write_tree(tmp_path, [
        'pkg/real.py',
        '.git/hooks/fake.py',
        '__pycache__/cached.py',
        'target/built.py',
        '.venv/lib/dep.py',
    ])
    derived = derive_globs_from_tree(str(tmp_path), [_VocabularyExtension()])
    prod_globs = [glob for glob, role in derived['minimal'] if role == 'production']
    assert _matches_any('pkg/real.py', prod_globs)
    # Files under pruned dirs are never scanned, so no glob is anchored at them.
    for pruned in ('.git/hooks/fake.py', '__pycache__/cached.py', 'target/built.py', '.venv/lib/dep.py'):
        assert not _matches_any(pruned, prod_globs), f'{pruned} should be pruned'


def test_derive_globs_deduplicates_globs(tmp_path):
    """Two production files in the same dir collapse to one derived glob."""
    _write_tree(tmp_path, ['pkg/a.py', 'pkg/b.py'])
    derived = derive_globs_from_tree(str(tmp_path), [_VocabularyExtension()])
    prod_globs = [glob for glob, role in derived['minimal'] if role == 'production']
    assert len(prod_globs) == len(set(prod_globs))
    # Both files live in pkg/, so a single pkg/*.py glob covers both.
    assert _matches_any('pkg/a.py', prod_globs)
    assert _matches_any('pkg/b.py', prod_globs)


def test_derive_globs_entries_are_sorted_and_deterministic(tmp_path):
    """The per-domain entries are emitted in deterministic sorted order."""
    _write_tree(tmp_path, ['z/mod.py', 'a/mod.py', 'm/mod.py'])
    first = derive_globs_from_tree(str(tmp_path), [_VocabularyExtension()])
    second = derive_globs_from_tree(str(tmp_path), [_VocabularyExtension()])
    assert first == second
    assert first['minimal'] == sorted(first['minimal'])


def test_derive_globs_skips_extension_without_domain_key(tmp_path):
    """An extension with a vocabulary but no resolvable domain key is omitted."""

    class _NoDomainKeyExtension(_VocabularyExtension):
        def get_skill_domains(self) -> list[dict]:
            return []

    _write_tree(tmp_path, ['pkg/mod.py'])
    derived = derive_globs_from_tree(str(tmp_path), [_NoDomainKeyExtension()])
    assert derived == {}


def test_derive_globs_documentation_heuristic_is_location_agnostic(tmp_path):
    """A documentation-heuristic suffix is claimed regardless of where it sits."""

    class _DocExtension(_MinimalExtension):
        def classify_globs(self) -> list[tuple[str, str]]:
            return [('.md', ROLE_HEURISTIC_DOCUMENTATION)]

    _write_tree(tmp_path, ['README.md', 'docs/intro.md', 'test/notes.md'])
    derived = derive_globs_from_tree(str(tmp_path), [_DocExtension()])
    doc_globs = [glob for glob, role in derived['minimal'] if role == 'documentation']
    # All three .md files are claimed under documentation — even the one under test/.
    assert _matches_any('README.md', doc_globs)
    assert _matches_any('docs/intro.md', doc_globs)
    assert _matches_any('test/notes.md', doc_globs)


def test_derive_globs_ignores_unknown_role_heuristic(tmp_path):
    """A vocabulary tuple with a non-ROLE_HEURISTICS name contributes nothing."""

    class _BadHeuristicExtension(_MinimalExtension):
        def classify_globs(self) -> list[tuple[str, str]]:
            return [('.py', 'not-a-real-heuristic')]

    _write_tree(tmp_path, ['pkg/mod.py'])
    derived = derive_globs_from_tree(str(tmp_path), [_BadHeuristicExtension()])
    assert derived == {}


def test_derive_globs_survives_extension_raising_in_classify_globs(tmp_path):
    """A broken extension is skipped, not allowed to abort the whole derivation."""

    class _RaisingExtension(_MinimalExtension):
        def classify_globs(self) -> list[tuple[str, str]]:
            raise RuntimeError('boom')

    _write_tree(tmp_path, ['pkg/mod.py'])
    derived = derive_globs_from_tree(
        str(tmp_path), [_RaisingExtension(), _VocabularyExtension()]
    )
    # The raising extension is skipped; the well-behaved one still contributes.
    assert 'minimal' in derived


def test_derive_globs_every_entry_role_resolves_to_a_build_class(tmp_path):
    """Each (glob, role) the deriver emits resolves to a BUILD_CLASSES member.

    This is exactly the per-entry lookup the build_map seed aggregator performs.
    """
    _write_tree(tmp_path, ['pkg/mod.py', 'test/test_mod.py', 'pyproject.toml'])
    ext = _VocabularyExtension()
    derived = derive_globs_from_tree(str(tmp_path), [ext])
    for _glob, role in derived['minimal']:
        assert ext.classify_build_class(_glob, role) in BUILD_CLASSES
