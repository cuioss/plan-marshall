#!/usr/bin/env python3
"""Tests for _cmd_manage.py module."""

import json
import sys
import tempfile
from pathlib import Path

# Import modules under test (PYTHONPATH set by conftest)
from _cmd_manage import (
    api_init,
    api_get_derived,
    api_get_derived_module,
    list_modules,
)
from _architecture_core import (
    DataNotFoundError,
    ModuleNotFoundError,
    save_derived_data,
)


# =============================================================================
# Helper Functions
# =============================================================================

def create_test_derived_data(tmpdir: str) -> dict:
    """Create test derived-data.json and return the data."""
    test_data = {
        "project": {
            "name": "test-project"
        },
        "modules": {
            "module-a": {
                "name": "module-a",
                "build_systems": ["maven"],
                "paths": {
                    "module": "module-a",
                    "descriptor": "module-a/pom.xml",
                    "sources": ["module-a/src/main/java"],
                    "tests": ["module-a/src/test/java"],
                    "readme": "module-a/README.md"
                },
                "metadata": {
                    "artifact_id": "module-a",
                    "description": "Module A description"
                },
                "packages": {
                    "com.example.a": {"path": "module-a/src/main/java/com/example/a"}
                },
                "dependencies": ["org.example:dep1:compile"],
                "stats": {"source_files": 10, "test_files": 5},
                "commands": {
                    "module-tests": "python3 .plan/execute-script.py ...",
                    "verify": "python3 .plan/execute-script.py ..."
                }
            },
            "module-b": {
                "name": "module-b",
                "build_systems": ["maven"],
                "paths": {
                    "module": "module-b"
                },
                "metadata": {},
                "packages": {},
                "dependencies": [],
                "stats": {},
                "commands": {}
            }
        }
    }
    save_derived_data(test_data, tmpdir)
    return test_data


# =============================================================================
# Tests for api_init
# =============================================================================

def test_api_init_creates_enrichment():
    """api_init creates llm-enriched.json with module stubs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_derived_data(tmpdir)

        result = api_init(tmpdir)

        assert result["status"] == "success"
        assert result["modules_initialized"] == 2
        assert "output_file" in result

        # Verify file created
        enriched_path = Path(tmpdir) / ".plan" / "project-architecture" / "llm-enriched.json"
        assert enriched_path.exists()

        # Verify structure
        enriched = json.loads(enriched_path.read_text())
        assert "project" in enriched
        assert "modules" in enriched
        assert "module-a" in enriched["modules"]
        assert "module-b" in enriched["modules"]
        assert "responsibility" in enriched["modules"]["module-a"]


def test_api_init_check_existing():
    """api_init with check=True reports existing file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_derived_data(tmpdir)

        # First create the file
        api_init(tmpdir)

        # Then check
        result = api_init(tmpdir, check=True)

        assert result["status"] == "exists"
        assert result["modules_enriched"] == 2


def test_api_init_check_missing():
    """api_init with check=True reports missing file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_derived_data(tmpdir)

        result = api_init(tmpdir, check=True)

        assert result["status"] == "missing"


def test_api_init_no_overwrite():
    """api_init does not overwrite without force flag."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_derived_data(tmpdir)

        # First create
        api_init(tmpdir)

        # Try again without force
        result = api_init(tmpdir)

        assert result["status"] == "exists"
        assert "force" in result.get("message", "").lower()


def test_api_init_force_overwrites():
    """api_init with force=True overwrites existing file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_derived_data(tmpdir)

        # First create
        api_init(tmpdir)

        # Force overwrite
        result = api_init(tmpdir, force=True)

        assert result["status"] == "success"


def test_api_init_missing_derived():
    """api_init returns error when derived-data.json missing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = api_init(tmpdir)

        assert result["status"] == "error"
        assert "discover" in result.get("error", "").lower()


# =============================================================================
# Tests for api_get_derived
# =============================================================================

def test_api_get_derived_returns_data():
    """api_get_derived returns derived data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_data = create_test_derived_data(tmpdir)

        result = api_get_derived(tmpdir)

        assert result["project"]["name"] == "test-project"
        assert "module-a" in result["modules"]
        assert "module-b" in result["modules"]


def test_api_get_derived_missing_raises():
    """api_get_derived raises DataNotFoundError when file missing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            api_get_derived(tmpdir)
            assert False, "Should have raised DataNotFoundError"
        except DataNotFoundError:
            pass


# =============================================================================
# Tests for api_get_derived_module
# =============================================================================

def test_api_get_derived_module_returns_module():
    """api_get_derived_module returns single module data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_derived_data(tmpdir)

        result = api_get_derived_module("module-a", tmpdir)

        assert result["name"] == "module-a"
        assert result["build_systems"] == ["maven"]
        assert "com.example.a" in result["packages"]


def test_api_get_derived_module_not_found_raises():
    """api_get_derived_module raises ModuleNotFoundError."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_derived_data(tmpdir)

        try:
            api_get_derived_module("nonexistent", tmpdir)
            assert False, "Should have raised ModuleNotFoundError"
        except ModuleNotFoundError:
            pass


# =============================================================================
# Tests for list_modules
# =============================================================================

def test_list_modules_returns_names():
    """list_modules returns list of module names."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_derived_data(tmpdir)

        result = list_modules(tmpdir)

        assert set(result) == {"module-a", "module-b"}


def test_list_modules_missing_raises():
    """list_modules raises DataNotFoundError when file missing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            list_modules(tmpdir)
            assert False, "Should have raised DataNotFoundError"
        except DataNotFoundError:
            pass


if __name__ == "__main__":
    import traceback

    tests = [
        test_api_init_creates_enrichment,
        test_api_init_check_existing,
        test_api_init_check_missing,
        test_api_init_no_overwrite,
        test_api_init_force_overwrites,
        test_api_init_missing_derived,
        test_api_get_derived_returns_data,
        test_api_get_derived_missing_raises,
        test_api_get_derived_module_returns_module,
        test_api_get_derived_module_not_found_raises,
        test_list_modules_returns_names,
        test_list_modules_missing_raises,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
            print(f"PASSED: {test.__name__}")
        except Exception as e:
            failed += 1
            print(f"FAILED: {test.__name__}")
            traceback.print_exc()
            print()

    print(f"\nResults: {passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)
