#!/usr/bin/env python3
"""Tests for pm-documents Extension.classify_paths()."""

import importlib.util
from pathlib import Path

_EXT_PATH = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'pm-documents'
    / 'skills'
    / 'plan-marshall-plugin'
    / 'extension.py'
)


def _load_extension():
    spec = importlib.util.spec_from_file_location('pm_documents_extension', _EXT_PATH)
    assert spec is not None
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod.Extension()


_ext = _load_extension()


def test_md_files_are_documentation():
    result = _ext.classify_paths(['README.md', 'docs/intro.md'])
    assert 'README.md' in result['documentation']
    assert 'docs/intro.md' in result['documentation']


def test_adoc_files_are_documentation():
    result = _ext.classify_paths(['docs/foo.adoc', 'manual.asciidoc'])
    assert 'docs/foo.adoc' in result['documentation']
    assert 'manual.asciidoc' in result['documentation']


def test_marketplace_skill_md_is_also_claimed():
    """pm-documents claims marketplace skill .md too (low specificity);
    aggregator's longest-glob-wins routes those paths to
    pm-plugin-development at the plan-wide layer."""
    path = 'marketplace/bundles/foo/skills/bar/SKILL.md'
    result = _ext.classify_paths([path])
    assert path in result['documentation']


def test_non_doc_file_is_unclaimed():
    result = _ext.classify_paths(['scripts/foo.py', 'pom.xml'])
    for role in ('production', 'test', 'documentation', 'config'):
        assert 'scripts/foo.py' not in result[role]
        assert 'pom.xml' not in result[role]


def test_specificity_for_documentation_is_zero():
    """pm-documents's *.md glob has zero explicit segments."""
    assert _ext.classify_path_specificity('README.md', 'documentation') == 0


# =============================================================================
# build_class per claimed role
# =============================================================================

_BUILD_CLASSES = frozenset({'compile', 'module-tests', 'docs-validate', 'verify', 'none'})


def test_documentation_path_build_class_is_docs_validate():
    assert _ext.classify_build_class('README.md', 'documentation') == 'docs-validate'
    assert _ext.classify_build_class('docs/foo.adoc', 'documentation') == 'docs-validate'


def test_every_claimed_path_yields_a_build_class_in_the_closed_set():
    """Each path this domain claims resolves to a member of the closed 5-value enum."""
    paths = [
        'README.md',
        'docs/intro.md',
        'docs/foo.adoc',
        'manual.asciidoc',
    ]
    claims = _ext.classify_paths(paths)
    for role, claimed in claims.items():
        for path in claimed:
            assert _ext.classify_build_class(path, role) in _BUILD_CLASSES


# =============================================================================
# classify_globs() vocabulary (build_map seed source)
# =============================================================================
#
# classify_globs() now returns the portable (suffix, role_heuristic) vocabulary
# consumed by the script-shared tree-deriver — NOT literal path-globs. Each doc
# suffix is declared under the location-agnostic `documentation` heuristic.

_ROLE_HEURISTICS = frozenset(
    {'production-by-location', 'test-by-location', 'documentation', 'config'}
)


def test_classify_globs_declares_each_doc_suffix_under_documentation():
    """Each documentation suffix is declared under the documentation heuristic."""
    vocabulary = _ext.classify_globs()
    assert ('.md', 'documentation') in vocabulary
    assert ('.adoc', 'documentation') in vocabulary
    assert ('.asciidoc', 'documentation') in vocabulary


def test_classify_globs_uses_only_role_heuristic_names():
    """Every vocabulary tuple's second element is a role-heuristic name."""
    for _suffix, role_heuristic in _ext.classify_globs():
        assert role_heuristic in _ROLE_HEURISTICS


def test_classify_globs_claims_only_documentation_heuristic():
    """The documents vocabulary uses only the documentation heuristic."""
    heuristics = {heuristic for _, heuristic in _ext.classify_globs()}
    assert heuristics == {'documentation'}


def test_classify_globs_does_not_return_literal_path_globs():
    """The vocabulary carries bare suffixes, not the old `*.md` synthesized globs."""
    suffixes = {suffix for suffix, _ in _ext.classify_globs()}
    for stale in ('*.md', '*.adoc', '*.asciidoc'):
        assert stale not in suffixes


def test_classify_globs_is_nonempty():
    """The documentation domain owns doc file types, so the vocabulary is non-empty."""
    assert _ext.classify_globs()


# =============================================================================
# provides_recipes() registration
# =============================================================================


def _recipe_by_key(key: str) -> dict | None:
    for recipe in _ext.provides_recipes():
        if recipe['key'] == key:
            return recipe
    return None


def test_provides_recipes_includes_verify_ascii_diagrams():
    """The verify-ascii-diagrams recipe is registered with the correct skill
    notation and default change type."""
    recipe = _recipe_by_key('verify-ascii-diagrams')
    assert recipe is not None, 'verify-ascii-diagrams recipe not registered'
    assert recipe['skill'] == 'pm-documents:recipe-verify-ascii-diagrams'
    assert recipe['default_change_type'] == 'tech_debt'
    assert recipe['scope'] == 'codebase_wide'


def test_provides_recipes_registers_all_three_documentation_recipes():
    """All three documentation recipes are registered by key."""
    keys = {recipe['key'] for recipe in _ext.provides_recipes()}
    assert keys == {'doc-verify', 'verify-architecture-diagrams', 'verify-ascii-diagrams'}


def test_provides_recipes_entries_have_required_fields():
    """Every recipe entry carries the full ext-point-recipe field set."""
    required = {'key', 'name', 'description', 'skill', 'default_change_type', 'scope'}
    for recipe in _ext.provides_recipes():
        assert required.issubset(recipe.keys()), f'missing fields in {recipe.get("key")}'
