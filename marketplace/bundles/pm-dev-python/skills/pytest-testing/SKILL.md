---
name: pytest-testing
description: "Use when writing, reviewing, or debugging Python tests — covers pytest framework, AAA pattern, fixtures, parametrization, isolation, mocking, assertions, and coverage configuration. Activate for any Python testing task."
user-invocable: false
---

# Pytest Testing Standards

**REFERENCE MODE**: This skill provides reference material for writing pytest tests. Load standards on-demand based on current task.

## Enforcement

**Execution mode**: Reference library; load standards on-demand for Python testing tasks.

**Prohibited actions:**
- Do not use `unittest.TestCase` for new tests; use plain pytest functions
- Do not share mutable state between tests without fixture isolation
- Do not use `os.chdir()` without restoration (use `monkeypatch.chdir()`)

**Constraints:**
- Tests must follow AAA (Arrange-Act-Assert) pattern
- Each test must be independent and isolated
- Fixtures must use appropriate scope (function/module/session)
- Working directory changes must be restored after each test

## When to Use This Skill

Activate when:
- **Writing new pytest tests** — test structure, naming, AAA pattern
- **Debugging test failures** — isolation issues, fixture scoping, state leaks
- **Adding fixtures** — shared setup, parametrization, conftest organization
- **Mocking dependencies** — `monkeypatch`, `unittest.mock.patch`, state patching
- **Reviewing test code** — checking isolation, assertion quality, coverage gaps
- **Configuring test infrastructure** — conftest.py, markers, coverage settings

## Available References

**File**: `standards/testing-pytest.md` (331 lines)

**Load When**:
- Writing or reviewing pytest test code
- Setting up test infrastructure (conftest, fixtures)
- Debugging isolation or mocking issues
- Organizing test file structure

**Contents**:
- Test naming conventions (files and functions)
- AAA pattern with examples
- Isolation patterns (`tmp_path`, `monkeypatch`, `_restore_cwd`)
- Script path discovery (dual-path pattern)
- Fixture scope and autouse
- Parametrization
- Mocking (module state, functions)
- Assertions (basic, exceptions, approximate)
- Output capture (`capsys`, `capfd`)
- Subprocess / script testing patterns (structured output, PYTHONPATH, error paths)
- Test organization (conftest, file structure)

**Load Command**:
```
Read standards/testing-pytest.md
```

## Quick Reference

| Topic | Rule |
|-------|------|
| File naming | `test_<module>.py` |
| Function naming | `test_<behavior>` — descriptive of what is tested |
| Structure | Arrange-Act-Assert (AAA) |
| Isolation | `tmp_path` for files, `monkeypatch` for state, autouse `_restore_cwd` |
| Fixtures | `conftest.py` for shared, function scope by default |
| Parametrize | `@pytest.mark.parametrize` for input variations |
| Exceptions | `pytest.raises(ExcType, match="pattern")` |
| Approximate | `pytest.approx(value, rel=tolerance)` |
| Output capture | `capsys` for Python, `capfd` for subprocess output |
| Script testing | `subprocess.run` with `capture_output=True, text=True, timeout=30` |

## Running Tests

```bash
# Via build system
python3 .plan/execute-script.py plan-marshall:build-python:python_build run --command-args "module-tests"

# Specific module
python3 .plan/execute-script.py plan-marshall:build-python:python_build run --command-args "module-tests pm-dev-python"

# With coverage
python3 .plan/execute-script.py plan-marshall:build-python:python_build run --command-args "coverage"
```

## Related Skills

- `pm-dev-python:python-core` - Core Python development patterns
- `plan-marshall:dev-general-module-testing` - Language-agnostic testing methodology
