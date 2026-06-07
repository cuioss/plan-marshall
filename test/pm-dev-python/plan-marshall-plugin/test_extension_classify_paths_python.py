#!/usr/bin/env python3
"""Tests for pm-dev-python Extension.classify_paths()."""

import importlib.util
from pathlib import Path

_EXT_PATH = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'pm-dev-python'
    / 'skills'
    / 'plan-marshall-plugin'
    / 'extension.py'
)


def _load_extension():
    spec = importlib.util.spec_from_file_location('pm_dev_python_extension', _EXT_PATH)
    assert spec is not None
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod.Extension()


_ext = _load_extension()


def test_scripts_py_is_production():
    result = _ext.classify_paths(['scripts/foo.py', 'scripts/sub/bar.py'])
    assert 'scripts/foo.py' in result['production']
    assert 'scripts/sub/bar.py' in result['production']


def test_test_py_is_test():
    result = _ext.classify_paths(['test/foo_test.py', 'tests/bar_test.py'])
    assert 'test/foo_test.py' in result['test']
    assert 'tests/bar_test.py' in result['test']


def test_pyproject_and_uv_lock_are_config():
    result = _ext.classify_paths(['pyproject.toml', 'uv.lock'])
    assert 'pyproject.toml' in result['config']
    assert 'uv.lock' in result['config']


def test_marshal_json_is_config():
    result = _ext.classify_paths(['.plan/marshal.json'])
    assert '.plan/marshal.json' in result['config']
    for role in ('production', 'test', 'documentation'):
        assert '.plan/marshal.json' not in result[role]


def test_py_outside_scripts_or_test_is_unclaimed():
    """A .py path outside scripts/ and test/ is intentionally omitted."""
    result = _ext.classify_paths(['random/foo.py'])
    for role in ('production', 'test', 'documentation', 'config'):
        assert 'random/foo.py' not in result[role]


def test_non_python_file_is_unclaimed():
    result = _ext.classify_paths(['README.md', 'foo.txt'])
    for role in ('production', 'test', 'documentation', 'config'):
        assert 'README.md' not in result[role]
        assert 'foo.txt' not in result[role]


def test_specificity_for_claimed_paths_is_positive():
    assert _ext.classify_path_specificity('scripts/foo.py', 'production') > 0
    assert _ext.classify_path_specificity('test/foo_test.py', 'test') > 0
    assert _ext.classify_path_specificity('pyproject.toml', 'config') > 0


def test_specificity_for_unclaimed_role_is_zero():
    assert _ext.classify_path_specificity('scripts/foo.py', 'test') == 0
    assert _ext.classify_path_specificity('random.txt', 'production') == 0


# =============================================================================
# build_class per claimed role
# =============================================================================

_BUILD_CLASSES = frozenset({'prod-compile', 'test-run', 'docs-validate', 'build-config-full', 'none'})


def test_production_path_build_class_is_prod_compile():
    assert _ext.classify_build_class('scripts/foo.py', 'production') == 'prod-compile'


def test_test_path_build_class_is_test_run():
    assert _ext.classify_build_class('test/foo_test.py', 'test') == 'test-run'


def test_config_path_build_class_is_build_config_full():
    assert _ext.classify_build_class('pyproject.toml', 'config') == 'build-config-full'


def test_every_claimed_path_yields_a_build_class_in_the_closed_set():
    """Each path this domain claims resolves to a member of the closed 5-value enum."""
    paths = [
        'scripts/foo.py',
        'test/foo_test.py',
        'pyproject.toml',
        'uv.lock',
        '.plan/marshal.json',
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
    assert inventory  # the python domain claims file types
    for glob, role in inventory:
        assert _ext.classify_build_class(glob, role) in _BUILD_CLASSES


def test_classify_globs_covers_production_test_config_roles():
    """The python glob inventory claims production, test, and config roles."""
    roles = {role for _, role in _ext.classify_globs()}
    assert roles == {'production', 'test', 'config'}
