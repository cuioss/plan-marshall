#!/usr/bin/env python3
"""Unit tests for discover_packages() files collection.

Tests that package discovery correctly lists direct source files
per package, excluding package-info.java and sub-package files.

Uses the shared discover_packages() from extension-api (_build_discover).
"""


from pathlib import Path

# Direct imports - conftest sets up PYTHONPATH
from _build_discover import discover_packages


def _create_java_package(base: Path, source_dir: str, package_path: str, files: list[str]) -> None:
    """Create a Java package directory with files.

    Args:
        base: Module root directory
        source_dir: Source directory (e.g., 'src/main/java')
        package_path: Package path (e.g., 'com/example/util')
        files: List of .java filenames to create
    """
    pkg_dir = base / source_dir / package_path
    pkg_dir.mkdir(parents=True, exist_ok=True)
    for f in files:
        (pkg_dir / f).write_text(f'// {f}')


# =============================================================================
# Tests: Direct Files Collection
# =============================================================================


def test_package_with_java_files(tmp_path):
    """Package with 3 .java files includes all 3 sorted names."""
    _create_java_package(
        tmp_path,
        'src/main/java',
        'com/example/util',
        [
            'MoreStrings.java',
            'CollectionBuilder.java',
            'MoreCollections.java',
        ],
    )

    packages = discover_packages(tmp_path, ['src/main/java'], '')

    assert 'com.example.util' in packages
    pkg = packages['com.example.util']
    assert pkg['files'] == ['CollectionBuilder.java', 'MoreCollections.java', 'MoreStrings.java']


def test_subpackage_files_not_in_parent(tmp_path):
    """Parent package only lists its direct files, not sub-package files."""
    _create_java_package(tmp_path, 'src/main/java', 'com/example', ['App.java'])
    _create_java_package(tmp_path, 'src/main/java', 'com/example/sub', ['Helper.java'])

    packages = discover_packages(tmp_path, ['src/main/java'], '')

    parent = packages['com.example']
    sub = packages['com.example.sub']
    assert parent['files'] == ['App.java']
    assert sub['files'] == ['Helper.java']


def test_package_info_excluded_from_files(tmp_path):
    """package-info.java is excluded from files list but tracked in package_info."""
    _create_java_package(
        tmp_path,
        'src/main/java',
        'com/example/core',
        [
            'Service.java',
            'package-info.java',
        ],
    )

    packages = discover_packages(tmp_path, ['src/main/java'], '')

    pkg = packages['com.example.core']
    assert pkg['files'] == ['Service.java']
    assert 'package_info' in pkg


def test_empty_package_omits_files(tmp_path):
    """Package with only sub-packages (no direct .java files) omits files field."""
    # Create parent with only package-info.java (no real source files)
    parent_dir = tmp_path / 'src' / 'main' / 'java' / 'com' / 'example'
    parent_dir.mkdir(parents=True)
    (parent_dir / 'package-info.java').write_text('// package-info')

    # Create sub-package with actual files (needed so parent is discovered via rglob)
    _create_java_package(tmp_path, 'src/main/java', 'com/example/sub', ['Impl.java'])

    packages = discover_packages(tmp_path, ['src/main/java'], '')

    parent = packages['com.example']
    assert 'files' not in parent
    assert 'package_info' in parent


def test_root_package_skipped(tmp_path):
    """Files directly in src/main/java (root package ".") are skipped."""
    src_dir = tmp_path / 'src' / 'main' / 'java'
    src_dir.mkdir(parents=True)
    (src_dir / 'Main.java').write_text('// Main')

    packages = discover_packages(tmp_path, ['src/main/java'], '')

    assert '.' not in packages
    assert len(packages) == 0


def test_relative_path_prefix(tmp_path):
    """When relative_path is set, paths are prefixed correctly."""
    _create_java_package(tmp_path, 'src/main/java', 'com/example', ['App.java'])

    packages = discover_packages(tmp_path, ['src/main/java'], 'my-module')

    pkg = packages['com.example']
    assert pkg['path'] == 'my-module/src/main/java/com/example'
    assert pkg['files'] == ['App.java']


