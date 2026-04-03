---
name: build-python
description: Python/pyprojectx build operations with execution, output parsing, module discovery, and coverage analysis
user-invocable: false
---

# Build Python

Python build execution via pyprojectx (`./pw` wrapper) with output parsing for mypy, ruff, and pytest.

## Enforcement

See `plan-marshall:extension-api/standards/build-api-reference.md` § Enforcement for shared rules.

**Tool-specific constraint:**
- All commands use `python3 .plan/execute-script.py plan-marshall:build-python:python_build {command} {args}`

**Note on script naming**: The script is named `python_build.py` (not `python.py`) to avoid shadowing Python's own module namespace. This results in the notation `plan-marshall:build-python:python_build`.

## Scripts Overview

| Script | Type | Purpose |
|--------|------|---------|
| `python_build.py` | CLI | pyprojectx operations dispatcher (includes coverage + warning config) |
| `_python_execute.py` | Library | Execution config via factory pattern |
| `_python_cmd_parse.py` | Library | Log parsing for mypy, ruff, pytest |
| `_python_cmd_discover.py` | Library | Module discovery via test directory detection |

Shared infrastructure from `extension-api`: `_build_execute_factory.py`, `_build_shared.py`, `_build_parse.py`, `_build_coverage_report.py`, `_build_check_warnings.py`.

## Subcommands

Python supports all shared subcommands documented in `build-api-reference.md`:
**run**, **parse**, **coverage-report**, **check-warnings**, **discover**.

### Python-Specific Notes

**run**: The `--command-args` value contains pyprojectx commands, e.g., `"verify"`, `"module-tests core"`, `"quality-gate"`. The result TOON includes a `wrapper` field showing the resolved pyprojectx executable path.

**parse**: Does not support `no-openrewrite` mode (not applicable).

**coverage-report**: Auto-detects coverage.py Cobertura XML in these locations:
- `coverage.xml` (project root)
- `htmlcov/coverage.xml`

Generate with `pytest --cov --cov-report=xml`.

**discover**: Modules are directories containing `test/` or `tests/` subdirectories. Metadata extracted from `pyproject.toml` using `tomllib`. Searches one level deep from project root, plus root itself.

## Multi-Parser Combination

Unlike Maven/Gradle/npm which route to a single parser, Python's `parse_log()` runs **all matching parsers** and combines results. This is because pyprojectx `verify` runs multiple tools (mypy + ruff + pytest) in sequence, producing mixed output in a single log file.

## Module Discovery

Uses the pyprojectx project structure. Modules are directories containing test subdirectories matching the `test/` or `tests/` pattern.

Excludes: `.venv`, `venv`, `.tox`, `.mypy_cache`, `.ruff_cache`, `.pytest_cache`, `dist`, `egg-info`.

For error categories, issue routing, command generation tables, and wrapper detection, see `build-api-reference.md`.

## References

- `plan-marshall:extension-api/standards/build-api-reference.md` — Shared subcommand documentation, error categories, issue routing, wrapper detection
- `plan-marshall:extension-api/standards/build-execution.md` — Execution contract and lifecycle
- `standards/python-impl.md` — Python/pyprojectx execution details
