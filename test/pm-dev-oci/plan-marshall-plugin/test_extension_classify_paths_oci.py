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
