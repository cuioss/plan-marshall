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

_BUILD_CLASSES = frozenset({'prod-compile', 'test-run', 'docs-validate', 'build-config-full', 'none'})


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
# classify_globs() inventory (build_map seed source)
# =============================================================================


def test_classify_globs_synthesizes_doc_suffix_globs():
    """Hand-rolled extension: classify_globs returns one *suffix glob per doc suffix."""
    inventory = _ext.classify_globs()
    assert ('*.md', 'documentation') in inventory
    assert ('*.adoc', 'documentation') in inventory
    assert ('*.asciidoc', 'documentation') in inventory


def test_classify_globs_roles_resolve_to_build_classes():
    """Every (glob, role) in the inventory derives a build_class in the closed set."""
    inventory = _ext.classify_globs()
    assert inventory
    for glob, role in inventory:
        assert _ext.classify_build_class(glob, role) in _BUILD_CLASSES


def test_classify_globs_claims_only_documentation_role():
    """The documents glob inventory claims only the documentation role."""
    roles = {role for _, role in _ext.classify_globs()}
    assert roles == {'documentation'}
