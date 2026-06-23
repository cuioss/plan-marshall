#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for plan-marshall build-pyproject BuildExtension (the Python file-to-build map).

Covers the build-system-owned ``BuildExtension(BuildExtensionBase)`` that ships
in ``build-pyproject/scripts/extension.py``. This extension owns Axis-B of the
extension contract for the Python build system: the explicit ``(pattern, role)``
``classify_globs()`` build_map routes plus the ``classify_paths()`` /
``classify_path_specificity()`` lookups the manage-execution-manifest aggregator
and the build_map seed consume.

Central to this deliverable is the config-claim contract: the Python build
extension claims ``pyproject.toml`` as config but NOT ``uv.lock`` or
``marshal.json`` — neither lockfile nor marshal config triggers a Python build,
so neither is a build-map config route.

The four build skills (build-pyproject, build-maven, build-gradle, build-npm)
each ship a ``BuildExtension`` subclass; each ``extension.py`` lives under the
respective skill's ``scripts/`` directory and shares the module basename
``extension``, so the class is loaded via ``importlib.util.spec_from_file_location``
against the explicit file path to avoid the cross-skill module-name collision.

The base-class default contract, the aggregator's longest-glob-wins overlap
resolution, and the route deriver / completeness validator are covered separately
in test/plan-marshall/script-shared/test_extension_base_classify_paths.py — this
module covers only the concrete pyproject BuildExtension's claims.
"""

import importlib.util
from pathlib import Path

# extension_base is importable: conftest._setup_marketplace_pythonpath() adds
# script-shared/scripts/extension/ to sys.path.
from extension_base import (  # type: ignore[import-not-found]
    BUILD_CLASS_BUILD_CONFIG_FULL,
    BUILD_CLASS_PROD_COMPILE,
    BUILD_CLASS_TEST_RUN,
    BUILD_CLASSES,
    BUILD_MAP_ROLES,
    BuildExtensionBase,
)

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
EXTENSION_FILE = (
    PROJECT_ROOT
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'build-pyproject'
    / 'scripts'
    / 'extension.py'
)


def _load_pyproject_build_extension():
    """Load the build-pyproject BuildExtension class by explicit file path.

    Every build skill ships an ``extension.py`` sharing the module basename
    ``extension``; loading via ``spec_from_file_location`` against the explicit
    path avoids the cross-skill ``import extension`` collision.

    Returns the loaded module so tests can patch the EXACT ``marketplace_paths``
    object the extension bound at import time (a sibling test's
    ``importlib.reload(marketplace_paths)`` can swap ``sys.modules`` out from
    under a separately-imported reference, so patching the extension's own bound
    reference is the order-independent target).
    """
    spec = importlib.util.spec_from_file_location(
        'pyproject_build_extension', EXTENSION_FILE
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_EXTENSION_MODULE = _load_pyproject_build_extension()
BuildExtension = _EXTENSION_MODULE.BuildExtension


def test_build_extension_subclasses_build_extension_base():
    """The pyproject BuildExtension is a BuildExtensionBase (Axis-B), not ExtensionBase."""
    assert issubclass(BuildExtension, BuildExtensionBase)


def test_build_extension_is_instantiable():
    """The pyproject BuildExtension instantiates with no required arguments."""
    ext = BuildExtension()
    assert isinstance(ext, BuildExtensionBase)


def test_classify_paths_claims_pyproject_toml_as_config():
    """pyproject.toml is claimed under the config role."""
    ext = BuildExtension()
    result = ext.classify_paths(['pyproject.toml'])
    assert result['config'] == ['pyproject.toml']


def test_classify_paths_does_not_claim_uv_lock():
    """uv.lock is NOT claimed in any role — it does not trigger a Python build."""
    ext = BuildExtension()
    result = ext.classify_paths(['uv.lock'])
    assert 'uv.lock' not in result['config']
    assert 'uv.lock' not in result['production']
    assert 'uv.lock' not in result['test']
    assert 'uv.lock' not in result['documentation']


def test_classify_paths_does_not_claim_marshal_json():
    """marshal.json is NOT claimed in any role — it does not trigger a Python build."""
    ext = BuildExtension()
    result = ext.classify_paths(['marshal.json'])
    assert 'marshal.json' not in result['config']
    assert 'marshal.json' not in result['production']
    assert 'marshal.json' not in result['test']
    assert 'marshal.json' not in result['documentation']


def test_classify_paths_claims_pyproject_but_not_lockfile_or_marshal_together():
    """Mixed config-like input: only pyproject.toml is claimed; uv.lock / marshal.json are not."""
    ext = BuildExtension()
    result = ext.classify_paths(['pyproject.toml', 'uv.lock', 'marshal.json'])
    assert result['config'] == ['pyproject.toml']


def test_classify_paths_claims_scripts_python_as_production():
    """Python under a scripts/ directory is claimed as production."""
    ext = BuildExtension()
    result = ext.classify_paths(
        ['marketplace/bundles/foo/skills/bar/scripts/baz.py']
    )
    assert 'marketplace/bundles/foo/skills/bar/scripts/baz.py' in result['production']


def test_classify_paths_claims_direct_child_scripts_python_as_production():
    """A direct child of scripts/ (no further subdir) is still production.

    fnmatch's ``**/scripts/**/*.py`` requires a subdirectory after scripts/, so
    the direct-child pattern ``**/scripts/*.py`` is needed to cover this case.
    """
    ext = BuildExtension()
    result = ext.classify_paths(['skills/bar/scripts/baz.py'])
    assert 'skills/bar/scripts/baz.py' in result['production']


def test_classify_paths_claims_test_python_as_test():
    """Python under a test/ directory is claimed as test."""
    ext = BuildExtension()
    result = ext.classify_paths(['test/plan-marshall/build-pyproject/test_foo.py'])
    assert 'test/plan-marshall/build-pyproject/test_foo.py' in result['test']


def test_classify_paths_claims_tests_python_as_test():
    """Python under a tests/ directory is claimed as test."""
    ext = BuildExtension()
    result = ext.classify_paths(['tests/test_foo.py'])
    assert 'tests/test_foo.py' in result['test']


def test_classify_paths_returns_all_four_role_keys():
    """The return always carries the four canonical role keys."""
    ext = BuildExtension()
    result = ext.classify_paths(['anything.txt'])
    assert set(result.keys()) == {'production', 'test', 'documentation', 'config'}


def test_classify_paths_omits_unmatched_paths():
    """A path matching no pattern is omitted from every role bucket."""
    ext = BuildExtension()
    result = ext.classify_paths(['mystery.xyz'])
    assert result == {
        'production': [],
        'test': [],
        'documentation': [],
        'config': [],
    }


def test_classify_paths_handles_empty_input():
    """An empty path list yields the empty four-role dict."""
    ext = BuildExtension()
    assert ext.classify_paths([]) == {
        'production': [],
        'test': [],
        'documentation': [],
        'config': [],
    }


def test_classify_paths_mixed_input():
    """A mixed input list classifies each path into the right bucket."""
    ext = BuildExtension()
    result = ext.classify_paths([
        'skills/bar/scripts/baz.py',
        'test/test_foo.py',
        'pyproject.toml',
        'uv.lock',
        'marshal.json',
    ])
    assert result['production'] == ['skills/bar/scripts/baz.py']
    assert result['test'] == ['test/test_foo.py']
    assert result['config'] == ['pyproject.toml']


def test_classify_path_specificity_returns_score_for_claimed_role():
    """A claimed path returns the matched glob's non-wildcard segment count."""
    ext = BuildExtension()
    # pyproject.toml -> ('pyproject.toml', 'config', 1)
    assert ext.classify_path_specificity('pyproject.toml', 'config') == 1
    # skills/bar/scripts/baz.py -> ('**/scripts/**/*.py', 'production', 2)
    assert (
        ext.classify_path_specificity('skills/bar/scripts/baz.py', 'production') == 2
    )


