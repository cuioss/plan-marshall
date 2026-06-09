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

_BUILD_CLASSES = frozenset({'compile', 'module-tests', 'docs-validate', 'verify', 'none'})


def test_production_path_build_class_is_compile():
    assert _ext.classify_build_class('scripts/foo.py', 'production') == 'compile'


def test_test_path_build_class_is_module_tests():
    assert _ext.classify_build_class('test/foo_test.py', 'test') == 'module-tests'


def test_config_path_build_class_is_verify():
    assert _ext.classify_build_class('pyproject.toml', 'config') == 'verify'


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
# classify_globs() vocabulary (build_map seed source)
# =============================================================================
#
# classify_globs() now returns the portable (suffix, role_heuristic) vocabulary
# consumed by the script-shared tree-deriver — NOT literal path-globs. The
# heuristic name decides the resolved role from where each matching file sits
# in the real tree.

_ROLE_HEURISTICS = frozenset(
    {'production-by-location', 'test-by-location', 'documentation', 'config'}
)


def test_classify_globs_returns_portable_py_vocabulary():
    """The python vocabulary declares .py under both production and test heuristics."""
    vocabulary = _ext.classify_globs()
    assert ('.py', 'production-by-location') in vocabulary
    assert ('.py', 'test-by-location') in vocabulary


def test_classify_globs_declares_config_basenames():
    """Config files are declared by exact basename under the config heuristic."""
    vocabulary = _ext.classify_globs()
    assert ('pyproject.toml', 'config') in vocabulary
    assert ('uv.lock', 'config') in vocabulary
    assert ('marshal.json', 'config') in vocabulary


def test_classify_globs_uses_only_role_heuristic_names():
    """Every vocabulary tuple's second element is a role-heuristic name.

    The vocabulary uses heuristic names (production-by-location etc.), never the
    resolved roles (production/test) — the deriver resolves the heuristic per
    file from its tree location.
    """
    for _suffix, role_heuristic in _ext.classify_globs():
        assert role_heuristic in _ROLE_HEURISTICS


def test_classify_globs_does_not_return_literal_path_globs():
    """The vocabulary must NOT carry the old scripts/-anchored literal globs.

    Regression guard for the build_map redesign: literal author-layout globs
    (`scripts/*.py`, `**/scripts/**/*.py`) are gone — the suffix `.py` plus a
    location heuristic replaces them so the tree-deriver finds production files
    wherever they actually live.
    """
    suffixes = {suffix for suffix, _ in _ext.classify_globs()}
    for stale in ('scripts/*.py', '**/scripts/**/*.py', 'scripts/**/*.py', 'test/**/*.py'):
        assert stale not in suffixes


def test_classify_globs_is_nonempty():
    """The python domain owns buildable file types, so the vocabulary is non-empty."""
    assert _ext.classify_globs()
