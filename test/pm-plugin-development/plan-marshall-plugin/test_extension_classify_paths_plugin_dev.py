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

_BUILD_CLASSES = frozenset({'prod-compile', 'test-run', 'docs-validate', 'build-config-full', 'none'})


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
# classify_globs() inventory (build_map seed source)
# =============================================================================


def test_classify_globs_derives_glob_role_pairs_from_patterns():
    """Tuple-shape extension: classify_globs derives (glob, role) from _CLASSIFY_PATTERNS."""
    expected = [(glob, role) for glob, role, _ in _ext._CLASSIFY_PATTERNS]
    assert _ext.classify_globs() == expected


def test_classify_globs_roles_resolve_to_build_classes():
    """Every (glob, role) in the inventory derives a build_class in the closed set."""
    inventory = _ext.classify_globs()
    assert inventory  # the plugin-dev domain claims marketplace skill markdown
    for glob, role in inventory:
        assert _ext.classify_build_class(glob, role) in _BUILD_CLASSES


def test_classify_globs_claims_only_documentation_role():
    """The plugin-dev glob inventory claims only the documentation role."""
    roles = {role for _, role in _ext.classify_globs()}
    assert roles == {'documentation'}
