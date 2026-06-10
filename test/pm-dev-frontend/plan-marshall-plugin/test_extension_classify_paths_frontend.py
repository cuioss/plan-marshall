#!/usr/bin/env python3
"""Tests for pm-dev-frontend Extension.classify_paths()."""

import importlib.util
from pathlib import Path

_EXT_PATH = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'pm-dev-frontend'
    / 'skills'
    / 'plan-marshall-plugin'
    / 'extension.py'
)


def _load_extension():
    spec = importlib.util.spec_from_file_location('pm_dev_frontend_extension', _EXT_PATH)
    assert spec is not None
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod.Extension()


_ext = _load_extension()


def test_js_files_are_production():
    result = _ext.classify_paths(['src/foo.js', 'src/bar.mjs', 'src/baz.ts', 'src/qux.tsx', 'src/quux.jsx'])
    assert 'src/foo.js' in result['production']
    assert 'src/bar.mjs' in result['production']
    assert 'src/baz.ts' in result['production']
    assert 'src/qux.tsx' in result['production']
    assert 'src/quux.jsx' in result['production']


def test_spec_and_test_files_are_test():
    result = _ext.classify_paths([
        'src/foo.spec.js',
        'src/foo.test.ts',
        'src/foo.spec.tsx',
    ])
    assert 'src/foo.spec.js' in result['test']
    assert 'src/foo.test.ts' in result['test']
    assert 'src/foo.spec.tsx' in result['test']


def test_config_files_are_config():
    result = _ext.classify_paths([
        'package.json',
        'tsconfig.json',
        'eslint.config.js',
        'eslint.config.mjs',
    ])
    assert 'package.json' in result['config']
    assert 'tsconfig.json' in result['config']
    assert 'eslint.config.js' in result['config']
    assert 'eslint.config.mjs' in result['config']


def test_non_js_file_is_unclaimed():
    result = _ext.classify_paths(['README.md', 'foo.css'])
    for role in ('production', 'test', 'documentation', 'config'):
        assert 'README.md' not in result[role]
        assert 'foo.css' not in result[role]


def test_production_does_not_include_test_files():
    """A .spec.js file must NOT be classified as production."""
    result = _ext.classify_paths(['src/foo.spec.js'])
    assert 'src/foo.spec.js' not in result['production']


# =============================================================================
# build_class per claimed role
# =============================================================================

_BUILD_CLASSES = frozenset({'compile', 'module-tests', 'docs-validate', 'verify', 'none'})


def test_production_path_build_class_is_compile():
    assert _ext.classify_build_class('src/foo.js', 'production') == 'compile'


def test_test_path_build_class_is_module_tests():
    assert _ext.classify_build_class('src/foo.spec.js', 'test') == 'module-tests'


def test_config_path_build_class_is_verify():
    assert _ext.classify_build_class('package.json', 'config') == 'verify'


def test_every_claimed_path_yields_a_build_class_in_the_closed_set():
    """Each path this domain claims resolves to a member of the closed 5-value enum."""
    paths = [
        'src/foo.js',
        'src/foo.spec.js',
        'src/foo.test.ts',
        'package.json',
        'tsconfig.json',
    ]
    claims = _ext.classify_paths(paths)
    for role, claimed in claims.items():
        for path in claimed:
            assert _ext.classify_build_class(path, role) in _BUILD_CLASSES


# =============================================================================
# classify_globs() explicit routes (build_map seed source)
# =============================================================================
#
# classify_globs() returns explicit (pattern, role) routes — single-* fnmatch
# globs paired with a resolved role. For each JS/TS suffix the domain declares
# a broad production route (e.g. *.js, where a single * spans /) plus the more-
# specific colocated-test routes (*.spec.js / *.test.js). The seed aggregator's
# longest-glob-wins specificity routes a .spec./.test. file to test even though
# the broad production glob also matches it. Config files are exact basenames.

_BUILD_MAP_ROLES = frozenset({'production', 'test', 'documentation', 'config'})


def test_classify_globs_declares_each_js_ts_suffix_as_production():
    """Each JS/TS suffix is declared as a broad production route."""
    routes = _ext.classify_globs()
    for ext in ('.js', '.mjs', '.ts', '.tsx', '.jsx'):
        assert (f'*{ext}', 'production') in routes


def test_classify_globs_declares_colocated_test_routes():
    """The .spec./.test. infix forms per suffix are declared as test routes."""
    routes = _ext.classify_globs()
    assert ('*.spec.js', 'test') in routes
    assert ('*.test.js', 'test') in routes
    assert ('*.spec.ts', 'test') in routes
    assert ('*.test.tsx', 'test') in routes


def test_classify_globs_declares_config_basenames():
    """The JS toolchain config files are declared by exact basename under config."""
    routes = _ext.classify_globs()
    assert ('package.json', 'config') in routes
    assert ('tsconfig.json', 'config') in routes


def test_classify_globs_uses_only_resolved_roles():
    """Every route's second element is one of the four resolved build_map roles."""
    for _pattern, role in _ext.classify_globs():
        assert role in _BUILD_MAP_ROLES


def test_classify_globs_uses_single_star_fnmatch_globs():
    """Routes are single-* fnmatch globs, never recursive ** forms.

    Regression guard: the old by-location heuristic vocabulary (bare `.js`
    suffix + `production-by-location`) and the malformed `*.spec.*.js` double-*
    forms are gone — clean single-* routes replace them.
    """
    for pattern, _role in _ext.classify_globs():
        assert '**' not in pattern, f'route {pattern!r} must use single-* fnmatch, not **'
        assert pattern.count('*') <= 1, f'route {pattern!r} must carry at most one *'


def test_classify_globs_production_route_covers_nested_source():
    """The broad *.js production route matches a nested-directory source (single * spans /)."""
    import fnmatch
    prod = [p for p, r in _ext.classify_globs() if r == 'production']
    assert any(fnmatch.fnmatch('src/components/foo.js', p) for p in prod)


def test_classify_globs_is_nonempty():
    """The frontend domain owns buildable file types, so the route set is non-empty."""
    assert _ext.classify_globs()
