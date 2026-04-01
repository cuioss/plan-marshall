---
name: build-python
description: Python/pyprojectx build operations with execution and output parsing
user-invocable: false
---

# Build Python

Python build execution via pyprojectx (`./pw` wrapper) with output parsing for mypy, ruff, and pytest.

## Enforcement

**Execution mode**: Run scripts exactly as documented; parse TOON output for status and route accordingly.

**Prohibited actions:**
- Do not invoke `./pw` or pytest/mypy/ruff directly; all builds go through the script API
- Do not invent script arguments not listed in the operations table

**Constraints:**
- All commands use `python3 .plan/execute-script.py plan-marshall:build-python:python_build {command} {args}`
- Output format defaults to TOON; use `--format json` only when explicitly required

## Scripts Overview

| Script | Type | Purpose |
|--------|------|---------|
| `python_build.py` | CLI + Library | pyprojectx operations, `execute_direct()`, coverage config |

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
- `--timeout` - Timeout in seconds (default: 300, adaptive via run-config, min floor: 60s)

## Error Categories

| Category | Description |
|----------|-------------|
| `type_error` | mypy type errors |
| `lint_error` | ruff violations |
| `test_failure` | pytest test failures |
| `import_error` | Module import errors |

## Coverage Report

```bash
python3 .plan/execute-script.py plan-marshall:build-python:python_build coverage-report \
    [--project-path <path>] \
    [--report-path <path>] \
    [--threshold <percent>]
```

**Parameters**:
- `--project-path` - Project directory (for auto-detection of report files)
- `--report-path` - Override coverage XML report path (default: auto-detect)
- `--threshold` - Coverage threshold percent (default: 80)

Parses coverage.py Cobertura XML (`coverage.xml`). Generate with `pytest --cov --cov-report=xml`.

## References

- `plan-marshall:extension-api` - Extension API contract
- `plan-marshall:extension-api/standards/build-execution.md` - Execution patterns and lifecycle
- `standards/python-impl.md` - Python/pyprojectx execution details
