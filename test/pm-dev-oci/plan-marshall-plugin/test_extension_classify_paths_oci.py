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

_BUILD_CLASSES = frozenset({'prod-compile', 'test-run', 'docs-validate', 'build-config-full', 'none'})


def test_dockerfile_build_class_is_prod_compile():
    assert _ext.classify_build_class('Dockerfile', 'production') == 'prod-compile'


def test_compose_build_class_is_build_config_full():
    assert _ext.classify_build_class('compose.yml', 'config') == 'build-config-full'


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
# classify_globs() inventory (build_map seed source)
# =============================================================================


def test_classify_globs_synthesizes_explicit_glob_inventory():
    """Hand-rolled extension: classify_globs returns explicit globs from the rules.

    The inventory mirrors _match_classify: exact-name production files
    (.dockerignore), the Dockerfile/Containerfile prefix family as production,
    and the compose config filenames.
    """
    inventory = _ext.classify_globs()
    assert ('.dockerignore', 'production') in inventory
    assert ('Dockerfile*', 'production') in inventory
    assert ('Containerfile*', 'production') in inventory
    assert ('compose.yml', 'config') in inventory
    assert ('docker-compose.yml', 'config') in inventory


def test_classify_globs_roles_resolve_to_build_classes():
    """Every (glob, role) in the inventory derives a build_class in the closed set."""
    inventory = _ext.classify_globs()
    assert inventory
    for glob, role in inventory:
        assert _ext.classify_build_class(glob, role) in _BUILD_CLASSES


def test_classify_globs_covers_production_and_config_roles():
    """The oci glob inventory claims production and config roles."""
    roles = {role for _, role in _ext.classify_globs()}
    assert roles == {'production', 'config'}
