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
├── conftest.py              # Shared fixtures
├── bundle_name/
│   ├── conftest.py          # Bundle-specific fixtures
│   ├── test_feature.py
│   └── test_integration.py
```

## Running Tests

```bash
# Run all tests
./pw module-tests

# Run specific module
./pw module-tests pm-dev-python

# Run with parallel execution
./pw module-tests -p

# Run with coverage
./pw coverage
```
