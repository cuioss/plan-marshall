#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Behavioral unit tests for ``_gradle_cmd_discover`` internals.

The existing ``test_gradle_discover_modules.py`` drives discovery through the
extension's subprocess path, which degrades to an error structure whenever no
Gradle binary is on PATH. These tests instead exercise the in-process building
blocks directly against crafted Gradle project trees and synthetic Gradle
command output, so coverage counts and behavior is pinned regardless of whether
Gradle is installed:

- ``_parse_properties_output`` — group/name/version/description extraction and
  the null / unspecified sentinels.
- ``_parse_dependencies_output`` — first-level deps, project deps, and the
  transitive-line skip.
- ``_find_gradle_descriptors`` — root + settings-driven submodule discovery,
  with absent dirs and build-file-less dirs filtered out.
- ``_extract_gradle_module`` — the error-only struct (Gradle metadata failed),
  the full success struct, the Gradle-name override, and the
  ``archivesBaseName`` fallback.
- ``_build_commands`` — root vs submodule task prefixing and quality-task
  selection.
- ``discover_gradle_modules`` — orchestration with the two Gradle-subprocess
  seams stubbed out.
- ``_get_gradle_metadata`` / ``_get_quality_tasks`` — the subprocess seams with
  ``execute_direct`` stubbed (success and failure).
