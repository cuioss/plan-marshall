---
name: build-python
description: Python/pyprojectx build operations with execution and output parsing
user-invocable: false
---

# Build Python

## Enforcement

- Run scripts EXACTLY as documented using `python3 .plan/execute-script.py plan-marshall:build-python:python_build ...`
- Never invoke `./pw` directly outside of script internals
- All script output follows TOON format contract

---

Python build execution via pyprojectx (`./pw` wrapper) with output parsing for mypy, ruff, and pytest.

## Scripts Overview

| Script | Type | Purpose |
|--------|------|---------|
| `python_build.py` | CLI + Library | pyprojectx operations, `execute_direct()` |

## python_build run (Primary API)

```bash
python3 .plan/execute-script.py plan-marshall:build-python:python_build run \
    --command-args "<canonical-command>" \
    [--format <toon|json>] \
    [--mode <mode>] \
    [--timeout <seconds>]
```

**Parameters**:
- `--command-args` - Canonical command to execute (required)
- `--format` - Output format: toon (default) or json
- `--mode` - Output mode: actionable (default), structured, errors
- `--timeout` - Timeout in seconds (default from run-config)

## Error Categories

| Category | Description |
|----------|-------------|
| `type_error` | mypy type errors |
| `lint_error` | ruff violations |
| `test_failure` | pytest test failures |
| `import_error` | Module import errors |

## References

- `plan-marshall:extension-api` - Extension API contract
- `plan-marshall:extension-api/standards/build-execution.md` - Execution patterns and lifecycle
