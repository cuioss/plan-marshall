# Python Suppression Syntax

Domain-specific suppression methods for Python tooling.

## Ruff

### Inline Suppression

```python
# Suppress specific rule on a single line
long_variable_name = some_function()  # noqa: E501

# Suppress multiple rules
value = eval(user_input)  # noqa: S307, E501
```

### File-Level Suppression

```python
# ruff: noqa: E501
# Placed at the top of the file, suppresses E501 for the entire file
```

### Project-Level Suppression (pyproject.toml)

```toml
[tool.ruff.lint]
# Globally ignored rules
ignore = ["D100", "D104"]  # Missing module/package docstrings

[tool.ruff.lint.per-file-ignores]
# Suppress rules for specific file patterns
"test_*.py" = ["S101"]      # Allow assert in tests
"__init__.py" = ["F401"]    # Allow unused imports in __init__
"conftest.py" = ["E501"]    # Allow long lines in fixtures
```

## Mypy

### Inline Suppression

```python
# Suppress specific mypy error category
result: str = dynamic_call()  # type: ignore[assignment]

# Suppress all mypy errors on a line (use sparingly)
value = untyped_lib.get()  # type: ignore
```

### Per-Module Suppression (pyproject.toml)

```toml
[[tool.mypy.overrides]]
module = "generated_code.*"
ignore_errors = true

[[tool.mypy.overrides]]
module = "vendored_lib.*"
ignore_missing_imports = true
```

## Pytest

### Skip and Expected Failure

```python
import pytest

# Skip unconditionally
@pytest.mark.skip(reason="Requires external service")
def test_external_api():
    ...

# Skip conditionally
@pytest.mark.skipif(
    sys.platform == "win32",
    reason="Unix-only test"
)
def test_unix_permissions():
    ...

# Expected failure (test runs but failure is not reported)
@pytest.mark.xfail(reason="Known upstream bug, see #123")
def test_known_issue():
    ...
```

### Filtering in pyproject.toml

```toml
[tool.pytest.ini_options]
# Exclude paths from collection
testpaths = ["test"]
norecursedirs = ["vendor", "generated"]

# Register custom markers
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    "integration: marks integration tests",
]
```

## Suppression Guidelines

| Scenario | Recommended Approach |
|----------|---------------------|
| Generated code | Per-file-ignores in pyproject.toml |
| Vendored dependencies | mypy overrides + ruff per-file-ignores |
| Dynamic/metaprogramming | Inline `# type: ignore[specific-code]` |
| Security false positive | Inline `# noqa: S-code` with comment explaining why |
| Platform-specific test | `@pytest.mark.skipif` with platform condition |
| Known upstream bug | `@pytest.mark.xfail` with issue link |
| Legacy code migration | Per-file-ignores, remove as files are modernized |
