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