"""

import sys

import _gradle_execute  # noqa: F401  (ensures sys.modules['_gradle_execute'] is populated)

from conftest import load_script_module

_mod = load_script_module('plan-marshall', 'build-gradle', '_gradle_cmd_discover.py', 'gcd_behavior_mod')


# =============================================================================
# _parse_properties_output
# =============================================================================


def test_parse_properties_output_extracts_all_fields():
    """All four coordinate fields parse from well-formed properties output."""
    # Arrange
    log = 'group: com.example\nname: my-module\nversion: 1.2.3\ndescription: A module\n'

    # Act
    metadata = _mod._parse_properties_output(log)

    # Assert
    assert metadata == {
        'group_id': 'com.example',
        'name': 'my-module',
        'version': '1.2.3',
        'description': 'A module',
    }


def test_parse_properties_output_skips_null_and_unspecified():
    """The 'null' / 'unspecified' sentinels are treated as absent values."""
    # Arrange
    log = 'group: null\nname: real-name\nversion: unspecified\ndescription: null\n'

    # Act
    metadata = _mod._parse_properties_output(log)

    # Assert
    assert metadata['group_id'] is None
    assert metadata['name'] == 'real-name'
    assert metadata['version'] is None
    assert metadata['description'] is None


def test_parse_properties_output_empty_log_yields_all_none():
    """An empty properties log leaves every field None."""
    # Act
    metadata = _mod._parse_properties_output('')

    # Assert
    assert all(value is None for value in metadata.values())


# =============================================================================
# _parse_dependencies_output
# =============================================================================


def test_parse_dependencies_output_extracts_direct_deps():
    """First-level '+---'/'\\---' lines become 'group:artifact:compile' strings."""
    # Arrange
    log = (
        'compileClasspath - Compile classpath for source set \'main\'.\n'
        '+--- org.springframework.boot:spring-boot-starter -> 3.0.0\n'
        '\\--- com.google.guava:guava:31.1-jre\n'
    )

    # Act
    deps = _mod._parse_dependencies_output(log)

    # Assert
    assert 'org.springframework.boot:spring-boot-starter:compile' in deps
    assert 'com.google.guava:guava:compile' in deps


def test_parse_dependencies_output_captures_project_deps():
    """A 'project :name' line becomes an inter-module 'project:name:compile' dep."""
    # Arrange
    log = '+--- project :lib-types\n'

    # Act
    deps = _mod._parse_dependencies_output(log)

    # Assert
    assert deps == ['project:lib-types:compile']


def test_parse_dependencies_output_skips_transitive_lines():
    """Lines carrying a '|' (transitive) prefix are ignored."""
    # Arrange
    log = (
        '+--- com.example:direct:1.0\n'
        '|    \\--- com.example:transitive:1.0\n'
    )

    # Act
    deps = _mod._parse_dependencies_output(log)

    # Assert
    assert deps == ['com.example:direct:compile']


# =============================================================================
# _find_gradle_descriptors
# =============================================================================


def test_find_descriptors_root_only(tmp_path):
    """A project with only a root build file yields a single '.' descriptor."""
    # Arrange
    (tmp_path / 'build.gradle').write_text('// root')

    # Act
    descriptors = _mod._find_gradle_descriptors(str(tmp_path))

    # Assert
    assert len(descriptors) == 1
    assert descriptors[0][1] == '.'


def test_find_descriptors_includes_settings_submodules(tmp_path):
    """settings.gradle includes drive submodule descriptor discovery."""
    # Arrange
    (tmp_path / 'build.gradle').write_text('// root')
    (tmp_path / 'settings.gradle').write_text("include 'core', 'web'\n")
    for name in ('core', 'web'):
        sub = tmp_path / name
        sub.mkdir()
        (sub / 'build.gradle').write_text('// sub')

    # Act
    descriptors = _mod._find_gradle_descriptors(str(tmp_path))

    # Assert
    rel_paths = {rel for _, rel in descriptors}
    assert rel_paths == {'.', 'core', 'web'}


def test_find_descriptors_skips_missing_and_buildless_submodules(tmp_path):
    """Included modules with no directory or no build file are dropped."""
    # Arrange
    (tmp_path / 'build.gradle').write_text('// root')
    (tmp_path / 'settings.gradle').write_text("include 'present', 'ghost', 'empty'\n")
    present = tmp_path / 'present'
    present.mkdir()
    (present / 'build.gradle').write_text('// present')
    # 'empty' dir exists but has no build file; 'ghost' dir does not exist at all.
    (tmp_path / 'empty').mkdir()

    # Act
    descriptors = _mod._find_gradle_descriptors(str(tmp_path))

    # Assert
    rel_paths = {rel for _, rel in descriptors}
    assert rel_paths == {'.', 'present'}


def test_find_descriptors_no_root_build_file(tmp_path):
    """With no root build file the root is omitted but submodules still surface."""
    # Arrange
    (tmp_path / 'settings.gradle').write_text("include 'core'\n")
    core = tmp_path / 'core'
    core.mkdir()
    (core / 'build.gradle.kts').write_text('// core')

    # Act
    descriptors = _mod._find_gradle_descriptors(str(tmp_path))

    # Assert
    rel_paths = {rel for _, rel in descriptors}
    assert rel_paths == {'core'}


# =============================================================================
# _extract_gradle_module
# =============================================================================


def test_extract_module_returns_none_without_build_file(tmp_path):
    """A directory with no build file extracts to None."""
    # Act
    result = _mod._extract_gradle_module(tmp_path, tmp_path, '.', {}, [])

    # Assert
    assert result is None


def test_extract_module_error_struct_when_metadata_failed(tmp_path):
    """gradle_data=None yields the minimal error structure (commands failed)."""
    # Arrange
    sub = tmp_path / 'core'
    sub.mkdir()
    (sub / 'build.gradle').write_text('// core')

    # Act
    result = _mod._extract_gradle_module(sub, tmp_path, 'core', None, [])

    # Assert
    assert result['build_systems'] == ['gradle']
    assert 'error' in result
    assert 'paths' not in result


def test_extract_module_success_uses_gradle_name(tmp_path):
    """A non-root module takes its name from the Gradle metadata when present."""
    # Arrange
    sub = tmp_path / 'core'
    sub.mkdir()
    (sub / 'build.gradle').write_text('// core')
    gradle_data = {'name': 'core-artifact', 'group_id': 'com.example', 'description': 'd', 'dependencies': []}

    # Act
    result = _mod._extract_gradle_module(sub, tmp_path, 'core', gradle_data, [])

    # Assert
    assert result['name'] == 'core-artifact'
    assert result['metadata']['group_id'] == 'com.example'
    assert result['metadata']['description'] == 'd'
    assert result['build_systems'] == ['gradle']


def test_extract_module_uses_archives_base_name_fallback(tmp_path):
    """With no Gradle name, archivesBaseName in the build file overrides the dir name."""
    # Arrange
    sub = tmp_path / 'web'
    sub.mkdir()
    (sub / 'build.gradle').write_text("archivesBaseName = 'custom-web'\n")
    gradle_data = {'name': None, 'group_id': None, 'description': None, 'dependencies': []}

    # Act
    result = _mod._extract_gradle_module(sub, tmp_path, 'web', gradle_data, [])

    # Assert
    assert result['name'] == 'custom-web'


def test_extract_module_root_keeps_base_name(tmp_path):
    """The root module retains the base name (default), not a Gradle override."""
    # Arrange
    (tmp_path / 'build.gradle').write_text('// root')
    gradle_data = {'name': 'should-be-ignored', 'group_id': None, 'description': None, 'dependencies': []}

    # Act
    result = _mod._extract_gradle_module(tmp_path, tmp_path, '.', gradle_data, [])

    # Assert
    assert result['name'] == 'default'


# =============================================================================
# _build_commands
# =============================================================================


def test_build_commands_root_includes_core_targets():
    """Root commands cover clean/verify/install/package without a task prefix."""
    # Act
    commands = _mod._build_commands(
        module_name='default', has_sources=True, has_tests=True, relative_path='.', quality_tasks=[]
    )

    # Assert
    for canonical in ('clean', 'quality-gate', 'verify', 'install', 'clean-install', 'package'):
        assert canonical in commands
    assert 'compile' in commands
    assert 'module-tests' in commands
    assert 'coverage' in commands


def test_build_commands_submodule_prefixes_tasks():
    """A submodule prefixes each Gradle task with ':module:'."""
    # Act
    commands = _mod._build_commands(
        module_name='core', has_sources=True, has_tests=True, relative_path='core', quality_tasks=[]
    )

    # Assert
    assert ':core:build' in commands['verify']
    assert ':core:test' in commands['module-tests']


def test_build_commands_omits_source_and_test_targets_when_absent():
    """compile/test-compile/module-tests are skipped when sources/tests absent."""
    # Act
    commands = _mod._build_commands(
        module_name='default', has_sources=False, has_tests=False, relative_path='.', quality_tasks=[]
    )

    # Assert
    assert 'compile' not in commands
    assert 'test-compile' not in commands
    assert 'module-tests' not in commands


def test_build_commands_spotless_selects_spotless_quality_target():
    """A detected spotlessCheck task drives the quality-gate target."""
    # Act
    commands = _mod._build_commands(
        module_name='default', has_sources=True, has_tests=False, relative_path='.', quality_tasks=['spotlessCheck']
    )

    # Assert
    assert 'spotlessCheck' in commands['quality-gate']


def test_build_commands_checkstyle_selects_checkstyle_quality_target():
    """A detected checkstyleMain task drives the quality-gate target."""
    # Act
    commands = _mod._build_commands(
        module_name='default', has_sources=True, has_tests=False, relative_path='.', quality_tasks=['checkstyleMain']
    )

    # Assert
    assert 'checkstyleMain' in commands['quality-gate']


# =============================================================================
# discover_gradle_modules (orchestration, subprocess seams stubbed)
# =============================================================================


def test_discover_gradle_modules_assembles_from_descriptors(tmp_path, monkeypatch):
    """Orchestration walks descriptors and builds one module per build file."""
    # Arrange — a root + one submodule, with the two Gradle subprocess seams stubbed.
    (tmp_path / 'build.gradle').write_text('// root')
    (tmp_path / 'settings.gradle').write_text("include 'core'\n")
    core = tmp_path / 'core'
    core.mkdir()
    (core / 'build.gradle').write_text('// core')

    monkeypatch.setattr(_mod, '_get_quality_tasks', lambda root: [])
    monkeypatch.setattr(
        _mod,
        '_get_gradle_metadata',
        lambda module_path, root: {'name': None, 'group_id': 'g', 'description': None, 'dependencies': []},
    )

    # Act
    modules = _mod.discover_gradle_modules(str(tmp_path))

    # Assert
    names = sorted(m['name'] for m in modules)
    assert names == ['core', 'default']
    assert all(m['build_systems'] == ['gradle'] for m in modules)


def test_discover_gradle_modules_propagates_metadata_failure(tmp_path, monkeypatch):
    """When Gradle metadata fails, the module surfaces as an error struct."""
    # Arrange
    (tmp_path / 'build.gradle').write_text('// root')
    monkeypatch.setattr(_mod, '_get_quality_tasks', lambda root: [])
    monkeypatch.setattr(_mod, '_get_gradle_metadata', lambda module_path, root: None)

    # Act
    modules = _mod.discover_gradle_modules(str(tmp_path))

    # Assert
    assert len(modules) == 1
    assert 'error' in modules[0]


# =============================================================================
# _get_gradle_metadata / _get_quality_tasks (execute_direct stubbed)
# =============================================================================


def test_get_gradle_metadata_parses_success_log(tmp_path, monkeypatch):
    """A successful Gradle call's log is parsed into coordinates + dependencies."""
    # Arrange
    log_file = tmp_path / 'gradle.log'
    log_file.write_text(
        'group: com.example\nname: core\nversion: 1.0\n'
        'compileClasspath - Compile classpath\n'
        '+--- com.google.guava:guava:31.1\n'
    )

    def _fake_execute(**kwargs):
        return {'status': 'success', 'log_file': str(log_file)}

    monkeypatch.setattr(sys.modules['_gradle_execute'], 'execute_direct', _fake_execute)

    # Act
    metadata = _mod._get_gradle_metadata('core', tmp_path)

    # Assert
    assert metadata['group_id'] == 'com.example'
    assert metadata['name'] == 'core'
    assert 'com.google.guava:guava:compile' in metadata['dependencies']


