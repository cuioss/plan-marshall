# Pytest Testing Standards

Standards for writing reliable, isolated pytest tests in Python projects.

## Test Structure

### Naming Conventions

```python
# Test files: test_<module>.py
test_user_service.py
test_build_wrapper.py

# Test functions: test_<behavior>
def test_detect_wrapper_finds_unix_on_unix():
    ...

def test_returns_none_when_missing():
    ...
```

### AAA Pattern

Structure tests with Arrange-Act-Assert:

```python
def test_calculate_total():
    # Arrange
    items = [Item(price=10), Item(price=20)]

    # Act
    result = calculate_total(items)

    # Assert
    assert result == 30
```

## Test Isolation

### Working Directory Restoration

Tests that change `cwd` must restore it. Use an autouse fixture as a safety net:

```python
import os
import pytest

@pytest.fixture(autouse=True)
def _restore_cwd():
    """Restore cwd after each test to prevent pollution."""
    original_cwd = os.getcwd()
    yield
    if os.getcwd() != original_cwd:
        os.chdir(original_cwd)
```

For explicit cwd changes within a test, use `monkeypatch`:

```python
def test_script_in_different_directory(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    # Test runs with tmp_path as cwd
    # Automatically restored after test
```

### Temporary Directories

Use `tmp_path` for isolated file operations:

```python
def test_creates_output_file(tmp_path):
    output = tmp_path / "result.json"
    generate_report(output)
    assert output.exists()
```

## Script Path Discovery

Scripts using `Path.cwd()` break when tests run from different directories. Use dual-path discovery:

```python
from pathlib import Path

# Script-relative path (works regardless of cwd)
SCRIPT_DIR = Path(__file__).resolve().parent
_ROOT_FROM_SCRIPT = SCRIPT_DIR.parent.parent.parent

def find_project_root() -> Path | None:
    """Find root with cwd-first, script-relative fallback.

    cwd-first allows tests to use fixture directories.
    Script-relative fallback works when cwd is different.
    """
    # Check cwd-based paths first (supports test fixtures)
    if (Path.cwd() / 'expected_marker').is_dir():
        return Path.cwd()

    # Fallback to script-relative (works regardless of cwd)
    if _ROOT_FROM_SCRIPT.is_dir():
        return _ROOT_FROM_SCRIPT

    return None
```

## Fixtures

### Scope and Autouse

```python
# Function scope (default) - runs for each test
@pytest.fixture
def sample_data():
    return {"key": "value"}

# Module scope - runs once per test file
@pytest.fixture(scope="module")
def database_connection():
    conn = create_connection()
    yield conn
    conn.close()

# Autouse - runs automatically for every test
@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
```

### Parametrization

```python
@pytest.mark.parametrize("input,expected", [
    ("hello", "HELLO"),
    ("world", "WORLD"),
    ("", ""),
])
def test_uppercase(input, expected):
    assert input.upper() == expected
```

## Mocking

### Patching Module State

```python
from unittest.mock import patch

def test_platform_detection():
    with patch('module.IS_WINDOWS', True):
        result = detect_wrapper()
        assert 'bat' in result
```

### Patching Functions

```python
def test_fallback_to_system(tmp_path):
    with patch('shutil.which', return_value='/usr/bin/tool'):
        result = detect_wrapper(str(tmp_path), 'tool', 'tool.bat', 'tool')
        assert result == 'tool'
```

## Assertions

### Basic Assertions

```python
assert result == expected
assert item in collection
assert value is None
assert len(items) == 3
```

### Exception Testing

```python
import pytest

def test_raises_on_invalid_input():
    with pytest.raises(ValueError, match="must be positive"):
        process_value(-1)
```

### Approximate Comparisons

```python
assert result == pytest.approx(3.14159, rel=1e-3)
```

## Output Capture

### Capturing stdout/stderr

```python
def test_prints_summary(capsys):
    generate_report(data)
    captured = capsys.readouterr()
    assert "Total: 42" in captured.out
    assert captured.err == ""

def test_file_descriptor_output(capfd):
    # capfd captures at file descriptor level (includes subprocess output)
    run_external_tool()
    captured = capfd.readouterr()
    assert "success" in captured.out
```

## Subprocess / Script Testing

Tests that invoke Python scripts via `subprocess.run` are common for CLI tools and marketplace scripts.

### Basic Pattern

```python
import subprocess
from pathlib import Path

def test_script_produces_valid_output(tmp_path):
    # Arrange
    input_file = tmp_path / "input.json"
    input_file.write_text('{"key": "value"}')

    # Act
    result = subprocess.run(
        ["python3", str(script_path), "subcommand", "--arg", str(input_file)],
        capture_output=True,
        text=True,
        timeout=30,
    )

    # Assert
    assert result.returncode == 0, f"Script failed: {result.stderr}"
    assert "expected_output" in result.stdout
```

### Asserting on Structured Output

When scripts emit structured output (JSON, TOON), parse and assert on the structure:

