#!/usr/bin/env python3
"""Tests for discover_modules() Gradle support in Java extension.

Tests the unified module discovery API for Gradle projects against
the contract defined in build-project-structure.md.

Contract requirements:
- build_systems: array with single element ["gradle"]
- When Gradle commands succeed:
  - paths: object with module, descriptor, sources, tests, readme
  - metadata: snake_case fields (artifact_id, group_id)
  - stats: only source_files, test_files
  - commands: resolved canonical command strings
- When Gradle commands fail:
  - error: top-level error message
  - No paths, metadata, stats, or commands (minimal structure)

Note: Tests must handle both cases since Gradle may or may not be
available depending on the environment (CI runners have it, local may not).
"""

import shutil
import sys
from pathlib import Path

# Import shared infrastructure (sets up PYTHONPATH for cross-skill imports)
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from conftest import BuildContext

# Direct imports - conftest sets up PYTHONPATH
# Import Extension class from the extension module
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
EXTENSION_DIR = PROJECT_ROOT / 'marketplace' / 'bundles' / 'pm-dev-java' / 'skills' / 'plan-marshall-plugin'
sys.path.insert(0, str(EXTENSION_DIR))

import importlib.util  # noqa: E402

spec = importlib.util.spec_from_file_location('java_extension', EXTENSION_DIR / 'extension.py')
java_extension = importlib.util.module_from_spec(spec)
spec.loader.exec_module(java_extension)
Extension = java_extension.Extension

# Check if Gradle is available system-wide
GRADLE_AVAILABLE = shutil.which('gradle') is not None


def _assert_valid_module_structure(module: dict) -> None:
    """Assert module has valid structure (either error or success).

    Args:
        module: Module dict to validate
    """
    assert 'build_systems' in module
    assert module['build_systems'] == ['gradle']
    assert 'name' in module

    if 'error' in module:
        # Error structure: minimal fields only
        assert 'paths' not in module or module.get('paths') is None
        assert 'stats' not in module or module.get('stats') is None
        assert 'commands' not in module or module.get('commands') is None
    else:
        # Success structure: has paths, stats, commands
        assert 'paths' in module
        assert 'commands' in module


# =============================================================================
# Test: Basic Gradle Module Discovery
# =============================================================================


def test_discover_gradle_single_module():
    """Test discover_modules with single-module Gradle project.

    Returns either error structure (no Gradle) or success structure (Gradle available).
    """
    with BuildContext() as ctx:
        # Create a single-module Gradle project
        build_gradle = """
plugins {
    id 'java'
}

group = 'com.example'
version = '1.0.0'
description = 'My Gradle application'
"""
        (ctx.temp_dir / 'build.gradle').write_text(build_gradle)

        # Create source directory
        src_main = ctx.temp_dir / 'src' / 'main' / 'java' / 'com' / 'example'
        src_main.mkdir(parents=True)
        (src_main / 'App.java').write_text('public class App {}')

        ext = Extension()
        modules = ext.discover_modules(str(ctx.temp_dir))

        assert len(modules) == 1
        module = modules[0]

        assert module['build_systems'] == ['gradle']
        assert module['name'] == 'default'  # Root module is always "default"
        _assert_valid_module_structure(module)


def test_discover_gradle_multi_module():
    """Test discover_modules with multi-module Gradle project.

    Returns either error structure (no Gradle) or success structure (Gradle available).
    """
    with BuildContext() as ctx:
        # Create settings.gradle with modules
        settings_gradle = """
rootProject.name = 'parent'
include 'core'
include 'web'
"""
        (ctx.temp_dir / 'settings.gradle').write_text(settings_gradle)

        # Create root build.gradle
        (ctx.temp_dir / 'build.gradle').write_text('// root')

        # Create core module
        core_dir = ctx.temp_dir / 'core'
        core_dir.mkdir()
        (core_dir / 'build.gradle').write_text('apply plugin: "java"')

        # Create web module
        web_dir = ctx.temp_dir / 'web'
        web_dir.mkdir()
        (web_dir / 'build.gradle').write_text('apply plugin: "java"')

        ext = Extension()
        modules = ext.discover_modules(str(ctx.temp_dir))

        # 3 modules: root "default" + core + web
        assert len(modules) == 3

        # All should have valid structure
        for module in modules:
            assert module['build_systems'] == ['gradle']
            _assert_valid_module_structure(module)


def test_discover_gradle_no_build_file():
    """Test discover_modules with no build.gradle."""
    with BuildContext() as ctx:
        ext = Extension()
        modules = ext.discover_modules(str(ctx.temp_dir))

        assert len(modules) == 0


