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

_BUILD_CLASSES = frozenset({'prod-compile', 'test-run', 'docs-validate', 'build-config-full', 'none'})


def test_production_path_build_class_is_prod_compile():
    assert _ext.classify_build_class('src/foo.js', 'production') == 'prod-compile'


def test_test_path_build_class_is_test_run():
    assert _ext.classify_build_class('src/foo.spec.js', 'test') == 'test-run'


def test_config_path_build_class_is_build_config_full():
    assert _ext.classify_build_class('package.json', 'config') == 'build-config-full'


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
# classify_globs() inventory (build_map seed source)
# =============================================================================


def test_classify_globs_synthesizes_explicit_glob_inventory():
    """Hand-rolled extension: classify_globs returns explicit globs from the rules.

    The inventory mirrors _match_classify: config filenames + the eslint.config.*
    prefix family, test patterns (*.spec.* / *.test.* paired with each JS/TS
    suffix), and production source (each JS/TS suffix).
    """
    inventory = _ext.classify_globs()
    assert ('package.json', 'config') in inventory
    assert ('tsconfig.json', 'config') in inventory
    assert ('eslint.config.*', 'config') in inventory
    assert ('*.spec.*.js', 'test') in inventory
    assert ('*.test.*.ts', 'test') in inventory
    assert ('*.js', 'production') in inventory
    assert ('*.tsx', 'production') in inventory


def test_classify_globs_roles_resolve_to_build_classes():
    """Every (glob, role) in the inventory derives a build_class in the closed set."""
    inventory = _ext.classify_globs()
    assert inventory
    for glob, role in inventory:
        assert _ext.classify_build_class(glob, role) in _BUILD_CLASSES


def test_classify_globs_covers_production_test_config_roles():
    """The frontend glob inventory claims production, test, and config roles."""
    roles = {role for _, role in _ext.classify_globs()}
    assert roles == {'production', 'test', 'config'}
