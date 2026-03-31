---
name: pytest-testing
description: Python unit testing standards covering pytest framework, test structure, AAA pattern, fixtures, parametrization, isolation, mocking, assertions, and coverage configuration
user-invocable: false
---

# Pytest Testing Standards

Standards for writing reliable, isolated pytest tests in Python projects.

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

## Standards Documents

| Document | Content |
|----------|---------|
| [testing-pytest.md](standards/testing-pytest.md) | Complete pytest reference — naming, AAA pattern, isolation, fixtures, parametrization, mocking, assertions, conftest, running tests |

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
