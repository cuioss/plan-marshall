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
# classify_globs() vocabulary (build_map seed source)
# =============================================================================
#
# classify_globs() now returns the portable (suffix, role_heuristic) vocabulary
# consumed by the script-shared tree-deriver — NOT literal path-globs. Container
# build files are production-by-location; compose files are config. The
# Dockerfile/Containerfile family is declared as a basename-suffix (so the
# deriver matches `Dockerfile` and `app.Dockerfile` alike).

_ROLE_HEURISTICS = frozenset(
    {'production-by-location', 'test-by-location', 'documentation', 'config'}
)


def test_classify_globs_declares_production_container_files():
    """.dockerignore and the Dockerfile/Containerfile family are production-by-location."""
    vocabulary = _ext.classify_globs()
    assert ('.dockerignore', 'production-by-location') in vocabulary
    assert ('Dockerfile', 'production-by-location') in vocabulary
    assert ('Containerfile', 'production-by-location') in vocabulary


def test_classify_globs_declares_compose_config_files():
    """Compose / docker-compose files are declared under the config heuristic."""
    vocabulary = _ext.classify_globs()
    assert ('compose.yml', 'config') in vocabulary
    assert ('docker-compose.yml', 'config') in vocabulary


def test_classify_globs_uses_only_role_heuristic_names():
    """Every vocabulary tuple's second element is a role-heuristic name."""
    for _suffix, role_heuristic in _ext.classify_globs():
        assert role_heuristic in _ROLE_HEURISTICS


def test_classify_globs_does_not_return_literal_path_globs():
    """The vocabulary carries plain basenames, not the old `Dockerfile*` glob form."""
    suffixes = {suffix for suffix, _ in _ext.classify_globs()}
    for stale in ('Dockerfile*', 'Containerfile*'):
        assert stale not in suffixes


def test_classify_globs_is_nonempty():
    """The oci domain owns container file types, so the vocabulary is non-empty."""
    assert _ext.classify_globs()
