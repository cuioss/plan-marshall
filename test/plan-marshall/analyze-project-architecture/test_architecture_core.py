#!/usr/bin/env python3
"""Tests for _architecture_core.py module."""

import json
import sys
import tempfile
from pathlib import Path

# Import modules under test (PYTHONPATH set by conftest)
from _architecture_core import (
    DATA_DIR,
    DataNotFoundError,
    ModuleNotFoundError,
    format_toon_value,
    get_data_dir,
    get_derived_path,
    get_enriched_path,
    get_module,
    get_module_names,
    get_root_module,
    load_derived_data,
    load_llm_enriched,
    load_llm_enriched_or_empty,
    merge_module_data,
    save_derived_data,
    save_llm_enriched,
)

# =============================================================================
# Tests for Path Functions
# =============================================================================

def test_get_data_dir_default():
    """get_data_dir returns .plan/project-architecture by default."""
    path = get_data_dir()
    assert path == Path(".") / DATA_DIR


def test_get_data_dir_with_project():
    """get_data_dir respects project_dir parameter."""
    path = get_data_dir("/my/project")
    assert path == Path("/my/project") / DATA_DIR


def test_get_derived_path():
    """get_derived_path returns correct path."""
    path = get_derived_path("/my/project")
    assert str(path).endswith("derived-data.json")


def test_get_enriched_path():
    """get_enriched_path returns correct path."""
    path = get_enriched_path("/my/project")
    assert str(path).endswith("llm-enriched.json")


# =============================================================================
# Tests for Load/Save Operations
# =============================================================================

def test_load_derived_data_success():
    """load_derived_data loads valid JSON file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir) / ".plan" / "project-architecture"
        data_dir.mkdir(parents=True)
        derived_path = data_dir / "derived-data.json"

        test_data = {"project": {"name": "test"}, "modules": {}}
        derived_path.write_text(json.dumps(test_data))

        result = load_derived_data(tmpdir)
        assert result == test_data


def test_load_derived_data_missing_raises():
    """load_derived_data raises DataNotFoundError when file missing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            load_derived_data(tmpdir)
            assert False, "Should have raised DataNotFoundError"
        except DataNotFoundError as e:
            assert "discover" in str(e).lower()


def test_load_llm_enriched_success():
    """load_llm_enriched loads valid JSON file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir) / ".plan" / "project-architecture"
        data_dir.mkdir(parents=True)
        enriched_path = data_dir / "llm-enriched.json"

        test_data = {"project": {"description": "test"}, "modules": {}}
        enriched_path.write_text(json.dumps(test_data))

        result = load_llm_enriched(tmpdir)
        assert result == test_data


def test_load_llm_enriched_missing_raises():
    """load_llm_enriched raises DataNotFoundError when file missing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            load_llm_enriched(tmpdir)
            assert False, "Should have raised DataNotFoundError"
        except DataNotFoundError as e:
            assert "init" in str(e).lower()


def test_load_llm_enriched_or_empty_returns_empty():
    """load_llm_enriched_or_empty returns empty structure when missing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = load_llm_enriched_or_empty(tmpdir)
        assert result == {"project": {}, "modules": {}}


def test_save_derived_data_creates_dir():
    """save_derived_data creates directory if missing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_data = {"project": {"name": "test"}, "modules": {}}

        result_path = save_derived_data(test_data, tmpdir)

        assert result_path.exists()
        loaded = json.loads(result_path.read_text())
        assert loaded == test_data


