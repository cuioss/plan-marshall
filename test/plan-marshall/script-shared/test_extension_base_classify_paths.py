#!/usr/bin/env python3
"""Tests for ExtensionBase.classify_paths() default no-op behavior.

Covers the default no-op contract and the subclass-override pattern.
The aggregator's longest-glob-wins overlap resolution and the unclaimed-path
warning are tested separately in test_manage_execution_manifest_*.py — this
module covers only the per-extension method contract.
"""

from extension_base import ExtensionBase  # type: ignore[import-not-found]


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
