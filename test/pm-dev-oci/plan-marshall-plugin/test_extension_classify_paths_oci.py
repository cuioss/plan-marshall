#!/usr/bin/env python3
"""Tests for pm-dev-oci Extension.classify_paths()."""

import importlib.util
from pathlib import Path

_EXT_PATH = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'pm-dev-oci'
    / 'skills'
    / 'plan-marshall-plugin'
    / 'extension.py'
)


def _load_extension():
    spec = importlib.util.spec_from_file_location('pm_dev_oci_extension', _EXT_PATH)
    assert spec is not None
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod.Extension()


_ext = _load_extension()


def test_dockerfile_is_production():
    result = _ext.classify_paths(['Dockerfile', 'Dockerfile.dev', 'src/Dockerfile.prod'])
    assert 'Dockerfile' in result['production']
    assert 'Dockerfile.dev' in result['production']
    assert 'src/Dockerfile.prod' in result['production']


def test_containerfile_is_production():
    result = _ext.classify_paths(['Containerfile', 'Containerfile.dev'])
    assert 'Containerfile' in result['production']
    assert 'Containerfile.dev' in result['production']


def test_dockerignore_is_production():
    result = _ext.classify_paths(['.dockerignore', 'sub/.dockerignore'])
    assert '.dockerignore' in result['production']
    assert 'sub/.dockerignore' in result['production']


def test_compose_files_are_config():
    result = _ext.classify_paths(['compose.yml', 'docker-compose.yml', 'compose.yaml'])
    assert 'compose.yml' in result['config']
    assert 'docker-compose.yml' in result['config']
    assert 'compose.yaml' in result['config']


def test_unrelated_yml_is_unclaimed():
    result = _ext.classify_paths(['foo.yml', 'ci.yml'])
    for role in ('production', 'test', 'documentation', 'config'):
        assert 'foo.yml' not in result[role]
        assert 'ci.yml' not in result[role]


# =============================================================================
# build_class per claimed role
# =============================================================================

_BUILD_CLASSES = frozenset({'compile', 'module-tests', 'docs-validate', 'verify', 'none'})


def test_dockerfile_build_class_is_compile():
    assert _ext.classify_build_class('Dockerfile', 'production') == 'compile'


def test_compose_build_class_is_verify():
    assert _ext.classify_build_class('compose.yml', 'config') == 'verify'


def test_every_claimed_path_yields_a_build_class_in_the_closed_set():
    """Each path this domain claims resolves to a member of the closed 5-value enum."""
    paths = [
        'Dockerfile',
        'Containerfile',
        '.dockerignore',
        'compose.yml',
        'docker-compose.yml',
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
# globs paired with a resolved role. Container build files (.dockerignore and
# the Dockerfile/Containerfile family) are claimed under production in three
# forms: bare (repo root), */name (any subdirectory), and *.name (named-suffix
# variant like app.Dockerfile). Compose files are config (repo root + */name).

_BUILD_MAP_ROLES = frozenset({'production', 'test', 'documentation', 'config'})


def test_classify_globs_declares_production_container_files():
    """.dockerignore and the Dockerfile/Containerfile family are production routes."""
    routes = _ext.classify_globs()
    assert ('.dockerignore', 'production') in routes
    assert ('Dockerfile', 'production') in routes
    assert ('Containerfile', 'production') in routes


def test_classify_globs_declares_subdirectory_and_named_variants():
    """The family is declared at the repo root, in any subdirectory, and as a named variant."""
    routes = _ext.classify_globs()
    assert ('*/Dockerfile', 'production') in routes
    assert ('*.Dockerfile', 'production') in routes
    assert ('*/.dockerignore', 'production') in routes


def test_classify_globs_declares_compose_config_files():
    """Compose / docker-compose files are declared under the config role."""
    routes = _ext.classify_globs()
    assert ('compose.yml', 'config') in routes
    assert ('docker-compose.yml', 'config') in routes


def test_classify_globs_uses_only_resolved_roles():
    """Every route's second element is one of the four resolved build_map roles."""
    for _pattern, role in _ext.classify_globs():
        assert role in _BUILD_MAP_ROLES


def test_classify_globs_uses_single_star_fnmatch_globs():
    """Routes are single-* fnmatch globs, never recursive ** forms.

    Regression guard: the old by-location heuristic vocabulary (bare basenames +
    `production-by-location`) is gone — explicit single-* routes replace it.
    """
    for pattern, _role in _ext.classify_globs():
        assert '**' not in pattern, f'route {pattern!r} must use single-* fnmatch, not **'


def test_classify_globs_named_variant_route_covers_app_dockerfile():
    """The *.Dockerfile route matches a named-suffix Dockerfile variant."""
    import fnmatch
    prod = [p for p, r in _ext.classify_globs() if r == 'production']
    assert any(fnmatch.fnmatch('app.Dockerfile', p) for p in prod)


def test_classify_globs_is_nonempty():
    """The oci domain owns container file types, so the route set is non-empty."""
    assert _ext.classify_globs()