def test_save_llm_enriched_creates_dir():
    """save_llm_enriched creates directory if missing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_data = {"project": {"description": "test"}, "modules": {}}

        result_path = save_llm_enriched(test_data, tmpdir)

        assert result_path.exists()
        loaded = json.loads(result_path.read_text())
        assert loaded == test_data


# =============================================================================
# Tests for Module Operations
# =============================================================================

def test_get_module_names():
    """get_module_names returns list of module names."""
    derived = {
        "modules": {
            "module-a": {},
            "module-b": {},
        }
    }
    names = get_module_names(derived)
    assert set(names) == {"module-a", "module-b"}


def test_get_module_names_empty():
    """get_module_names returns empty list when no modules."""
    derived = {"modules": {}}
    names = get_module_names(derived)
    assert names == []


def test_get_root_module_finds_dot():
    """get_root_module finds module at '.' path."""
    derived = {
        "modules": {
            "child": {"paths": {"module": "child"}},
            "parent": {"paths": {"module": "."}},
        }
    }
    root = get_root_module(derived)
    assert root == "parent"


def test_get_root_module_finds_empty():
    """get_root_module finds module with empty path."""
    derived = {
        "modules": {
            "child": {"paths": {"module": "child"}},
            "root": {"paths": {"module": ""}},
        }
    }
    root = get_root_module(derived)
    assert root == "root"


def test_get_root_module_fallback():
    """get_root_module falls back to first module."""
    derived = {
        "modules": {
            "only-module": {"paths": {"module": "only-module"}},
        }
    }
    root = get_root_module(derived)
    assert root == "only-module"


def test_get_module_success():
    """get_module returns module data."""
    derived = {
        "modules": {
            "test-module": {"name": "test-module", "data": "value"},
        }
    }
    result = get_module(derived, "test-module")
    assert result["data"] == "value"


def test_get_module_not_found_raises():
    """get_module raises ModuleNotFoundError when not found."""
    derived = {"modules": {"existing": {}}}
    try:
        get_module(derived, "missing")
        assert False, "Should have raised ModuleNotFoundError"
    except ModuleNotFoundError:
        pass


# =============================================================================
# Tests for Merge Operations
# =============================================================================

def test_merge_module_data_combines():
    """merge_module_data combines derived and enriched data."""
    derived = {
        "modules": {
            "test": {
                "name": "test",
                "paths": {"module": "test"},
                "dependencies": ["dep1"],
            }
        }
    }
    enriched = {
        "modules": {
            "test": {
                "responsibility": "Test module",
                "purpose": "library",
            }
        }
    }

    result = merge_module_data(derived, enriched, "test")

    assert result["name"] == "test"
    assert result["paths"]["module"] == "test"
    assert result["dependencies"] == ["dep1"]
    assert result["responsibility"] == "Test module"
    assert result["purpose"] == "library"


def test_merge_module_data_enriched_overwrites():
    """merge_module_data allows enriched to override derived."""
    derived = {
        "modules": {
            "test": {"description": "derived desc"}
        }
    }
    enriched = {
        "modules": {
            "test": {"description": "enriched desc"}
        }
    }

    result = merge_module_data(derived, enriched, "test")
    assert result["description"] == "enriched desc"


def test_merge_module_data_empty_enriched():
    """merge_module_data handles empty enriched data."""
    derived = {
        "modules": {
            "test": {"name": "test", "paths": {}}
        }
    }
    enriched = {"modules": {}}

    result = merge_module_data(derived, enriched, "test")
    assert result["name"] == "test"


def test_merge_module_data_skills_by_profile():
    """merge_module_data includes skills_by_profile from enriched data."""
    derived = {
        "modules": {
            "test": {
                "name": "test",
                "paths": {"module": "test"},
            }
        }
    }
    enriched = {
        "modules": {
            "test": {
                "skills_by_profile": {
                    "implementation": ["pm-dev-java:java-core"],
                    "unit-testing": ["pm-dev-java:junit-core"]
                }
            }
        }
    }

    result = merge_module_data(derived, enriched, "test")

    assert "skills_by_profile" in result
    assert result["skills_by_profile"]["implementation"] == ["pm-dev-java:java-core"]
    assert result["skills_by_profile"]["unit-testing"] == ["pm-dev-java:junit-core"]


# =============================================================================
# Tests for TOON Formatting
# =============================================================================

def test_format_toon_value_none():
    """format_toon_value returns empty string for None."""
    assert format_toon_value(None) == ""


def test_format_toon_value_bool():
    """format_toon_value formats booleans."""
    assert format_toon_value(True) == "true"
    assert format_toon_value(False) == "false"


def test_format_toon_value_list():
    """format_toon_value joins list with +."""
    assert format_toon_value(["a", "b", "c"]) == "a+b+c"


def test_format_toon_value_string():
    """format_toon_value passes strings through."""
    assert format_toon_value("test") == "test"


def test_format_toon_value_int():
    """format_toon_value converts int to string."""
    assert format_toon_value(42) == "42"


if __name__ == "__main__":
    import traceback

    tests = [
        test_get_data_dir_default,
        test_get_data_dir_with_project,
        test_get_derived_path,
        test_get_enriched_path,
        test_load_derived_data_success,
        test_load_derived_data_missing_raises,
        test_load_llm_enriched_success,
        test_load_llm_enriched_missing_raises,
        test_load_llm_enriched_or_empty_returns_empty,
        test_save_derived_data_creates_dir,
        test_save_llm_enriched_creates_dir,
        test_get_module_names,
        test_get_module_names_empty,
        test_get_root_module_finds_dot,
        test_get_root_module_finds_empty,
        test_get_root_module_fallback,
        test_get_module_success,
        test_get_module_not_found_raises,
        test_merge_module_data_combines,
        test_merge_module_data_enriched_overwrites,
        test_merge_module_data_empty_enriched,
        test_merge_module_data_skills_by_profile,
        test_format_toon_value_none,
        test_format_toon_value_bool,
        test_format_toon_value_list,
        test_format_toon_value_string,
        test_format_toon_value_int,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
            print(f"PASSED: {test.__name__}")
        except Exception:
            failed += 1
            print(f"FAILED: {test.__name__}")
            traceback.print_exc()
            print()

    print(f"\nResults: {passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)
