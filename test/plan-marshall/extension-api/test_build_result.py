#!/usr/bin/env python3
"""Tests for build_result.py module."""

import sys
import tempfile
from pathlib import Path

# Import shared infrastructure (conftest.py sets up PYTHONPATH)

# Import modules under test (PYTHONPATH set by conftest)
from _build_result import (
    LOG_BASE_DIR,
    TIMESTAMP_FORMAT,
    STATUS_SUCCESS,
    STATUS_ERROR,
    STATUS_TIMEOUT,
    ERROR_BUILD_FAILED,
    ERROR_TIMEOUT,
    ERROR_EXECUTION_FAILED,
    ERROR_WRAPPER_NOT_FOUND,
    ERROR_LOG_FILE_FAILED,
    REQUIRED_FIELDS,
    create_log_file,
    success_result,
    error_result,
    timeout_result,
    validate_result,
)


def test_log_base_dir():
    """LOG_BASE_DIR has expected value."""
    assert LOG_BASE_DIR == ".plan/temp/build-output"


def test_timestamp_format():
    """TIMESTAMP_FORMAT has expected pattern."""
    assert TIMESTAMP_FORMAT == "%Y-%m-%d-%H%M%S"


def test_status_constants():
    """Status constants have expected values."""
    assert STATUS_SUCCESS == "success"
    assert STATUS_ERROR == "error"
    assert STATUS_TIMEOUT == "timeout"


def test_error_constants():
    """Error constants have expected values."""
    assert ERROR_BUILD_FAILED == "build_failed"
    assert ERROR_TIMEOUT == "timeout"
    assert ERROR_EXECUTION_FAILED == "execution_failed"
    assert ERROR_WRAPPER_NOT_FOUND == "wrapper_not_found"
    assert ERROR_LOG_FILE_FAILED == "log_file_failed"


def test_required_fields():
    """REQUIRED_FIELDS contains all required fields."""
    expected = {"status", "exit_code", "duration_seconds", "log_file", "command"}
    assert REQUIRED_FIELDS == expected


def test_create_log_file_creates():
    """Creates log file in expected location."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = create_log_file("maven", "default", tmpdir)
        assert log_file is not None
        assert Path(log_file).exists()


def test_create_log_file_creates_directories():
    """Creates intermediate directories."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = create_log_file("maven", "core-api", tmpdir)
        assert log_file is not None
        assert Path(log_file).parent.name == "core-api"


def test_create_log_file_path_pattern():
    """Log file follows expected path pattern."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = create_log_file("maven", "default", tmpdir)
        path = Path(log_file)

        assert ".plan/temp/build-output" in str(path)
        assert "/default/" in str(path)
        assert path.name.startswith("maven-")
        assert path.suffix == ".log"


def test_create_log_file_different_build_systems():
    """Works with different build system names."""
    with tempfile.TemporaryDirectory() as tmpdir:
        maven_log = create_log_file("maven", "default", tmpdir)
        gradle_log = create_log_file("gradle", "default", tmpdir)
        npm_log = create_log_file("npm", "default", tmpdir)

        assert "maven-" in maven_log
        assert "gradle-" in gradle_log
        assert "npm-" in npm_log


def test_create_log_file_different_scopes():
    """Creates files in different scope directories."""
    with tempfile.TemporaryDirectory() as tmpdir:
        default_log = create_log_file("maven", "default", tmpdir)
        core_log = create_log_file("maven", "core-api", tmpdir)

        assert "/default/" in default_log
        assert "/core-api/" in core_log


def test_create_log_file_returns_absolute():
    """Returns absolute path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = create_log_file("maven", "default", tmpdir)
        assert Path(log_file).is_absolute()


def test_success_result_basic():
    """Returns dict with all required fields."""
    result = success_result(45, "/path/to/log", "./mvnw clean verify")

    assert result["status"] == STATUS_SUCCESS
    assert result["exit_code"] == 0
    assert result["duration_seconds"] == 45
    assert result["log_file"] == "/path/to/log"
    assert result["command"] == "./mvnw clean verify"


def test_success_result_extra_fields():
    """Extra fields are included."""
    result = success_result(
        45, "/path/to/log", "./mvnw clean verify",
        wrapper="./mvnw"
    )
    assert result["wrapper"] == "./mvnw"


def test_success_result_validates():
    """Result passes validation."""
    result = success_result(45, "/path/to/log", "./mvnw clean verify")
    valid, missing = validate_result(result)
    assert valid
    assert missing == []


def test_error_result_basic():
    """Returns dict with all required fields."""
    result = error_result(
        ERROR_BUILD_FAILED, 1, 23, "/path/to/log", "./mvnw clean verify"
    )

    assert result["status"] == STATUS_ERROR
    assert result["error"] == ERROR_BUILD_FAILED
    assert result["exit_code"] == 1
    assert result["duration_seconds"] == 23
    assert result["log_file"] == "/path/to/log"
    assert result["command"] == "./mvnw clean verify"


