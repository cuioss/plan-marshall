#!/usr/bin/env python3
"""Tests for module discovery utilities (via extension_base public API)."""

import sys
import tempfile
from pathlib import Path

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import TestRunner

# Import modules under test (PYTHONPATH set by conftest)
from extension_base import (
    README_PATTERNS,
    EXCLUDE_DIRS,
    ModulePaths,
    ModuleBase,
    discover_descriptors,
    build_module_base,
    find_readme,
)


def test_readme_patterns_defined():
    """README_PATTERNS should contain expected patterns."""
    assert "README.md" in README_PATTERNS
    assert "README.adoc" in README_PATTERNS
    assert "README.txt" in README_PATTERNS
    assert "README" in README_PATTERNS


def test_exclude_dirs_defined():
    """EXCLUDE_DIRS should contain expected directories."""
    assert ".git" in EXCLUDE_DIRS
    assert "node_modules" in EXCLUDE_DIRS
    assert "target" in EXCLUDE_DIRS
    assert "build" in EXCLUDE_DIRS
    assert "__pycache__" in EXCLUDE_DIRS


def test_module_paths_creation():
    """ModulePaths can be created with all fields."""
    paths = ModulePaths(
        module="core",
        descriptor="core/pom.xml",
        readme="core/README.md"
    )
    assert paths.module == "core"
    assert paths.descriptor == "core/pom.xml"
    assert paths.readme == "core/README.md"


def test_module_paths_readme_none():
    """ModulePaths can have None readme."""
    paths = ModulePaths(module="core", descriptor="core/pom.xml", readme=None)
    assert paths.readme is None


def test_module_base_creation():
    """ModuleBase can be created with name and paths."""
    paths = ModulePaths(module="core", descriptor="core/pom.xml", readme=None)
    base = ModuleBase(name="core", paths=paths)
    assert base.name == "core"
    assert base.paths.module == "core"


def test_module_base_to_dict():
    """to_dict returns proper structure."""
    paths = ModulePaths(
        module="core",
        descriptor="core/pom.xml",
        readme="core/README.md"
    )
    base = ModuleBase(name="core", paths=paths)
    result = base.to_dict()

    assert result["name"] == "core"
    assert result["paths"]["module"] == "core"
    assert result["paths"]["descriptor"] == "core/pom.xml"
    assert result["paths"]["readme"] == "core/README.md"


def test_discover_descriptors_empty():
    """Returns empty list for directory without descriptors."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = discover_descriptors(tmpdir, "pom.xml")
        assert result == []


def test_discover_descriptors_single():
    """Finds single descriptor at root."""
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / "pom.xml").touch()
        result = discover_descriptors(tmpdir, "pom.xml")
        assert len(result) == 1
        assert result[0].name == "pom.xml"


def test_discover_descriptors_nested():
    """Finds descriptors at multiple levels."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "pom.xml").touch()
        (root / "core").mkdir()
        (root / "core" / "pom.xml").touch()
        (root / "core" / "api").mkdir()
        (root / "core" / "api" / "pom.xml").touch()

        result = discover_descriptors(tmpdir, "pom.xml")
        assert len(result) == 3


def test_discover_descriptors_depth_ordering():
    """Results are sorted by depth, root first."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir).resolve()
        (root / "deep" / "nested").mkdir(parents=True)
        (root / "deep" / "nested" / "pom.xml").touch()
        (root / "pom.xml").touch()
        (root / "shallow").mkdir()
        (root / "shallow" / "pom.xml").touch()

        result = discover_descriptors(str(root), "pom.xml")
        depths = [len(p.relative_to(root).parts) for p in result]
        assert depths == sorted(depths)


def test_discover_descriptors_excludes_git():
    """Does not search in .git directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / ".git").mkdir()
        (root / ".git" / "pom.xml").touch()
        (root / "pom.xml").touch()

        result = discover_descriptors(tmpdir, "pom.xml")
        assert len(result) == 1
        assert ".git" not in str(result[0])


def test_discover_descriptors_excludes_node_modules():
    """Does not search in node_modules directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "node_modules" / "some-package").mkdir(parents=True)
        (root / "node_modules" / "some-package" / "package.json").touch()
        (root / "package.json").touch()

        result = discover_descriptors(tmpdir, "package.json")
        assert len(result) == 1
        assert "node_modules" not in str(result[0])


def test_discover_descriptors_excludes_target():
    """Does not search in target directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "target").mkdir()
        (root / "target" / "pom.xml").touch()
        (root / "pom.xml").touch()

        result = discover_descriptors(tmpdir, "pom.xml")
        assert len(result) == 1
        assert "target" not in str(result[0])


