---
name: build-python
description: Python/pyprojectx build operations — mypy type-checking, ruff linting, pytest with Cobertura coverage, and test-directory-based module discovery
user-invocable: false
implements: plan-marshall:extension-api/standards/ext-point-build
---

# Build Python

Python build execution via pyprojectx (`./pw` wrapper) with output parsing for mypy, ruff, and pytest.

## Enforcement

See `build-api-reference.md` § Enforcement for shared rules.
All commands use `python3 .plan/execute-script.py plan-marshall:build-python:python_build {command} {args}`.

**Note on script naming**: Named `python_build.py` (not `python.py`) to avoid shadowing Python's module namespace. Notation: `plan-marshall:build-python:python_build`.

## Scripts

| Script | Purpose |
|--------|---------|
| `python_build.py` | CLI dispatcher |
| `_python_execute.py` | Execution config via factory (uses shared `default_command_key_fn`, `default_build_command_fn`) |
| `_python_cmd_parse.py` | Multi-parser registry for mypy, ruff, pytest |
| `_python_cmd_discover.py` | Module discovery via test directory detection |

## Subcommands

Supports: **run**, **parse**, **coverage-report**, **check-warnings**, **discover**.
See `build-api-reference.md` for the full subcommand API and availability matrix.

### Python-Specific Behavior

- **run**: `--command-args` takes pyprojectx commands, e.g., `"verify"`, `"module-tests core"`, `"quality-gate"`. Result includes `wrapper` field showing resolved executable path
- **coverage-report**: Searches `coverage.xml`, `htmlcov/coverage.xml`. Generate with `pytest --cov --cov-report=xml`
- **discover**: Modules are directories containing `test/` or `tests/` subdirectories. Metadata from `pyproject.toml` via `tomllib`. Excludes `.venv`, `venv`, `.tox`, cache directories

## Parser Architecture

Unlike Maven/Gradle (single parser) and npm (single-match registry), Python runs **all matching parsers** and combines results. This handles pyprojectx `verify` which runs mypy + ruff + pytest in sequence, producing mixed output in a single log file.

## Module Discovery

Directories with `test/` or `tests/` subdirectories. Searches one level deep from project root, plus root itself.

## References

- `build-api-reference.md` — Shared subcommand API, error categories, issue routing, wrapper detection
- `build-execution.md` — Execution contract and lifecycle
- `standards/python-impl.md` — Python/pyprojectx execution details
