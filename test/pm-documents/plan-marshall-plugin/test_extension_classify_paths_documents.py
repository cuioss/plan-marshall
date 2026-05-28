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