def test_classify_path_specificity_returns_zero_for_wrong_role():
    """A path claimed under a different role than asked returns 0."""
    ext = BuildExtension()
    # pyproject.toml is config, not production.
    assert ext.classify_path_specificity('pyproject.toml', 'production') == 0


def test_classify_path_specificity_returns_zero_for_unclaimed_path():
    """A path that matches no pattern returns 0 for any role."""
    ext = BuildExtension()
    assert ext.classify_path_specificity('uv.lock', 'config') == 0
    assert ext.classify_path_specificity('marshal.json', 'config') == 0
    assert ext.classify_path_specificity('mystery.xyz', 'production') == 0


def test_classify_globs_returns_pyproject_config_route():
    """The sole config route is pyproject.toml — uv.lock / marshal.json are absent."""
    ext = BuildExtension()
    routes = ext.classify_globs()
    config_patterns = [pattern for pattern, role in routes if role == 'config']
    assert config_patterns == ['pyproject.toml']
    assert ('uv.lock', 'config') not in routes
    assert ('marshal.json', 'config') not in routes


def test_classify_globs_enumerates_production_roots_claude(monkeypatch):
    """On the Claude target the project-local-skill root resolves to .claude/skills."""
    # Patch the EXACT marketplace_paths object the extension bound at import,
    # immune to a sibling test's importlib.reload swapping sys.modules.
    monkeypatch.setattr(
        _EXTENSION_MODULE.marketplace_paths,
        'get_project_skill_roots',
        lambda: ('.claude/skills',),
    )
    ext = BuildExtension()
    routes = ext.classify_globs()
    production_patterns = {pattern for pattern, role in routes if role == 'production'}
    assert production_patterns == {
        'build.py',
        '.claude/skills/*.py',
        'marketplace/bundles/*.py',
        'marketplace/targets/*.py',
    }


