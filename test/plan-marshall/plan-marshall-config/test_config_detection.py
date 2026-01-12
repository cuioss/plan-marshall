#!/usr/bin/env python3
"""Tests for config_detection module.

Tests module detection including nested Maven modules and npm workspaces.
"""

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import TestRunner

# Import functions under test (PYTHONPATH set by conftest)
from _config_detection import detect_maven_modules, detect_npm_workspaces


class TempProjectContext:
    """Context manager for creating temporary project structures."""

    def __init__(self):
        self.temp_dir = None
        self.original_cwd = None

    def __enter__(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def create_pom(self, path: str, modules: list = None):
        """Create a pom.xml file with optional modules section."""
        pom_path = self.temp_dir / path / 'pom.xml' if path else self.temp_dir / 'pom.xml'
        pom_path.parent.mkdir(parents=True, exist_ok=True)

        modules_xml = ""
        if modules:
            modules_xml = "<modules>\n"
            for mod in modules:
                modules_xml += f"    <module>{mod}</module>\n"
            modules_xml += "  </modules>"

        content = f"""<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.example</groupId>
  <artifactId>test-project</artifactId>
  <version>1.0.0</version>
  {modules_xml}
</project>
"""
        pom_path.write_text(content)

    def create_package_json(self, path: str, name: str = None, workspaces: list = None):
        """Create a package.json file."""
        pkg_path = self.temp_dir / path / 'package.json' if path else self.temp_dir / 'package.json'
        pkg_path.parent.mkdir(parents=True, exist_ok=True)

        content = {"name": name or "test-package", "version": "1.0.0"}
        if workspaces:
            content["workspaces"] = workspaces

        pkg_path.write_text(json.dumps(content, indent=2))


# =============================================================================
# Maven Module Detection Tests
# =============================================================================

def test_detect_maven_no_pom():
    """Test detection with no pom.xml returns empty list."""
    with TempProjectContext():
        result = detect_maven_modules()
        assert result == [], f"Expected empty list, got {result}"


def test_detect_maven_single_level():
    """Test detection of top-level modules."""
    with TempProjectContext() as ctx:
        ctx.create_pom("", modules=["module-a", "module-b"])
        ctx.create_pom("module-a")
        ctx.create_pom("module-b")

        result = detect_maven_modules()

        assert len(result) == 2, f"Expected 2 modules, got {len(result)}"
        names = [m["name"] for m in result]
        assert "module-a" in names
        assert "module-b" in names


def test_detect_maven_nested_modules():
    """Test detection of nested modules (2 levels)."""
    with TempProjectContext() as ctx:
        # Root with parent module
        ctx.create_pom("", modules=["parent-module"])
        # Parent with children
        ctx.create_pom("parent-module", modules=["child-a", "child-b"])
        ctx.create_pom("parent-module/child-a")
        ctx.create_pom("parent-module/child-b")

        result = detect_maven_modules()

        assert len(result) == 3, f"Expected 3 modules, got {len(result)}"
        names = [m["name"] for m in result]
        assert "parent-module" in names
        assert "child-a" in names
        assert "child-b" in names


def test_detect_maven_three_level_nesting():
    """Test detection of deeply nested modules (3 levels)."""
    with TempProjectContext() as ctx:
        ctx.create_pom("", modules=["level1"])
        ctx.create_pom("level1", modules=["level2"])
        ctx.create_pom("level1/level2", modules=["level3"])
        ctx.create_pom("level1/level2/level3")

        result = detect_maven_modules()

        assert len(result) == 3, f"Expected 3 modules, got {len(result)}"
        # Check paths are correct
        paths = {m["name"]: m["path"] for m in result}
        assert paths["level1"] == "level1"
        assert paths["level2"] == "level1/level2"
        assert paths["level3"] == "level1/level2/level3"


def test_detect_maven_parent_relationships():
    """Test that parent relationships are captured."""
    with TempProjectContext() as ctx:
        ctx.create_pom("", modules=["parent"])
        ctx.create_pom("parent", modules=["child"])
        ctx.create_pom("parent/child")

        result = detect_maven_modules()

        # Find parent module - should have no parent field
        parent_mod = next(m for m in result if m["name"] == "parent")
        assert "parent" not in parent_mod, "Root-level module should not have parent field"

        # Find child module - should have parent field
        child_mod = next(m for m in result if m["name"] == "child")
        assert child_mod.get("parent") == "parent", f"Child should have parent='parent', got {child_mod.get('parent')}"


def test_detect_maven_missing_module_directory():
    """Test that modules without directories are skipped."""
    with TempProjectContext() as ctx:
        ctx.create_pom("", modules=["exists", "missing"])
        ctx.create_pom("exists")
        # Don't create "missing" directory

        result = detect_maven_modules()

        assert len(result) == 1, f"Expected 1 module, got {len(result)}"
        assert result[0]["name"] == "exists"


def test_detect_maven_oauth_sheriff_structure():
    """Test detection matching OAuth-Sheriff project structure."""
    with TempProjectContext() as ctx:
        # Simulate OAuth-Sheriff structure
        ctx.create_pom("", modules=[
            "bom",
            "oauth-sheriff-core",
            "oauth-sheriff-quarkus-parent",
            "benchmarking"
        ])
        ctx.create_pom("bom")
        ctx.create_pom("oauth-sheriff-core")
        ctx.create_pom("oauth-sheriff-quarkus-parent", modules=[
            "oauth-sheriff-quarkus",
            "oauth-sheriff-quarkus-deployment",
            "oauth-sheriff-quarkus-integration-tests"
        ])
        ctx.create_pom("oauth-sheriff-quarkus-parent/oauth-sheriff-quarkus")
        ctx.create_pom("oauth-sheriff-quarkus-parent/oauth-sheriff-quarkus-deployment")
        ctx.create_pom("oauth-sheriff-quarkus-parent/oauth-sheriff-quarkus-integration-tests")
        ctx.create_pom("benchmarking", modules=[
            "benchmark-core",
            "benchmark-integration-wrk",
            "benchmarking-common"
        ])
        ctx.create_pom("benchmarking/benchmark-core")
        ctx.create_pom("benchmarking/benchmark-integration-wrk")
        ctx.create_pom("benchmarking/benchmarking-common")

        result = detect_maven_modules()

        # Should find all 10 modules (not just 4)
        assert len(result) == 10, f"Expected 10 modules, got {len(result)}: {[m['name'] for m in result]}"

        # Verify nested module paths
        paths = {m["name"]: m["path"] for m in result}
        assert paths["oauth-sheriff-quarkus"] == "oauth-sheriff-quarkus-parent/oauth-sheriff-quarkus"
        assert paths["benchmarking-common"] == "benchmarking/benchmarking-common"


# =============================================================================
# npm Workspace Detection Tests
# =============================================================================

def test_detect_npm_no_package_json():
    """Test detection with no package.json returns empty list."""
    with TempProjectContext():
        result = detect_npm_workspaces()
        assert result == [], f"Expected empty list, got {result}"


def test_detect_npm_no_workspaces():
    """Test detection with package.json but no workspaces."""
    with TempProjectContext() as ctx:
        ctx.create_package_json("", name="root-pkg")

        result = detect_npm_workspaces()
        assert result == [], f"Expected empty list, got {result}"


def test_detect_npm_workspaces_direct_paths():
    """Test detection with direct workspace paths."""
    with TempProjectContext() as ctx:
        ctx.create_package_json("", name="root", workspaces=["packages/pkg-a", "packages/pkg-b"])
        ctx.create_package_json("packages/pkg-a", name="@scope/pkg-a")
        ctx.create_package_json("packages/pkg-b", name="@scope/pkg-b")

        result = detect_npm_workspaces()

        assert len(result) == 2, f"Expected 2 workspaces, got {len(result)}"
        names = [m["name"] for m in result]
        assert "@scope/pkg-a" in names
        assert "@scope/pkg-b" in names


def test_detect_npm_workspaces_glob_pattern():
    """Test detection with glob patterns like packages/*."""
    with TempProjectContext() as ctx:
        ctx.create_package_json("", name="root", workspaces=["packages/*"])
        ctx.create_package_json("packages/core", name="@myorg/core")
        ctx.create_package_json("packages/utils", name="@myorg/utils")
        ctx.create_package_json("packages/cli", name="@myorg/cli")

        result = detect_npm_workspaces()

        assert len(result) == 3, f"Expected 3 workspaces, got {len(result)}"
        names = [m["name"] for m in result]
        assert "@myorg/core" in names
        assert "@myorg/utils" in names
        assert "@myorg/cli" in names


def test_detect_npm_workspaces_multiple_patterns():
    """Test detection with multiple workspace patterns."""
    with TempProjectContext() as ctx:
        ctx.create_package_json("", name="root", workspaces=["packages/*", "apps/*"])
        ctx.create_package_json("packages/lib", name="@proj/lib")
        ctx.create_package_json("apps/web", name="@proj/web")
        ctx.create_package_json("apps/api", name="@proj/api")

        result = detect_npm_workspaces()

        assert len(result) == 3, f"Expected 3 workspaces, got {len(result)}"
        paths = [m["path"] for m in result]
        assert "packages/lib" in paths
        assert "apps/web" in paths
        assert "apps/api" in paths


def test_detect_npm_workspaces_object_format():
    """Test detection with object format workspaces config."""
    with TempProjectContext() as ctx:
        # Some projects use {"packages": [...]} format
        (ctx.temp_dir / "package.json").write_text(json.dumps({
            "name": "root",
            "workspaces": {"packages": ["packages/*"]}
        }))
        ctx.create_package_json("packages/foo", name="foo")

        result = detect_npm_workspaces()

        assert len(result) == 1, f"Expected 1 workspace, got {len(result)}"
        assert result[0]["name"] == "foo"


def test_detect_npm_workspaces_missing_package_json():
    """Test that directories without package.json are skipped."""
    with TempProjectContext() as ctx:
        ctx.create_package_json("", name="root", workspaces=["packages/*"])
        ctx.create_package_json("packages/has-pkg", name="has-pkg")
        # Create directory without package.json
        (ctx.temp_dir / "packages" / "no-pkg").mkdir(parents=True)

        result = detect_npm_workspaces()

        assert len(result) == 1, f"Expected 1 workspace, got {len(result)}"
        assert result[0]["name"] == "has-pkg"


# =============================================================================
# Main
# =============================================================================

if __name__ == '__main__':
    runner = TestRunner()
    runner.add_tests([
        # Maven tests
        test_detect_maven_no_pom,
        test_detect_maven_single_level,
        test_detect_maven_nested_modules,
        test_detect_maven_three_level_nesting,
        test_detect_maven_parent_relationships,
        test_detect_maven_missing_module_directory,
        test_detect_maven_oauth_sheriff_structure,
        # npm tests
        test_detect_npm_no_package_json,
        test_detect_npm_no_workspaces,
        test_detect_npm_workspaces_direct_paths,
        test_detect_npm_workspaces_glob_pattern,
        test_detect_npm_workspaces_multiple_patterns,
        test_detect_npm_workspaces_object_format,
        test_detect_npm_workspaces_missing_package_json,
    ])
    sys.exit(runner.run())
