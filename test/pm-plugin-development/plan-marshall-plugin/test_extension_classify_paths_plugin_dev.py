#!/usr/bin/env python3
"""Tests for pm-plugin-development Extension.classify_paths()."""

import importlib.util
from pathlib import Path

_EXT_PATH = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'pm-plugin-development'
    / 'skills'
    / 'plan-marshall-plugin'
    / 'extension.py'
)


def _load_extension():
    spec = importlib.util.spec_from_file_location('pm_plugin_development_extension', _EXT_PATH)
    assert spec is not None
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod.Extension()


_ext = _load_extension()


def test_skill_md_in_marketplace_is_documentation():
    path = 'marketplace/bundles/foo/skills/bar/SKILL.md'
    result = _ext.classify_paths([path])
    assert path in result['documentation']


def test_workflow_md_in_marketplace_is_documentation():
    path = 'marketplace/bundles/foo/skills/bar/workflow/step.md'
    result = _ext.classify_paths([path])
    assert path in result['documentation']


def test_standards_md_in_marketplace_is_documentation():
    path = 'marketplace/bundles/foo/skills/bar/standards/contract.md'
    result = _ext.classify_paths([path])
    assert path in result['documentation']


def test_references_md_in_marketplace_is_documentation():
    path = 'marketplace/bundles/foo/skills/bar/references/glossary.md'
    result = _ext.classify_paths([path])
    assert path in result['documentation']


def test_regular_md_outside_marketplace_is_unclaimed():
    """README.md at repo root is NOT a marketplace skill markdown."""
    result = _ext.classify_paths(['README.md', 'docs/intro.md'])
    for role in ('production', 'test', 'documentation', 'config'):
        assert 'README.md' not in result[role]
        assert 'docs/intro.md' not in result[role]


def test_specificity_for_skill_md_is_higher_than_pm_documents():
    """pm-plugin-development must report a non-zero specificity for marketplace
    skill markdown so the aggregator's longest-glob-wins routes the overlap
    to this extension."""
    path = 'marketplace/bundles/foo/skills/bar/SKILL.md'
    assert _ext.classify_path_specificity(path, 'documentation') > 0


def test_integration_overlap_resolution_pm_plugin_dev_wins():
    """End-to-end check: when both pm-documents and pm-plugin-development
    claim the same marketplace SKILL.md path, pm-plugin-development's
    higher specificity wins."""
    from importlib.util import module_from_spec, spec_from_file_location

    docs_path = (
        Path(__file__).parent.parent.parent.parent
        / 'marketplace'
        / 'bundles'
        / 'pm-documents'
        / 'skills'
        / 'plan-marshall-plugin'
        / 'extension.py'
    )
    spec = spec_from_file_location('pm_documents_extension_ovl', docs_path)
    assert spec is not None
    docs_mod = module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(docs_mod)
    docs_ext = docs_mod.Extension()

    path = 'marketplace/bundles/foo/skills/bar/SKILL.md'
    plugin_spec = _ext.classify_path_specificity(path, 'documentation')
    docs_spec = docs_ext.classify_path_specificity(path, 'documentation')
    assert plugin_spec > docs_spec, (
        f'pm-plugin-development specificity ({plugin_spec}) must beat '
        f'pm-documents specificity ({docs_spec}) on {path}'
    )


# =============================================================================
# build_class per claimed role
# =============================================================================

_BUILD_CLASSES = frozenset({'compile', 'module-tests', 'docs-validate', 'verify', 'none'})


def test_skill_md_build_class_is_docs_validate():
    """pm-plugin-development claims only the documentation role, which derives
    docs-validate via the ExtensionBase default."""
    path = 'marketplace/bundles/foo/skills/bar/SKILL.md'
    assert _ext.classify_build_class(path, 'documentation') == 'docs-validate'


def test_every_claimed_path_yields_a_build_class_in_the_closed_set():
    """Each path this domain claims resolves to a member of the closed 5-value enum."""
    paths = [
        'marketplace/bundles/foo/skills/bar/SKILL.md',
        'marketplace/bundles/foo/skills/bar/workflow/step.md',
        'marketplace/bundles/foo/skills/bar/standards/contract.md',
        'marketplace/bundles/foo/skills/bar/references/glossary.md',
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
# consumed by the script-shared tree-deriver — NOT literal path-globs.
# Marketplace skill markdown is plain `.md` under the documentation heuristic;
# the deriver scans the tree and emits the concrete marketplace-anchored globs.
# The longest-glob-wins overlap with pm-documents is resolved by the seed
# aggregator's specificity comparison, not by this vocabulary.

_ROLE_HEURISTICS = frozenset(
    {'production-by-location', 'test-by-location', 'documentation', 'config'}
)


def test_classify_globs_declares_md_under_documentation():
    """The plugin-dev vocabulary is a single .md / documentation entry."""
    assert _ext.classify_globs() == [('.md', 'documentation')]


def test_classify_globs_uses_only_role_heuristic_names():
    """Every vocabulary tuple's second element is a role-heuristic name."""
    for _suffix, role_heuristic in _ext.classify_globs():
        assert role_heuristic in _ROLE_HEURISTICS


def test_classify_globs_does_not_return_marketplace_anchored_literal_globs():
    """The vocabulary carries a bare `.md` suffix, not the old marketplace-anchored globs.

    Regression guard: the old literal globs
    (`marketplace/bundles/*/skills/*/SKILL.md`, etc.) are gone — the tree-deriver
    now produces those concrete globs from the real tree, so the vocabulary only
    declares the portable `.md` / documentation pair.
    """
    suffixes = {suffix for suffix, _ in _ext.classify_globs()}
    for stale in (
        'marketplace/bundles/*/skills/*/SKILL.md',
        'marketplace/bundles/*/skills/*/standards/*.md',
    ):
        assert stale not in suffixes


def test_classify_globs_is_nonempty():
    """The plugin-dev domain owns marketplace skill markdown, so the vocabulary is non-empty."""
    assert _ext.classify_globs()