def test_discover_descriptors_nonexistent():
    """Returns empty list for nonexistent directory."""
    result = discover_descriptors("/nonexistent/path", "pom.xml")
    assert result == []


def test_build_module_base_root():
    """Root module gets name 'default'."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "pom.xml").touch()

        base = build_module_base(tmpdir, str(root / "pom.xml"))
        assert base.name == "default"
        assert base.paths.module == "."
        assert base.paths.descriptor == "pom.xml"


def test_build_module_base_nested():
    """Nested module gets directory name."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "core").mkdir()
        (root / "core" / "pom.xml").touch()

        base = build_module_base(tmpdir, str(root / "core" / "pom.xml"))
        assert base.name == "core"
        assert base.paths.module == "core"
        assert base.paths.descriptor == "core/pom.xml"


def test_build_module_base_deeply_nested():
    """Deeply nested module gets immediate directory name."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "parent" / "child").mkdir(parents=True)
        (root / "parent" / "child" / "pom.xml").touch()

        base = build_module_base(tmpdir, str(root / "parent" / "child" / "pom.xml"))
        assert base.name == "child"
        assert base.paths.module == "parent/child"
        assert base.paths.descriptor == "parent/child/pom.xml"


def test_build_module_base_with_readme():
    """Finds README when present."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "core").mkdir()
        (root / "core" / "pom.xml").touch()
        (root / "core" / "README.md").touch()

        base = build_module_base(tmpdir, str(root / "core" / "pom.xml"))
        assert base.paths.readme == "core/README.md"


def test_build_module_base_without_readme():
    """readme is None when not present."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "core").mkdir()
        (root / "core" / "pom.xml").touch()

        base = build_module_base(tmpdir, str(root / "core" / "pom.xml"))
        assert base.paths.readme is None


def test_find_readme_md():
    """Finds README.md."""
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / "README.md").touch()
        assert find_readme(tmpdir) == "README.md"


def test_find_readme_adoc():
    """Finds README.adoc."""
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / "README.adoc").touch()
        assert find_readme(tmpdir) == "README.adoc"


def test_find_readme_txt():
    """Finds README.txt."""
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / "README.txt").touch()
        assert find_readme(tmpdir) == "README.txt"


def test_find_readme_no_extension():
    """Finds README without extension."""
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / "README").touch()
        assert find_readme(tmpdir) == "README"


def test_find_readme_prefers_md():
    """Prefers README.md when multiple exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / "README.md").touch()
        (Path(tmpdir) / "README.adoc").touch()
        assert find_readme(tmpdir) == "README.md"


def test_find_readme_none():
    """Returns None when no README exists."""
    with tempfile.TemporaryDirectory() as tmpdir:
        assert find_readme(tmpdir) is None


def test_find_readme_nonexistent():
    """Returns None for nonexistent directory."""
    assert find_readme("/nonexistent/path") is None


if __name__ == "__main__":
    import traceback

    tests = [
        test_readme_patterns_defined,
        test_exclude_dirs_defined,
        test_module_paths_creation,
        test_module_paths_readme_none,
        test_module_base_creation,
        test_module_base_to_dict,
        test_discover_descriptors_empty,
        test_discover_descriptors_single,
        test_discover_descriptors_nested,
        test_discover_descriptors_depth_ordering,
        test_discover_descriptors_excludes_git,
        test_discover_descriptors_excludes_node_modules,
        test_discover_descriptors_excludes_target,
        test_discover_descriptors_nonexistent,
        test_build_module_base_root,
        test_build_module_base_nested,
        test_build_module_base_deeply_nested,
        test_build_module_base_with_readme,
        test_build_module_base_without_readme,
        test_find_readme_md,
        test_find_readme_adoc,
        test_find_readme_txt,
        test_find_readme_no_extension,
        test_find_readme_prefers_md,
        test_find_readme_none,
        test_find_readme_nonexistent,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"FAILED: {test.__name__}")
            traceback.print_exc()
            print()

    print(f"\nResults: {passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)
