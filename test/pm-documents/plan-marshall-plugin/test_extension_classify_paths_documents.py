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
# classify_globs() explicit routes (build_map seed source)
# =============================================================================
#
# classify_globs() returns explicit (pattern, role) routes — one broad per-
# suffix glob (*.md / *.adoc / *.asciidoc) under the documentation role. A
# single * spans / under fnmatch.fnmatch (the downstream
# manage-execution-manifest matcher), so *.md covers every markdown file
# anywhere in the tree. The longest-glob-wins overlap with pm-plugin-development's
# more-specific marketplace-skill routes is resolved by the seed aggregator.

_BUILD_MAP_ROLES = frozenset({'production', 'test', 'documentation', 'config'})


def test_classify_globs_declares_each_doc_suffix_as_documentation():
    """Each documentation suffix is declared as a broad *.suffix documentation route."""
    routes = _ext.classify_globs()
    assert ('*.md', 'documentation') in routes
    assert ('*.adoc', 'documentation') in routes
    assert ('*.asciidoc', 'documentation') in routes


def test_classify_globs_uses_only_resolved_roles():
    """Every route's second element is one of the four resolved build_map roles."""
    for _pattern, role in _ext.classify_globs():
        assert role in _BUILD_MAP_ROLES


def test_classify_globs_claims_only_documentation_role():
    """The documents domain declares only documentation routes."""
    roles = {role for _, role in _ext.classify_globs()}
    assert roles == {'documentation'}


def test_classify_globs_uses_single_star_fnmatch_globs():
    """Routes are single-* fnmatch globs, never recursive ** forms.

    Regression guard: the old by-location heuristic vocabulary (bare `.md`
    suffix + `documentation` heuristic) is gone — explicit *.md routes replace it.
    """
    for pattern, _role in _ext.classify_globs():
        assert '**' not in pattern, f'route {pattern!r} must use single-* fnmatch, not **'


def test_classify_globs_md_route_covers_nested_markdown():
    """The broad *.md documentation route matches a nested-directory markdown file."""
    import fnmatch
    docs = [p for p, r in _ext.classify_globs() if r == 'documentation']
    assert any(fnmatch.fnmatch('doc/developer/build.md', p) for p in docs)


def test_classify_globs_is_nonempty():
    """The documentation domain owns doc file types, so the route set is non-empty."""
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
