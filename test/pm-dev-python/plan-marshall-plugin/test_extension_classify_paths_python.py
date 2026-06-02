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