```python
import json

def test_script_returns_structured_data():
    result = subprocess.run(
        ["python3", str(script_path), "list"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["status"] == "ok"
    assert len(data["items"]) > 0
```

### PYTHONPATH for Shared Libraries

Scripts that import shared modules (e.g., `toon_parser`) need PYTHONPATH set:

```python
import os

def test_script_with_shared_imports():
    env = os.environ.copy()
    env["PYTHONPATH"] = str(shared_lib_dir)
    result = subprocess.run(
        ["python3", str(script_path), "run"],
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )
    assert result.returncode == 0
```

### Error Path Testing

```python
def test_script_fails_on_missing_arg():
    result = subprocess.run(
        ["python3", str(script_path)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode != 0
    assert "usage" in result.stderr.lower() or "error" in result.stderr.lower()
```

## Test Organization

### Shared Infrastructure

Place shared fixtures and helpers in `conftest.py`:

```python
# test/conftest.py
import pytest

@pytest.fixture
def sample_config():
    return {"debug": True}

def run_script(script_path, *args):
    """Helper to run scripts with subprocess."""
    ...
```

### Test File Structure

```
test/
├── conftest.py              # Shared fixtures (single top-level conftest)
├── _fixtures.py             # Shared plain-Python helpers (no pytest magic)
├── bundle_name/
│   ├── _fixtures.py         # Bundle-specific private helpers
│   ├── test_feature.py
│   └── test_integration.py
```

Nested sibling `conftest.py` files under skill/bundle test directories are prohibited — see "Conftest Scoping and Module Shadowing" below for the rationale and allow-list.

## Conftest Scoping and Module Shadowing

Pytest resolves `conftest` imports by Python module name, not by path. When a test file executes `from conftest import helper`, Python locates the **nearest ancestor `conftest.py`** — which is whichever `conftest.py` sits closest in the module resolution chain. This creates a silent shadowing hazard in multi-level test trees.

### The Shadowing Hazard

If `test/conftest.py` exports shared helpers (e.g., `get_script_path`, `run_script`), and a skill-level test directory introduces its own sibling `conftest.py`, that sibling **shadows** the root `conftest.py` by module name. Any sibling test module that imports via `from conftest import ...` will bind to the skill-local `conftest.py` and break when the helpers it expects are absent.

```
test/
├── conftest.py                    # exports get_script_path, run_script
├── skill_a/
│   ├── conftest.py                # sibling — SHADOWS root conftest for skill_a tests
│   └── test_feature.py            # from conftest import get_script_path  → ImportError
```

The failure is subtle: pytest collects and runs fine in isolation (when only the root `conftest.py` is on the path), but breaks the moment another `conftest.py` appears alongside the tests — even if that sibling was added for an unrelated purpose.

### Prescription: `_fixtures.py` for Private Helpers

Use `_fixtures.py` — or `{feature}_fixtures.py` for multi-feature suites — as the canonical private helper module for pytest suites. The leading underscore has two effects:

1. **Signals "private helper, not a test target"** — readers immediately recognize the module as support code rather than a test module.
2. **Avoids pytest's automatic test collection** — pytest's default `test_*.py` / `*_test.py` collection patterns do not match `_fixtures.py`, so the helper module is never mistaken for a test file.

```
test/
├── conftest.py                    # pytest fixtures only (no re-exported helpers)
├── _fixtures.py                   # shared plain-Python helpers
├── skill_a/
│   ├── _skill_a_fixtures.py       # skill-specific helpers
│   └── test_feature.py            # from _fixtures import get_script_path
```

Import helpers directly by module name (`from _fixtures import ...` or `from test._fixtures import ...` depending on PYTHONPATH), bypassing the conftest resolution chain entirely.

### Allow-List: When a Nested `conftest.py` Is Acceptable

A `conftest.py` at `test/` root, or a narrowly-scoped nested `conftest.py` that does **not** re-export shared helpers, is acceptable. Examples:

- `test/conftest.py` — the canonical location for shared pytest fixtures and plugins.
- `test/adapters/conftest.py` — narrowly scoped for `sys.path` setup or directory-specific fixtures, without re-exporting shared helpers used by sibling modules.

The invariant: a nested `conftest.py` must not define or re-export symbols that sibling test files import by bare module name.

### Cross-Reference

This is the Python/pytest-specific realization of the language-agnostic rule. See [plan-marshall:dev-general-module-testing — Test Helper Module Organization](../../../plan-marshall/skills/dev-general-module-testing/standards/testing-methodology.md) for the general principle applied across languages.

## Running Tests

```bash
# Run all tests
python3 .plan/execute-script.py plan-marshall:build-python:python_build run --command-args "module-tests"

# Run specific module
python3 .plan/execute-script.py plan-marshall:build-python:python_build run --command-args "module-tests pm-dev-python"

# Run with coverage
python3 .plan/execute-script.py plan-marshall:build-python:python_build run --command-args "coverage"
```
