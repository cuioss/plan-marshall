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
# classify_globs() vocabulary (build_map seed source)
# =============================================================================
#
# classify_globs() now returns the portable (suffix, role_heuristic) vocabulary
# consumed by the script-shared tree-deriver — NOT literal path-globs. Each
# JS/TS suffix is declared under BOTH production-by-location and
# test-by-location; the deriver splits them per file via the .spec./.test.
# infix and the test-root convention.

_ROLE_HEURISTICS = frozenset(
    {'production-by-location', 'test-by-location', 'documentation', 'config'}
)


def test_classify_globs_declares_each_js_ts_suffix_under_both_location_heuristics():
    """Each JS/TS suffix appears under production-by-location AND test-by-location."""
    vocabulary = _ext.classify_globs()
    for ext in ('.js', '.mjs', '.ts', '.tsx', '.jsx'):
        assert (ext, 'production-by-location') in vocabulary
        assert (ext, 'test-by-location') in vocabulary


def test_classify_globs_declares_config_basenames():
    """The JS toolchain config files are declared by exact basename under config."""
    vocabulary = _ext.classify_globs()
    assert ('package.json', 'config') in vocabulary
    assert ('tsconfig.json', 'config') in vocabulary


def test_classify_globs_uses_only_role_heuristic_names():
    """Every vocabulary tuple's second element is a role-heuristic name."""
    for _suffix, role_heuristic in _ext.classify_globs():
        assert role_heuristic in _ROLE_HEURISTICS


def test_classify_globs_does_not_return_literal_path_globs():
    """The vocabulary carries bare suffixes, not the old synthesized literal globs.

    Regression guard: the old `*.js` / `*.spec.*.js` / `eslint.config.*` literal
    globs are gone — bare suffixes plus a location heuristic replace them.
    """
    suffixes = {suffix for suffix, _ in _ext.classify_globs()}
    for stale in ('*.js', '*.tsx', '*.spec.*.js', '*.test.*.ts', 'eslint.config.*'):
        assert stale not in suffixes


def test_classify_globs_is_nonempty():
    """The frontend domain owns buildable file types, so the vocabulary is non-empty."""
    assert _ext.classify_globs()
