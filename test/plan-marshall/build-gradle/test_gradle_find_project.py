#!/usr/bin/env python3
"""Tests for _gradle_cmd_find_project.py.

Tests project discovery from settings.gradle files and build.gradle scanning.
"""


# Tier 2 direct imports via importlib for uniform import style
import importlib.util  # noqa: E402
from pathlib import Path

import pytest

_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace' / 'bundles' / 'plan-marshall' / 'skills' / 'build-gradle' / 'scripts'
)


def _load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_gradle_cmd_find_project_mod = _load_module('_gradle_cmd_find_project', '_gradle_cmd_find_project.py')

find_build_files = _gradle_cmd_find_project_mod.find_build_files
find_settings_file = _gradle_cmd_find_project_mod.find_settings_file
get_root_project_name = _gradle_cmd_find_project_mod.get_root_project_name
parse_included_projects = _gradle_cmd_find_project_mod.parse_included_projects
project_path_to_gradle_notation = _gradle_cmd_find_project_mod.project_path_to_gradle_notation


@pytest.fixture
def gradle_project(tmp_path):
    """Create a minimal Gradle project structure."""
    # Root settings
    settings = tmp_path / 'settings.gradle.kts'
    settings.write_text(
        """rootProject.name = "my-app"
include("core", "web")
"""
    )
    # Root build file
    (tmp_path / 'build.gradle.kts').write_text('// root')
    # Subproject build files
    core_dir = tmp_path / 'core'
    core_dir.mkdir()
    (core_dir / 'build.gradle.kts').write_text('// core')
    web_dir = tmp_path / 'web'
    web_dir.mkdir()
    (web_dir / 'build.gradle.kts').write_text('// web')
    return tmp_path


# =============================================================================
# find_settings_file
# =============================================================================


def test_find_settings_kts(gradle_project):
    """Finds settings.gradle.kts file."""
    result = find_settings_file(gradle_project)
    assert result is not None
    assert result.name == 'settings.gradle.kts'


def test_find_settings_groovy(tmp_path):
    """Finds settings.gradle (Groovy) file."""
    (tmp_path / 'settings.gradle').write_text('rootProject.name = "test"')
    result = find_settings_file(tmp_path)
    assert result is not None
    assert result.name == 'settings.gradle'


def test_find_settings_prefers_kts(tmp_path):
    """Prefers settings.gradle.kts over settings.gradle."""
    (tmp_path / 'settings.gradle.kts').write_text('// kts')
    (tmp_path / 'settings.gradle').write_text('// groovy')
    result = find_settings_file(tmp_path)
    assert result.name == 'settings.gradle.kts'


def test_find_settings_returns_none(tmp_path):
    """Returns None when no settings file exists."""
    assert find_settings_file(tmp_path) is None


# =============================================================================
# parse_included_projects
# =============================================================================


def test_parse_included_projects_kts(gradle_project):
    """Parses include() from Kotlin DSL settings."""
    settings = gradle_project / 'settings.gradle.kts'
    projects = parse_included_projects(settings)
    assert ':core' in projects
    assert ':web' in projects


def test_parse_included_projects_groovy(tmp_path):
    """Parses include from Groovy settings."""
    settings = tmp_path / 'settings.gradle'
    settings.write_text("include ':api', ':impl'\n")
    projects = parse_included_projects(settings)
    assert ':api' in projects
    assert ':impl' in projects


def test_parse_included_projects_adds_colon_prefix(tmp_path):
    """Adds colon prefix to projects without it."""
    settings = tmp_path / 'settings.gradle.kts'
    settings.write_text('include("lib")\n')
    projects = parse_included_projects(settings)
    assert ':lib' in projects


def test_parse_included_projects_empty(tmp_path):
    """Returns empty list when no includes found."""
    settings = tmp_path / 'settings.gradle.kts'
    settings.write_text('rootProject.name = "empty"\n')
    projects = parse_included_projects(settings)
    assert projects == []


# =============================================================================
# get_root_project_name
# =============================================================================


def test_get_root_project_name(gradle_project):
    """Extracts rootProject.name from settings."""
    settings = gradle_project / 'settings.gradle.kts'
    assert get_root_project_name(settings) == 'my-app'


def test_get_root_project_name_returns_none(tmp_path):
    """Returns None when rootProject.name not set."""
    settings = tmp_path / 'settings.gradle.kts'
    settings.write_text('include("core")\n')
    assert get_root_project_name(settings) is None


# =============================================================================
# find_build_files
# =============================================================================


def test_find_build_files(gradle_project):
    """Finds all build.gradle(.kts) files."""
    build_files = find_build_files(gradle_project)
    names = [f.name for f in build_files]
    assert 'build.gradle.kts' in names
    assert len(build_files) >= 3  # root + core + web


def test_find_build_files_excludes_hidden_dirs(tmp_path):
    """Excludes build files in hidden directories."""
    (tmp_path / '.hidden' / 'sub').mkdir(parents=True)
    (tmp_path / '.hidden' / 'sub' / 'build.gradle').write_text('// hidden')
    (tmp_path / 'build.gradle').write_text('// root')
    build_files = find_build_files(tmp_path)
    assert len(build_files) == 1


# =============================================================================
# project_path_to_gradle_notation
# =============================================================================


def test_project_path_to_gradle_notation(gradle_project):
    """Converts directory path to Gradle notation."""
    core_dir = gradle_project / 'core'
    result = project_path_to_gradle_notation(gradle_project, core_dir)
    assert result == ':core'


def test_project_path_to_gradle_notation_nested(tmp_path):
    """Handles nested project paths."""
    nested = tmp_path / 'services' / 'auth'
    nested.mkdir(parents=True)
    result = project_path_to_gradle_notation(tmp_path, nested)
    assert result == ':services:auth'


def test_project_path_to_gradle_notation_root(tmp_path):
    """Root project returns ':'."""
    result = project_path_to_gradle_notation(tmp_path, tmp_path)
    assert result == ':'