def test_multiple_packages_independent_files(tmp_path):
    """Each package gets only its own direct files."""
    _create_java_package(tmp_path, 'src/main/java', 'com/example/api', ['Api.java', 'Client.java'])
    _create_java_package(tmp_path, 'src/main/java', 'com/example/impl', ['Impl.java'])

    packages = discover_packages(tmp_path, ['src/main/java'], '')

    assert packages['com.example.api']['files'] == ['Api.java', 'Client.java']
    assert packages['com.example.impl']['files'] == ['Impl.java']


# =============================================================================
# Tests: Test Package Discovery
# =============================================================================


def test_test_packages_from_test_sources(tmp_path):
    """Test packages are discovered from src/test/java."""
    _create_java_package(
        tmp_path,
        'src/test/java',
        'com/example/util',
        [
            'MoreStringsTest.java',
            'CollectionBuilderTest.java',
        ],
    )

    test_pkgs = discover_packages(tmp_path, ['src/test/java'], '')

    assert 'com.example.util' in test_pkgs
    assert test_pkgs['com.example.util']['files'] == ['CollectionBuilderTest.java', 'MoreStringsTest.java']


def test_test_packages_independent_from_main(tmp_path):
    """Main and test packages are discovered independently."""
    _create_java_package(tmp_path, 'src/main/java', 'com/example', ['Service.java'])
    _create_java_package(tmp_path, 'src/test/java', 'com/example', ['ServiceTest.java'])

    main_pkgs = discover_packages(tmp_path, ['src/main/java'], '')
    test_pkgs = discover_packages(tmp_path, ['src/test/java'], '')

    assert main_pkgs['com.example']['files'] == ['Service.java']
    assert main_pkgs['com.example']['path'] == 'src/main/java/com/example'
    assert test_pkgs['com.example']['files'] == ['ServiceTest.java']
    assert test_pkgs['com.example']['path'] == 'src/test/java/com/example'


def test_test_packages_empty_when_no_test_sources(tmp_path):
    """No test packages when test source dir is missing."""
    _create_java_package(tmp_path, 'src/main/java', 'com/example', ['App.java'])

    test_pkgs = discover_packages(tmp_path, ['src/test/java'], '')

    assert len(test_pkgs) == 0


def test_test_packages_with_relative_path(tmp_path):
    """Test package paths include relative_path prefix."""
    _create_java_package(tmp_path, 'src/test/java', 'com/example', ['AppTest.java'])

    test_pkgs = discover_packages(tmp_path, ['src/test/java'], 'my-module')

    assert test_pkgs['com.example']['path'] == 'my-module/src/test/java/com/example'


# =============================================================================
# Tests: Multi-language Support
# =============================================================================


def test_kotlin_packages_discovered(tmp_path):
    """Kotlin source files create packages."""
    pkg_dir = tmp_path / 'src' / 'main' / 'kotlin' / 'com' / 'example'
    pkg_dir.mkdir(parents=True)
    (pkg_dir / 'App.kt').write_text('class App')

    packages = discover_packages(tmp_path, ['src/main/kotlin'], '')

    assert 'com.example' in packages
    assert packages['com.example']['files'] == ['App.kt']


def test_mixed_java_kotlin_package(tmp_path):
    """Package with both Java and Kotlin files lists all source files."""
    pkg_dir = tmp_path / 'src' / 'main' / 'java' / 'com' / 'example'
    pkg_dir.mkdir(parents=True)
    (pkg_dir / 'Service.java').write_text('// java')
    (pkg_dir / 'Helper.kt').write_text('// kotlin')

    packages = discover_packages(tmp_path, ['src/main/java'], '')

    assert 'com.example' in packages
    assert packages['com.example']['files'] == ['Helper.kt', 'Service.java']


def test_resources_dir_skipped(tmp_path):
    """Resource directories are skipped during package discovery."""
    res_dir = tmp_path / 'src' / 'main' / 'resources' / 'com' / 'example'
    res_dir.mkdir(parents=True)
    (res_dir / 'config.properties').write_text('key=value')

    packages = discover_packages(tmp_path, ['src/main/resources'], '')

    assert len(packages) == 0
