#!/usr/bin/env python3
"""Tests for ExtensionBase.classify_paths() default no-op behavior.

Covers the default no-op contract and the subclass-override pattern.
The aggregator's longest-glob-wins overlap resolution and the unclaimed-path
warning are tested separately in test_manage_execution_manifest_*.py — this
module covers only the per-extension method contract.
"""

from extension_base import (  # type: ignore[import-not-found]
    BUILD_CLASS_BUILD_CONFIG_FULL,
    BUILD_CLASS_DOCS_VALIDATE,
    BUILD_CLASS_NONE,
    BUILD_CLASS_PROD_COMPILE,
    BUILD_CLASS_TEST_RUN,
    BUILD_CLASSES,
    ExtensionBase,
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
    """BUILD_CLASSES is exactly the closed 5-value enum, no more, no less."""
    assert BUILD_CLASSES == frozenset({
        'prod-compile',
        'test-run',
        'docs-validate',
        'build-config-full',
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


def test_default_classify_build_class_production_maps_to_prod_compile():
    """role=production derives prod-compile by default."""
    ext = _MinimalExtension()
    assert ext.classify_build_class('scripts/foo.py', 'production') == BUILD_CLASS_PROD_COMPILE


def test_default_classify_build_class_test_maps_to_test_run():
    """role=test derives test-run by default."""
    ext = _MinimalExtension()
    assert ext.classify_build_class('test/foo_test.py', 'test') == BUILD_CLASS_TEST_RUN


def test_default_classify_build_class_documentation_maps_to_docs_validate():
    """role=documentation derives docs-validate by default."""
    ext = _MinimalExtension()
    assert ext.classify_build_class('README.md', 'documentation') == BUILD_CLASS_DOCS_VALIDATE


def test_default_classify_build_class_config_maps_to_build_config_full():
    """role=config derives build-config-full by default."""
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
    while a regular production file still inherits the `prod-compile` default.
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
# classify_globs() accessor (build_map seed source)
# =============================================================================


class _GlobInventoryExtension(_MinimalExtension):
    """ExtensionBase subclass overriding classify_globs() with a small inventory."""

    def classify_globs(self) -> list[tuple[str, str]]:
        return [
            ('scripts/*.py', 'production'),
            ('test/**/*.py', 'test'),
            ('pyproject.toml', 'config'),
        ]


def test_default_classify_globs_returns_empty_list():
    """The base default classify_globs returns an empty list (domain claims nothing)."""
    ext = _MinimalExtension()
    assert ext.classify_globs() == []


def test_classify_paths_override_does_not_imply_globs_override():
    """A classify_paths override alone leaves classify_globs at the empty default.

    classify_globs is a separate accessor — overriding classify_paths does not
    auto-populate the glob inventory.
    """
    ext = _ClassifyingExtension()
    assert ext.classify_globs() == []


def test_subclass_classify_globs_returns_glob_role_inventory():
    """A classify_globs override returns the (glob, role) inventory verbatim."""
    ext = _GlobInventoryExtension()
    assert ext.classify_globs() == [
        ('scripts/*.py', 'production'),
        ('test/**/*.py', 'test'),
        ('pyproject.toml', 'config'),
    ]


def test_classify_globs_roles_resolve_to_build_classes():
    """Every role in the glob inventory derives a BUILD_CLASSES member via classify_build_class.

    This is exactly the lookup the build_map seed aggregator performs per entry.
    """
    ext = _GlobInventoryExtension()
    for glob, role in ext.classify_globs():
        assert ext.classify_build_class(glob, role) in BUILD_CLASSES
