---
name: build-python
description: Python/pyprojectx build operations with execution, parsing, and coverage analysis
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
- Always analyze the result TOON: check `status` for success/error/timeout, review `errors` for failures

## Scripts Overview

| Script | Type | Purpose |
|--------|------|---------|
| `python_build.py` | CLI | pyprojectx operations dispatcher (includes coverage + warning config) |
| `_python_execute.py` | Library | Execution config via factory pattern |
| `_python_cmd_parse.py` | Library | Log parsing for mypy, ruff, pytest |

## Unified API

All build skills share the same subcommand structure. Python supports the common subcommands:

| Subcommand | Purpose |
|------------|---------|
| `run` | Execute build and auto-parse on failure (primary API) |
| `parse` | Parse pyprojectx build output from log file |
| `coverage-report` | Parse coverage.py XML report |
| `check-warnings` | Categorize build warnings against acceptable patterns |

**Not available**: `search-markers` (OpenRewrite is Java-specific, not applicable to Python projects).

### run (Primary API)

```bash
python3 .plan/execute-script.py plan-marshall:build-python:python_build run \
    --command-args "<canonical-command>" \
    [--format <toon|json>] \
    [--mode <mode>] \
    [--timeout <seconds>]
```

**Parameters**:
- `--command-args` - Canonical pyprojectx command (e.g., `"verify"`, `"module-tests core"`, `"quality-gate"`) (required)
- `--format` - Output format: toon (default) or json
- `--mode` - Output mode: actionable (default), structured, errors
- `--timeout` - Timeout in seconds (default: 300, adaptive via run-config, min floor: 60s)

**Output Format (TOON)**:

Success:
```
status	success
exit_code	0
duration_seconds	45
log_file	.plan/temp/build-output/default/python-2026-01-04-143022.log
command	./pw verify
wrapper	./pw
```

Build Failed:
```
status	error
exit_code	1
duration_seconds	23
log_file	.plan/temp/build-output/default/python-2026-01-04-143022.log
command	./pw module-tests core
wrapper	./pw
error	build_failed

errors[2]{file,line,message,category}:
src/core/utils.py    42    error: Incompatible return value type    type_error
src/core/service.py  15    F401 'os' imported but unused            lint_error

tests:
  passed: 40
  failed: 2
  skipped: 1
```

### parse

```bash
python3 .plan/execute-script.py plan-marshall:build-python:python_build parse \
    --log <path> [--mode <mode>]
```

**Parameters**:
- `--log` - Path to build log file (required)
- `--mode` - Output mode: default, errors, structured (default)

### coverage-report

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

**Output Format (TOON)**:

```
status	success
passed	true
threshold	80
message	"Coverage meets threshold: 85.2% line, 78.3% branch"

overall:
  line	85.2
  branch	78.3
  instruction	81.5
  method	87.1
```

### check-warnings

```bash
python3 .plan/execute-script.py plan-marshall:build-python:python_build check-warnings \
    --warnings <json> [--acceptable-warnings <json>]
```

**Parameters**:
- `--warnings` - JSON array of warnings
- `--acceptable-warnings` - JSON object with acceptable patterns

## Wrapper Detection

```
Python: ./pw > pwx (on PATH)
```

Unlike Maven/Gradle which fall back to system commands, Python raises `FileNotFoundError` if no pyprojectx wrapper is found.

## Error Categories

| Category | Description |
|----------|-------------|
| `type_error` | mypy type errors |
| `lint_error` | ruff violations |
| `test_failure` | pytest test failures |
| `import_error` | Module import errors |

## Module Discovery

Python module discovery uses the pyprojectx project structure. Modules are directories containing test subdirectories matching the `test/` or `tests/` pattern.

### Command Generation

Discovery generates canonical commands per module:

| Canonical | pyprojectx Command |
|-----------|-------------------|
| `verify` | `verify {module}` |
| `quality-gate` | `quality-gate {module}` |
| `compile` | `compile {module}` |
| `module-tests` | `module-tests {module}` |
| `coverage` | `coverage {module}` |
| `clean` | `clean` |

Omit `{module}` to run against all modules.

## References

- `plan-marshall:extension-api` - Extension API contract
- `plan-marshall:extension-api/standards/build-execution.md` - Execution patterns and lifecycle
- `standards/python-impl.md` - Python/pyprojectx execution details
