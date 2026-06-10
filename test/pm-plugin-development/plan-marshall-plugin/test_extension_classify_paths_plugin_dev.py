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
# classify_globs() explicit routes (build_map seed source)
# =============================================================================
#
# classify_globs() returns explicit (pattern, role) routes — the concrete
# marketplace-anchored globs covering skill markdown (SKILL.md plus the
# workflow / standards / references subtrees), all under the documentation role.
# A single * spans / under fnmatch.fnmatch (the downstream
# manage-execution-manifest matcher), so marketplace/bundles/*/skills/*/standards/*.md
# covers every standards markdown beneath any bundle's skills. These routes are
# deliberately more specific than pm-documents's broad *.md route, so the seed
# aggregator's longest-glob-wins comparison routes the overlap here.

_BUILD_MAP_ROLES = frozenset({'production', 'test', 'documentation', 'config'})


def test_classify_globs_declares_marketplace_anchored_skill_routes():
    """The plugin-dev routes are the concrete marketplace-anchored skill-markdown globs."""
    routes = _ext.classify_globs()
    assert ('marketplace/bundles/*/skills/*/SKILL.md', 'documentation') in routes
    assert ('marketplace/bundles/*/skills/*/workflow/*.md', 'documentation') in routes
    assert ('marketplace/bundles/*/skills/*/standards/*.md', 'documentation') in routes
    assert ('marketplace/bundles/*/skills/*/references/*.md', 'documentation') in routes


def test_classify_globs_uses_only_resolved_roles():
    """Every route's second element is one of the four resolved build_map roles."""
    for _pattern, role in _ext.classify_globs():
        assert role in _BUILD_MAP_ROLES


def test_classify_globs_claims_only_documentation_role():
    """The plugin-dev domain declares only documentation routes."""
    roles = {role for _, role in _ext.classify_globs()}
    assert roles == {'documentation'}


def test_classify_globs_does_not_return_bare_suffix_vocabulary():
    """The routes carry concrete marketplace-anchored globs, not the old bare-suffix pair.

    Regression guard for the build_map redesign: the old portable
    `('.md', 'documentation')` by-location vocabulary is gone — explicit
    marketplace-anchored routes replace it, declared more specifically than
    pm-documents's broad *.md route so longest-glob-wins routes the overlap here.
    """
    patterns = {pattern for pattern, _ in _ext.classify_globs()}
    assert '.md' not in patterns


def test_classify_globs_uses_single_star_fnmatch_globs():
    """Routes are single-* fnmatch globs, never recursive ** forms."""
    for pattern, _role in _ext.classify_globs():
        assert '**' not in pattern, f'route {pattern!r} must use single-* fnmatch, not **'


def test_classify_globs_skill_route_covers_deep_standards_md():
    """The standards route matches a real bundle's standards markdown."""
    import fnmatch
    docs = [p for p, r in _ext.classify_globs() if r == 'documentation']
    sample = 'marketplace/bundles/plan-marshall/skills/phase-5-execute/standards/workflow.md'
    assert any(fnmatch.fnmatch(sample, p) for p in docs)


def test_classify_globs_is_nonempty():
    """The plugin-dev domain owns marketplace skill markdown, so the route set is non-empty."""
    assert _ext.classify_globs()
