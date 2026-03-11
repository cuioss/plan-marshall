#!/usr/bin/env python3
"""Unit tests for _discover_packages() and _discover_test_packages() files collection.

Tests that package discovery correctly lists direct .java files
per package, excluding package-info.java and sub-package files.
"""

import sys
from pathlib import Path

# Import shared infrastructure (sets up PYTHONPATH for cross-skill imports)
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Direct imports - conftest sets up PYTHONPATH
from _maven_cmd_discover import _discover_packages, _discover_test_packages  # noqa: E402


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
    _create_java_package(tmp_path, 'src/main/java', 'com/example/util', [
        'MoreStrings.java', 'CollectionBuilder.java', 'MoreCollections.java',
    ])

    sources = {'main': ['src/main/java']}
    packages = _discover_packages(tmp_path, sources, '')

    assert 'com.example.util' in packages
    pkg = packages['com.example.util']
    assert pkg['files'] == ['CollectionBuilder.java', 'MoreCollections.java', 'MoreStrings.java']


def test_subpackage_files_not_in_parent(tmp_path):
    """Parent package only lists its direct files, not sub-package files."""
    _create_java_package(tmp_path, 'src/main/java', 'com/example', ['App.java'])
    _create_java_package(tmp_path, 'src/main/java', 'com/example/sub', ['Helper.java'])

    sources = {'main': ['src/main/java']}
    packages = _discover_packages(tmp_path, sources, '')

    parent = packages['com.example']
    sub = packages['com.example.sub']
    assert parent['files'] == ['App.java']
    assert sub['files'] == ['Helper.java']


def test_package_info_excluded_from_files(tmp_path):
    """package-info.java is excluded from files list but tracked in package_info."""
    _create_java_package(tmp_path, 'src/main/java', 'com/example/core', [
        'Service.java', 'package-info.java',
    ])

    sources = {'main': ['src/main/java']}
    packages = _discover_packages(tmp_path, sources, '')

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

    sources = {'main': ['src/main/java']}
    packages = _discover_packages(tmp_path, sources, '')

    parent = packages['com.example']
    assert 'files' not in parent
    assert 'package_info' in parent


def test_root_package_skipped(tmp_path):
    """Files directly in src/main/java (root package ".") are skipped."""
    src_dir = tmp_path / 'src' / 'main' / 'java'
    src_dir.mkdir(parents=True)
    (src_dir / 'Main.java').write_text('// Main')

    sources = {'main': ['src/main/java']}
    packages = _discover_packages(tmp_path, sources, '')

    assert '.' not in packages
    assert len(packages) == 0


def test_relative_path_prefix(tmp_path):
    """When relative_path is set, paths are prefixed correctly."""
    _create_java_package(tmp_path, 'src/main/java', 'com/example', ['App.java'])

    sources = {'main': ['src/main/java']}
    packages = _discover_packages(tmp_path, sources, 'my-module')

    pkg = packages['com.example']
    assert pkg['path'] == 'my-module/src/main/java/com/example'
    assert pkg['files'] == ['App.java']


def test_multiple_packages_independent_files(tmp_path):
    """Each package gets only its own direct files."""
    _create_java_package(tmp_path, 'src/main/java', 'com/example/api', ['Api.java', 'Client.java'])
    _create_java_package(tmp_path, 'src/main/java', 'com/example/impl', ['Impl.java'])

    sources = {'main': ['src/main/java']}
    packages = _discover_packages(tmp_path, sources, '')

    assert packages['com.example.api']['files'] == ['Api.java', 'Client.java']
    assert packages['com.example.impl']['files'] == ['Impl.java']


# =============================================================================
# Tests: Test Package Discovery
# =============================================================================


def test_test_packages_from_test_sources(tmp_path):
    """Test packages are discovered from src/test/java."""
    _create_java_package(tmp_path, 'src/test/java', 'com/example/util', [
        'MoreStringsTest.java', 'CollectionBuilderTest.java',
    ])

    sources = {'main': [], 'test': ['src/test/java']}
    test_pkgs = _discover_test_packages(tmp_path, sources, '')

    assert 'com.example.util' in test_pkgs
    assert test_pkgs['com.example.util']['files'] == ['CollectionBuilderTest.java', 'MoreStringsTest.java']


def test_test_packages_independent_from_main(tmp_path):
    """Main and test packages are discovered independently."""
    _create_java_package(tmp_path, 'src/main/java', 'com/example', ['Service.java'])
    _create_java_package(tmp_path, 'src/test/java', 'com/example', ['ServiceTest.java'])

    sources = {'main': ['src/main/java'], 'test': ['src/test/java']}
    main_pkgs = _discover_packages(tmp_path, sources, '')
    test_pkgs = _discover_test_packages(tmp_path, sources, '')

    assert main_pkgs['com.example']['files'] == ['Service.java']
    assert main_pkgs['com.example']['path'] == 'src/main/java/com/example'
    assert test_pkgs['com.example']['files'] == ['ServiceTest.java']
    assert test_pkgs['com.example']['path'] == 'src/test/java/com/example'


def test_test_packages_empty_when_no_test_sources(tmp_path):
    """No test packages when test source dir is missing."""
    _create_java_package(tmp_path, 'src/main/java', 'com/example', ['App.java'])

    sources = {'main': ['src/main/java'], 'test': ['src/test/java']}
    test_pkgs = _discover_test_packages(tmp_path, sources, '')

    assert len(test_pkgs) == 0


def test_test_packages_with_relative_path(tmp_path):
    """Test package paths include relative_path prefix."""
    _create_java_package(tmp_path, 'src/test/java', 'com/example', ['AppTest.java'])

    sources = {'main': [], 'test': ['src/test/java']}
    test_pkgs = _discover_test_packages(tmp_path, sources, 'my-module')

    assert test_pkgs['com.example']['path'] == 'my-module/src/test/java/com/example'