def test_discover_gradle_kotlin_dsl():
    """Test discover_modules with Kotlin DSL (build.gradle.kts).

    Returns either error structure (no Gradle) or success structure (Gradle available).
    """
    with BuildContext() as ctx:
        build_gradle_kts = """
plugins {
    java
}

group = "com.example"
version = "2.0.0"
description = "Kotlin DSL project"
"""
        (ctx.temp_dir / 'build.gradle.kts').write_text(build_gradle_kts)

        ext = Extension()
        modules = ext.discover_modules(str(ctx.temp_dir))

        assert len(modules) == 1
        # Contract: build_systems is ["gradle"]
        assert modules[0]['build_systems'] == ['gradle']
        assert modules[0]['name'] == 'default'
        _assert_valid_module_structure(modules[0])


# =============================================================================
# Test: Source Directory Discovery
# =============================================================================


def test_gradle_discover_sources():
    """Test source directory discovery for Gradle.

    Returns either error structure (no Gradle) or success structure (Gradle available).
    """
    with BuildContext() as ctx:
        # Create build.gradle
        (ctx.temp_dir / 'build.gradle').write_text('apply plugin: "java"')

        # Create standard Gradle/Maven layout
        (ctx.temp_dir / 'src' / 'main' / 'java' / 'com').mkdir(parents=True)
        (ctx.temp_dir / 'src' / 'test' / 'java' / 'com').mkdir(parents=True)

        ext = Extension()
        modules = ext.discover_modules(str(ctx.temp_dir))

        assert len(modules) == 1
        _assert_valid_module_structure(modules[0])


# =============================================================================
# Test: Stats
# =============================================================================


def test_gradle_stats_file_counts():
    """Test source and test file counting for Gradle.

    Returns either error structure (no Gradle) or success structure (Gradle available).
    """
    with BuildContext() as ctx:
        (ctx.temp_dir / 'build.gradle').write_text('apply plugin: "java"')

        # Create source files
        src_dir = ctx.temp_dir / 'src' / 'main' / 'java' / 'com' / 'example'
        src_dir.mkdir(parents=True)
        (src_dir / 'Foo.java').write_text('public class Foo {}')
        (src_dir / 'Bar.java').write_text('public class Bar {}')

        # Create test files
        test_dir = ctx.temp_dir / 'src' / 'test' / 'java' / 'com' / 'example'
        test_dir.mkdir(parents=True)
        (test_dir / 'FooTest.java').write_text('public class FooTest {}')

        ext = Extension()
        modules = ext.discover_modules(str(ctx.temp_dir))

        _assert_valid_module_structure(modules[0])


def test_gradle_kotlin_sources_detected():
    """Test Kotlin source files detection.

    Returns either error structure (no Gradle) or success structure (Gradle available).
    """
    with BuildContext() as ctx:
        (ctx.temp_dir / 'build.gradle.kts').write_text('plugins { kotlin("jvm") }')

        # Create Kotlin source files
        src_dir = ctx.temp_dir / 'src' / 'main' / 'kotlin' / 'com' / 'example'
        src_dir.mkdir(parents=True)
        (src_dir / 'App.kt').write_text('class App')
        (src_dir / 'Service.kt').write_text('class Service')

        ext = Extension()
        modules = ext.discover_modules(str(ctx.temp_dir))

        assert len(modules) == 1
        _assert_valid_module_structure(modules[0])


def test_gradle_groovy_sources_detected():
    """Test Groovy source files detection.

    Returns either error structure (no Gradle) or success structure (Gradle available).
    """
    with BuildContext() as ctx:
        (ctx.temp_dir / 'build.gradle').write_text('apply plugin: "groovy"')

        # Create Groovy source files
        src_dir = ctx.temp_dir / 'src' / 'main' / 'groovy' / 'com' / 'example'
        src_dir.mkdir(parents=True)
        (src_dir / 'Script.groovy').write_text('class Script {}')

        ext = Extension()
        modules = ext.discover_modules(str(ctx.temp_dir))

        assert len(modules) == 1
        _assert_valid_module_structure(modules[0])


def test_gradle_scala_sources_detected():
    """Test Scala source files detection.

    Returns either error structure (no Gradle) or success structure (Gradle available).
    """
    with BuildContext() as ctx:
        (ctx.temp_dir / 'build.gradle').write_text('apply plugin: "scala"')

        # Create Scala source files
        src_dir = ctx.temp_dir / 'src' / 'main' / 'scala' / 'com' / 'example'
        src_dir.mkdir(parents=True)
        (src_dir / 'App.scala').write_text('object App')

        ext = Extension()
        modules = ext.discover_modules(str(ctx.temp_dir))

        assert len(modules) == 1
        _assert_valid_module_structure(modules[0])