def test_get_gradle_metadata_returns_none_on_failure(tmp_path, monkeypatch):
    """A non-success Gradle result yields None metadata."""
    # Arrange
    monkeypatch.setattr(sys.modules['_gradle_execute'], 'execute_direct', lambda **kwargs: {'status': 'error'})

    # Act
    metadata = _mod._get_gradle_metadata('', tmp_path)

    # Assert
    assert metadata is None


def test_get_quality_tasks_extracts_known_tasks(tmp_path, monkeypatch):
    """Only recognized verification tasks are returned from the tasks listing."""
    # Arrange
    log_file = tmp_path / 'tasks.log'
    log_file.write_text(
        'spotlessCheck - Checks that sourcecode satisfies formatting\n'
        'checkstyleMain - Runs Checkstyle\n'
        'someUnknownTask - Not a quality task\n'
    )
    monkeypatch.setattr(
        sys.modules['_gradle_execute'], 'execute_direct', lambda **kwargs: {'status': 'success', 'log_file': str(log_file)}
    )

    # Act
    tasks = _mod._get_quality_tasks(tmp_path)

    # Assert
    assert 'spotlessCheck' in tasks
    assert 'checkstyleMain' in tasks
    assert 'someUnknownTask' not in tasks


def test_get_quality_tasks_returns_empty_on_failure(tmp_path, monkeypatch):
    """A failed tasks call yields an empty quality-task list."""
    # Arrange
    monkeypatch.setattr(sys.modules['_gradle_execute'], 'execute_direct', lambda **kwargs: {'status': 'error'})

    # Act
    tasks = _mod._get_quality_tasks(tmp_path)

    # Assert
    assert tasks == []
