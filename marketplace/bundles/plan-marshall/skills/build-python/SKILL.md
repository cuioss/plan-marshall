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

## Quality-Gate Coverage

The `quality-gate` build target (root `build.py:cmd_quality_gate`) is the fast-feedback stage developers run on every iteration. It enforces the following marketplace-wide invariants in seconds, so violations are caught before push rather than at CI time:

| Stage | Tool / Rule | Scope |
|-------|-------------|-------|
| Type-check | `mypy` | Production sources (`marketplace/bundles`, `.claude` when present) |
| Lint | `ruff check` | `marketplace/bundles`, `test`, `.claude` (full tree) or scoped paths (module run) |
| Static-analysis invariants | `pm-plugin-development:plugin-doctor:doctor-marketplace quality-gate` | Marketplace-wide (full-tree run only) |

The plugin-doctor `quality-gate` subcommand runs only the rules whose violations are currently enforced as build-failing invariants by the pytest suite (real marketplace must produce zero findings):

- `scan_argparse_safety` — every `argparse.ArgumentParser(...)` and `subparsers.add_parser(...)` call must specify `allow_abbrev=False`. Prevents prefix-abbreviation matching from silently accepting truncated flags.
- `validate_extension_contracts` — extension-point implementations must declare the required contract sections (severity guidelines, acceptable-to-accept lists, etc.) per `plan-marshall:extension-api`.
- `analyze_argument_naming` — notation/subcommand/flag/canonical-forms cluster. Gated by `PM_ARGUMENT_NAMING_ENABLED`; emits nothing when gated off.

Module-scoped quality-gate runs (`./pw quality-gate <module>`) skip the marketplace-wide plugin-doctor sweep because they target a single bundle.

**Coverage scope**: `quality-gate` does NOT run pytest tests. Invariants enforced by pytest fixtures (helper-classification rules, fixture-driven detection tests, integration-test contracts) still require `module-tests` or `verify`. New plugin-doctor static-analysis rules are picked up automatically once their `scan_*` / `validate_*` entry point is wired into `cmd_quality_gate` in `doctor-marketplace.py`; no per-rule registration in `build.py` is needed.

## Parser Architecture

Unlike Maven/Gradle (single parser) and npm (single-match registry), Python runs **all matching parsers** and combines results. This handles pyprojectx `verify` which runs mypy + ruff + pytest in sequence, producing mixed output in a single log file.

## Module Discovery

Directories with `test/` or `tests/` subdirectories. Searches one level deep from project root, plus root itself.

## References

- `build-api-reference.md` — Shared subcommand API, error categories, issue routing, wrapper detection
- `build-execution.md` — Execution contract and lifecycle
- `standards/python-impl.md` — Python/pyprojectx execution details