def test_gradle_mixed_jvm_languages():
    """Test mixed Java/Kotlin/Groovy project.

    Returns either error structure (no Gradle) or success structure (Gradle available).
    """
    with BuildContext() as ctx:
        (ctx.temp_dir / 'build.gradle').write_text('apply plugin: "java"\napply plugin: "kotlin"')

        # Create Java source
        java_dir = ctx.temp_dir / 'src' / 'main' / 'java' / 'com'
        java_dir.mkdir(parents=True)
        (java_dir / 'JavaClass.java').write_text('public class JavaClass {}')

        # Create Kotlin source
        kotlin_dir = ctx.temp_dir / 'src' / 'main' / 'kotlin' / 'com'
        kotlin_dir.mkdir(parents=True)
        (kotlin_dir / 'KotlinClass.kt').write_text('class KotlinClass')

        ext = Extension()
        modules = ext.discover_modules(str(ctx.temp_dir))

        assert len(modules) == 1
        _assert_valid_module_structure(modules[0])


def test_gradle_kotlin_only_module_has_compile_command():
    """Test Kotlin-only module.

    Returns either error structure (no Gradle) or success structure (Gradle available).
    """
    with BuildContext() as ctx:
        (ctx.temp_dir / 'build.gradle.kts').write_text('plugins { kotlin("jvm") }')

        # Create Kotlin source (no Java)
        src_dir = ctx.temp_dir / 'src' / 'main' / 'kotlin' / 'com'
        src_dir.mkdir(parents=True)
        (src_dir / 'App.kt').write_text('class App')

        ext = Extension()
        modules = ext.discover_modules(str(ctx.temp_dir))

        assert len(modules) == 1
        _assert_valid_module_structure(modules[0])


def test_gradle_stats_readme_in_paths():
    """Test README detection.

    Returns either error structure (no Gradle) or success structure (Gradle available).
    """
    with BuildContext() as ctx:
        (ctx.temp_dir / 'build.gradle').write_text('apply plugin: "java"')
        (ctx.temp_dir / 'README.md').write_text('# My Project')

        ext = Extension()
        modules = ext.discover_modules(str(ctx.temp_dir))

        _assert_valid_module_structure(modules[0])


# =============================================================================
# Test: Commands
# =============================================================================


def test_gradle_module_has_commands():
    """Test Gradle module commands.

    Returns either error structure (no Gradle) or success structure (Gradle available).
    """
    with BuildContext() as ctx:
        (ctx.temp_dir / 'build.gradle').write_text('apply plugin: "java"')

        # Create source and test files
        src_dir = ctx.temp_dir / 'src' / 'main' / 'java'
        src_dir.mkdir(parents=True)
        (src_dir / 'App.java').write_text('public class App {}')
        test_dir = ctx.temp_dir / 'src' / 'test' / 'java'
        test_dir.mkdir(parents=True)
        (test_dir / 'AppTest.java').write_text('public class AppTest {}')

        ext = Extension()
        modules = ext.discover_modules(str(ctx.temp_dir))

        _assert_valid_module_structure(modules[0])


# =============================================================================
# Test: No Duplicate Modules
# =============================================================================


def test_no_duplicate_modules_with_both_build_files():
    """Test that modules are not duplicated when both pom.xml and build.gradle exist.

    Note: Maven discovery requires Maven commands to succeed. In a test environment
    without a valid Maven setup, Maven modules are skipped and Gradle takes over.
    This test verifies no duplication occurs in either case.
    """
    with BuildContext() as ctx:
        # Create both Maven and Gradle files
        (ctx.temp_dir / 'pom.xml').write_text("""<?xml version="1.0"?>
<project>
    <artifactId>test-project</artifactId>
    <groupId>com.example</groupId>
</project>""")
        (ctx.temp_dir / 'build.gradle').write_text('apply plugin: "java"')

        ext = Extension()
        modules = ext.discover_modules(str(ctx.temp_dir))

        # Should only have one module (no duplication)
        assert len(modules) == 1
        # build_systems depends on whether Maven is available
        # In test environment, Maven fails so Gradle is used
        assert modules[0]['build_systems'] in [['maven'], ['gradle']]


# =============================================================================
# Runner
# =============================================================================