def test_classify_globs_enumerates_production_roots_opencode(monkeypatch):
    """On OpenCode every repo-relative project-local-skill root becomes a production glob.

    User-global (~/-anchored or absolute) roots are dropped — a git-tracked .py
    never lives under a user-global root.
    """
    # Patch the EXACT marketplace_paths object the extension bound at import,
    # immune to a sibling test's importlib.reload swapping sys.modules.
    monkeypatch.setattr(
        _EXTENSION_MODULE.marketplace_paths,
        'get_project_skill_roots',
        lambda: (
            '.opencode/skills',
            '.claude/skills',
            '.agents/skills',
            '/home/u/.config/opencode/skills',
        ),
    )
    ext = BuildExtension()
    routes = ext.classify_globs()
    production_patterns = {pattern for pattern, role in routes if role == 'production'}
    assert '.opencode/skills/*.py' in production_patterns
    assert '.claude/skills/*.py' in production_patterns
    assert '.agents/skills/*.py' in production_patterns
    # The user-global root is dropped (no tracked .py lives there).
    assert '/home/u/.config/opencode/skills/*.py' not in production_patterns
    assert {'build.py', 'marketplace/bundles/*.py', 'marketplace/targets/*.py'} <= production_patterns


def test_classify_globs_declares_test_route():
    """The test root test/*.py is declared under the test role."""
    ext = BuildExtension()
    routes = ext.classify_globs()
    assert ('test/*.py', 'test') in routes


def test_classify_globs_every_role_is_a_build_map_role():
    """Each route's role is one of the four resolved BUILD_MAP_ROLES."""
    ext = BuildExtension()
    for _pattern, role in ext.classify_globs():
        assert role in BUILD_MAP_ROLES


def test_classify_globs_uses_single_star_not_recursive():
    """Routes use single-* fnmatch globs (matcher spans /), not recursive ** forms."""
    ext = BuildExtension()
    for pattern, _role in ext.classify_globs():
        assert '**' not in pattern


def test_classify_build_class_production_maps_to_compile():
    """A production path derives the compile build_class via the inherited default."""
    ext = BuildExtension()
    assert (
        ext.classify_build_class('marketplace/bundles/foo.py', 'production')
        == BUILD_CLASS_PROD_COMPILE
    )


def test_classify_build_class_test_maps_to_module_tests():
    """A test path derives the module-tests build_class via the inherited default."""
    ext = BuildExtension()
    assert (
        ext.classify_build_class('test/test_foo.py', 'test') == BUILD_CLASS_TEST_RUN
    )


def test_classify_build_class_config_maps_to_verify():
    """A config path (pyproject.toml) derives the verify build_class."""
    ext = BuildExtension()
    assert (
        ext.classify_build_class('pyproject.toml', 'config')
        == BUILD_CLASS_BUILD_CONFIG_FULL
    )


def test_classify_build_class_every_route_role_resolves_to_a_member():
    """Each declared route role resolves to a BUILD_CLASSES member.

    This is the per-entry lookup the build_map seed aggregator performs.
    """
    ext = BuildExtension()
    for pattern, role in ext.classify_globs():
        assert ext.classify_build_class(pattern, role) in BUILD_CLASSES
