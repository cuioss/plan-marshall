#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Behavioral tests for the Maven discovery enrich path and declared-profile pipeline.

The existing ``test_discover_modules.py`` covers the cheap, subprocess-free
discovery path and the pure parsers, and stubs ``_get_maven_metadata`` away.
These tests instead drive the lazy enrich seam — ``_get_maven_metadata`` and the
public ``enrich_maven_module`` — with ``execute_direct`` stubbed to write a
synthetic Maven log, plus the cheap-path ``_map_canonical_declared_profiles`` and
``_apply_profile_pipeline`` config branches with ``ext_defaults_get`` stubbed.
None of these paths require a Maven binary.
"""

import sys

import _config_core
import _maven_execute  # noqa: F401  (ensures sys.modules['_maven_execute'] is populated)

from conftest import load_script_module

_mod = load_script_module('plan-marshall', 'build-maven', '_maven_cmd_discover.py', 'mcd_enrich_mod')


_SUCCESS_LOG = (
    '[INFO] com.example:my-app:jar:1.0.0\n'
    'Profile Id: coverage (Active: false, Source: pom)\n'
    'Profile Id: jdk17 (Active: true, Source: pom)\n'
    '[INFO] +- org.junit.jupiter:junit-jupiter:jar:5.10.0:test\n'
)


def _stub_execute(monkeypatch, log_file=None, status='success'):
    """Stub _maven_execute.execute_direct to return a fixed result dict."""
    result = {'status': status}
    if log_file is not None:
        result['log_file'] = str(log_file)

    def _fake(**kwargs):
        return result

    monkeypatch.setattr(sys.modules['_maven_execute'], 'execute_direct', _fake)


def _make_pom_dir(tmp_path):
    """Create a tmp module dir containing a minimal pom.xml and return it."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    pom = tmp_path / 'pom.xml'
    pom.write_text('<project><artifactId>my-app</artifactId></project>')
    return tmp_path


# =============================================================================
# _get_maven_metadata — guard paths
# =============================================================================


def test_get_maven_metadata_none_when_pom_absent(tmp_path, monkeypatch):
    """A module dir with no pom.xml short-circuits to None before any subprocess."""
    # Arrange — never reached, but stub so an accidental call is visible.
    _stub_execute(monkeypatch, status='error')

    # Act
    result = _mod._get_maven_metadata(tmp_path, tmp_path)

    # Assert
    assert result is None


def test_get_maven_metadata_none_on_execute_failure(tmp_path, monkeypatch):
    """A non-success execute result yields None metadata."""
    # Arrange
    module_dir = _make_pom_dir(tmp_path)
    _stub_execute(monkeypatch, status='error')

    # Act
    result = _mod._get_maven_metadata(module_dir, module_dir)

    # Assert
    assert result is None


def test_get_maven_metadata_none_when_log_missing(tmp_path, monkeypatch):
    """A success result pointing at a nonexistent log file yields None."""
    # Arrange
    module_dir = _make_pom_dir(tmp_path)
    _stub_execute(monkeypatch, log_file=tmp_path / 'does-not-exist.log')

    # Act
    result = _mod._get_maven_metadata(module_dir, module_dir)

    # Assert
    assert result is None


# =============================================================================
# _get_maven_metadata — success path
# =============================================================================


def test_get_maven_metadata_parses_coordinates_profiles_deps(tmp_path, monkeypatch):
    """A successful run parses coordinates, command-line profiles, and direct deps."""
    # Arrange
    module_dir = _make_pom_dir(tmp_path)
    log_file = tmp_path / 'maven.log'
    log_file.write_text(_SUCCESS_LOG)
    _stub_execute(monkeypatch, log_file=log_file)

    # Act
    result = _mod._get_maven_metadata(module_dir, module_dir)

    # Assert
    assert result['artifact_id'] == 'my-app'
    assert result['group_id'] == 'com.example'
    assert result['packaging'] == 'jar'
    # jdk17 is default-activated (Active: true) and must be filtered out.
    profile_ids = [p['id'] for p in result['profiles']]
    assert 'coverage' in profile_ids
    assert 'jdk17' not in profile_ids
    assert 'org.junit.jupiter:junit-jupiter:test' in result['dependencies']


def test_get_maven_metadata_handles_pom_outside_project_root(tmp_path, monkeypatch):
    """A pom not under project_root falls back to an absolute -f path (no crash)."""
    # Arrange — module dir and project root are unrelated trees.
    module_dir = _make_pom_dir(tmp_path / 'module')
    other_root = tmp_path / 'elsewhere'
    other_root.mkdir()
    log_file = tmp_path / 'maven.log'
    log_file.write_text(_SUCCESS_LOG)
    _stub_execute(monkeypatch, log_file=log_file)

    # Act
    result = _mod._get_maven_metadata(module_dir, other_root)

    # Assert
    assert result is not None
    assert result['artifact_id'] == 'my-app'