def test_error_result_wrapper_not_found():
    """Handles wrapper_not_found error."""
    result = error_result(
        ERROR_WRAPPER_NOT_FOUND, -1, 0, "", "mvnw clean verify"
    )
    assert result["error"] == ERROR_WRAPPER_NOT_FOUND
    assert result["exit_code"] == -1


def test_error_result_extra_fields():
    """Extra fields are included."""
    result = error_result(
        ERROR_BUILD_FAILED, 1, 23, "/path/to/log", "./mvnw clean verify",
        errors=[{"file": "Main.java", "line": 15, "message": "error"}]
    )
    assert "errors" in result
    assert len(result["errors"]) == 1


def test_error_result_validates():
    """Result passes validation."""
    result = error_result(
        ERROR_BUILD_FAILED, 1, 23, "/path/to/log", "./mvnw clean verify"
    )
    valid, missing = validate_result(result)
    assert valid
    assert missing == []


def test_timeout_result_basic():
    """Returns dict with all required fields."""
    result = timeout_result(300, 300, "/path/to/log", "./mvnw clean verify")

    assert result["status"] == STATUS_TIMEOUT
    assert result["error"] == ERROR_TIMEOUT
    assert result["exit_code"] == -1
    assert result["timeout_used_seconds"] == 300
    assert result["duration_seconds"] == 300
    assert result["log_file"] == "/path/to/log"
    assert result["command"] == "./mvnw clean verify"


def test_timeout_result_extra_fields():
    """Extra fields are included."""
    result = timeout_result(
        300, 300, "/path/to/log", "./mvnw clean verify",
        wrapper="./mvnw"
    )
    assert result["wrapper"] == "./mvnw"


def test_timeout_result_validates():
    """Result passes validation."""
    result = timeout_result(300, 300, "/path/to/log", "./mvnw clean verify")
    valid, missing = validate_result(result)
    assert valid
    assert missing == []


def test_validate_result_valid():
    """Returns True for valid result."""
    result = {
        "status": "success",
        "exit_code": 0,
        "duration_seconds": 45,
        "log_file": "/path/to/log",
        "command": "./mvnw clean verify",
    }
    valid, missing = validate_result(result)
    assert valid
    assert missing == []


def test_validate_result_missing_one():
    """Returns False with one missing field."""
    result = {
        "status": "success",
        "exit_code": 0,
        "duration_seconds": 45,
        "log_file": "/path/to/log",
    }
    valid, missing = validate_result(result)
    assert not valid
    assert missing == ["command"]


def test_validate_result_missing_multiple():
    """Returns False with multiple missing fields."""
    result = {"status": "success"}
    valid, missing = validate_result(result)
    assert not valid
    assert "command" in missing
    assert "duration_seconds" in missing
    assert "exit_code" in missing
    assert "log_file" in missing


def test_validate_result_empty():
    """Returns False for empty dict."""
    valid, missing = validate_result({})
    assert not valid
    assert len(missing) == 5


def test_validate_result_non_dict():
    """Returns False for non-dict."""
    valid, missing = validate_result("not a dict")
    assert not valid
    assert len(missing) == 5


def test_validate_result_missing_sorted():
    """Missing fields are sorted alphabetically."""
    result = {"status": "success"}
    valid, missing = validate_result(result)
    assert missing == sorted(missing)


def test_validate_result_extra_fields_ok():
    """Extra fields don't affect validation."""
    result = {
        "status": "success",
        "exit_code": 0,
        "duration_seconds": 45,
        "log_file": "/path/to/log",
        "command": "./mvnw clean verify",
        "extra": "field",
    }
    valid, missing = validate_result(result)
    assert valid
    assert missing == []


if __name__ == "__main__":
    import traceback

    tests = [
        test_log_base_dir,
        test_timestamp_format,
        test_status_constants,
        test_error_constants,
        test_required_fields,
        test_create_log_file_creates,
        test_create_log_file_creates_directories,
        test_create_log_file_path_pattern,
        test_create_log_file_different_build_systems,
        test_create_log_file_different_scopes,
        test_create_log_file_returns_absolute,
        test_success_result_basic,
        test_success_result_extra_fields,
        test_success_result_validates,
        test_error_result_basic,
        test_error_result_wrapper_not_found,
        test_error_result_extra_fields,
        test_error_result_validates,
        test_timeout_result_basic,
        test_timeout_result_extra_fields,
        test_timeout_result_validates,
        test_validate_result_valid,
        test_validate_result_missing_one,
        test_validate_result_missing_multiple,
        test_validate_result_empty,
        test_validate_result_non_dict,
        test_validate_result_missing_sorted,
        test_validate_result_extra_fields_ok,
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
