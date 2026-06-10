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
# classify_globs() explicit routes (build_map seed source)
# =============================================================================
#
# classify_globs() returns explicit (pattern, role) routes — single-* fnmatch
# globs paired with a resolved role (production / test / config). A single *
# spans / under fnmatch.fnmatch (the downstream manage-execution-manifest
# matcher), so marketplace/bundles/*.py covers every production .py anywhere
# beneath marketplace/bundles/. The git-tracked completeness validator reports
# any tracked .py these routes forgot.

_BUILD_MAP_ROLES = frozenset({'production', 'test', 'documentation', 'config'})


def test_classify_globs_declares_production_py_roots():
    """The python routes enumerate the four production .py roots as explicit globs."""
    routes = _ext.classify_globs()
    assert ('build.py', 'production') in routes
    assert ('.claude/skills/*.py', 'production') in routes
    assert ('marketplace/bundles/*.py', 'production') in routes
    assert ('marketplace/targets/*.py', 'production') in routes


def test_classify_globs_declares_test_route():
    """Test .py is claimed by the explicit test/*.py route."""
    assert ('test/*.py', 'test') in _ext.classify_globs()


def test_classify_globs_declares_config_basenames():
    """Config files are declared by exact basename under the config role."""
    routes = _ext.classify_globs()
    assert ('pyproject.toml', 'config') in routes
    assert ('uv.lock', 'config') in routes
    assert ('marshal.json', 'config') in routes


def test_classify_globs_uses_only_resolved_roles():
    """Every route's second element is one of the four resolved build_map roles."""
    for _pattern, role in _ext.classify_globs():
        assert role in _BUILD_MAP_ROLES


def test_classify_globs_uses_single_star_fnmatch_globs():
    """Routes are single-* fnmatch globs, never recursive ** forms.

    Regression guard for the build_map redesign: the old by-location heuristic
    vocabulary (bare `.py` suffix + `production-by-location`) and recursive `**`
    globs are gone — explicit single-* routes replace them so the route seeds
    directly without a tree scan.
    """
    for pattern, _role in _ext.classify_globs():
        assert '**' not in pattern, f'route {pattern!r} must use single-* fnmatch, not **'


def test_classify_globs_marketplace_route_covers_extension_py():
    """The marketplace/bundles/*.py production route matches a deep extension.py.

    Confirms the single-* span across / — the route that fixes the build_map
    redesign's central regression (production .py outside scripts/).
    """
    import fnmatch
    prod = [p for p, r in _ext.classify_globs() if r == 'production']
    sample = 'marketplace/bundles/pm-dev-python/skills/plan-marshall-plugin/extension.py'
    assert any(fnmatch.fnmatch(sample, p) for p in prod)


def test_classify_globs_is_nonempty():
    """The python domain owns buildable file types, so the route set is non-empty."""
    assert _ext.classify_globs()