# =============================================================================
# enrich_maven_module — public seam delegates to _get_maven_metadata
# =============================================================================


def test_enrich_maven_module_returns_resolved_metadata(tmp_path, monkeypatch):
    """enrich_maven_module surfaces the resolved metadata from the subprocess seam."""
    # Arrange
    module_dir = _make_pom_dir(tmp_path)
    log_file = tmp_path / 'maven.log'
    log_file.write_text(_SUCCESS_LOG)
    _stub_execute(monkeypatch, log_file=log_file)

    # Act
    result = _mod.enrich_maven_module(str(module_dir), str(module_dir))

    # Assert
    assert result['artifact_id'] == 'my-app'
    assert any(p['id'] == 'coverage' for p in result['profiles'])


# =============================================================================
# _apply_profile_pipeline — config-driven skip + mapping
# =============================================================================


def test_apply_profile_pipeline_skips_and_maps_via_config(monkeypatch):
    """The skip list and explicit mapping from config drive the pipeline output."""
    # Arrange
    raw_profiles = [
        {'id': 'pre-commit', 'is_active': False},
        {'id': 'release', 'is_active': False},
        {'id': 'jdk17', 'is_active': True},
    ]

    def _fake_ext(key, root):
        if key == _mod.EXT_KEY_PROFILES_SKIP:
            return 'release'
        if key == _mod.EXT_KEY_PROFILES_MAP:
            return 'pre-commit:quality-gate'
        return None

    monkeypatch.setattr(_config_core, 'ext_defaults_get', _fake_ext)

    # Act
    profiles = _mod._apply_profile_pipeline(raw_profiles, '/proj')

    # Assert — jdk17 filtered (active), release skipped, pre-commit mapped.
    by_id = {p['id']: p for p in profiles}
    assert 'jdk17' not in by_id
    assert 'release' not in by_id
    assert by_id['pre-commit']['canonical'] == 'quality-gate'


def test_apply_profile_pipeline_no_config_uses_aliases(monkeypatch):
    """With no config, alias classification still maps known profile ids."""
    # Arrange
    raw_profiles = [{'id': 'coverage', 'is_active': False}]
    monkeypatch.setattr(_config_core, 'ext_defaults_get', lambda key, root: None)

    # Act
    profiles = _mod._apply_profile_pipeline(raw_profiles, '/proj')

    # Assert
    assert profiles[0]['canonical'] == 'coverage'


# =============================================================================
# _map_canonical_declared_profiles — cheap-path declared-id mapping
# =============================================================================


def test_map_declared_profiles_default_path(monkeypatch):
    """Declared ids map through aliases when no skip/map config is set."""
    # Arrange
    monkeypatch.setattr(_config_core, 'ext_defaults_get', lambda key, root: None)

    # Act
    profiles = _mod._map_canonical_declared_profiles(['coverage', 'integration-tests'], '/proj')

    # Assert
    by_id = {p['id']: p for p in profiles}
    assert by_id['coverage']['canonical'] == 'coverage'
    assert by_id['integration-tests']['canonical'] == 'integration-tests'


def test_map_declared_profiles_honours_skip_and_mapping(monkeypatch):
    """Declared ids honor the config skip list and explicit canonical mapping."""
    # Arrange
    def _fake_ext(key, root):
        if key == _mod.EXT_KEY_PROFILES_SKIP:
            return 'native'
        if key == _mod.EXT_KEY_PROFILES_MAP:
            return 'pre-commit:quality-gate'
        return None

    monkeypatch.setattr(_config_core, 'ext_defaults_get', _fake_ext)

    # Act
    profiles = _mod._map_canonical_declared_profiles(['pre-commit', 'native'], '/proj')

    # Assert
    by_id = {p['id']: p for p in profiles}
    assert 'native' not in by_id
    assert by_id['pre-commit']['canonical'] == 'quality-gate'


# =============================================================================
# discover_maven_modules — declared profiles flow into commands (cheap path)
# =============================================================================


def test_discover_surfaces_declared_profile_commands(tmp_path, monkeypatch):
    """A pom declaring a coverage profile yields a coverage command on the cheap path."""
    # Arrange — no Maven binary; the declared profile flows through the cheap pipeline.
    monkeypatch.setattr(_config_core, 'ext_defaults_get', lambda key, root: None)
    pom = tmp_path / 'pom.xml'
    pom.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<project xmlns="http://maven.apache.org/POM/4.0.0">\n'
        '  <groupId>com.example</groupId>\n'
        '  <artifactId>cov-app</artifactId>\n'
        '  <version>1.0.0</version>\n'
        '  <profiles>\n'
        '    <profile><id>coverage</id></profile>\n'
        '  </profiles>\n'
        '</project>\n'
    )

    # Act
    modules = _mod.discover_maven_modules(str(tmp_path))

    # Assert
    assert len(modules) == 1
    module = modules[0]
    assert 'coverage' in module['commands']
    assert any(p['id'] == 'coverage' for p in module['metadata']['profiles'])
