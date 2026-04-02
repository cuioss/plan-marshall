# Python Implementation Standards

Standards for Python/pyprojectx build execution, output parsing, and issue handling.

---

## Build Command Construction

### Base Command

All Python builds use the pyprojectx wrapper from the project root:

```bash
./pw {command} {args}
```

### Wrapper Detection

Detection order (platform-aware):
- Unix: `./pw` > `pwx` (on PATH)
- Windows: `pw.bat` > `pwx` (on PATH)

If no wrapper is found, a `FileNotFoundError` is raised (unlike Maven/Gradle which fall back to system commands).

### Canonical Commands

| Command | Purpose |
|---------|---------|
| `compile {module}` | Type-check and lint without running tests |
| `test-compile {module}` | Compile tests only |
| `module-tests {module}` | Run module test suite |
| `quality-gate {module}` | Run quality checks (mypy + ruff) |
| `coverage {module}` | Run tests with coverage collection |
| `verify {module}` | Full verification (quality-gate + tests) |
| `clean` | Remove build artifacts |

Omit `{module}` to run against all modules.

---

## Timeout Behavior

- **Unit**: Seconds
- **Default**: 300 seconds (5 minutes), same as all other build skills
- **Minimum**: 60 seconds (enforced via `MIN_TIMEOUT`)
- **Adaptive learning**: On successful completion, actual duration is recorded. On timeout failure, the cached timeout is doubled for the next run.
- **Command key format**: `python:{first_subcommand}` (e.g., `python:module_tests`)

---

## Output Parsing

### Error Categories

| Category | Source | Pattern |
|----------|--------|---------|
| `type_error` | mypy | `error:` in mypy output |
| `lint_error` | ruff | Ruff violation codes (E, W, F series) |
| `test_failure` | pytest | `FAILED` in pytest output |
| `import_error` | Python | `ModuleNotFoundError`, `ImportError` |

### Parser Detection

The parser detects the tool from output content:
- Lines containing mypy patterns -> type error parsing
- Lines containing ruff codes -> lint error parsing
- Lines containing pytest markers -> test failure parsing

---

## Acceptable Warnings

Warnings can be suppressed per-project via `.plan/acceptable-warnings-python.txt`. One pattern per line. Lines starting with `#` are comments. The file is loaded from `{project_dir}/.plan/`.

### Configuration

Acceptable warning patterns are also stored in `run-configuration.json` under the `python` section:

```json
{
    "python": {
        "acceptable_warnings": [
            "DeprecationWarning",
            "^.*experimental.*$"
        ]
    }
}
```

Patterns support substring matching and regex (patterns starting with `^`).

### Access

```
Skill: plan-marshall:manage-run-config
Workflow: Read Configuration
Field: python.acceptable_warnings
```

---

## Best Practices

### Build Command Selection

**Quality checks:**
- Use `quality-gate` for mypy + ruff without running tests
- Use `compile` for type-checking only
- Use `verify` for full verification (quality-gate + tests)

**Testing:**
- Use `module-tests {module}` for a specific module
- Use `module-tests` (no module) for all modules
- Use `coverage {module}` for tests with coverage collection

**Maintenance:**
- Use `clean` to remove build artifacts before fresh builds

### Environment Configuration

**CI environment:**
```bash
CI=true ./pw verify
```

**Specific module testing:**
```bash
./pw module-tests core
```

**Coverage generation:**
```bash
./pw coverage core
# or directly: pytest --cov --cov-report=xml
```

---

## CI/CD Standards

### Environment Variables

```bash
export CI=true
export PYTHONDONTWRITEBYTECODE=1
```

### Non-Interactive Mode

pyprojectx runs non-interactively by default. No special flags needed.

### Caching

Cache the `.pyprojectx/` directory between CI runs to avoid re-downloading tools.

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| `FileNotFoundError` for wrapper | Ensure `./pw` or `pwx` exists; Python does not fall back to system commands |
| mypy import errors | Check `mypy.ini` or `pyproject.toml` for missing `mypy_path` entries |
| ruff configuration | Verify `[tool.ruff]` section in `pyproject.toml` |
| pytest collection errors | Check for `__init__.py` in test directories if using package layout |
| Timeout on first run | pyprojectx downloads tools on first invocation; increase timeout |

### Diagnostic Commands

```bash
# Show pyprojectx version and installed tools
./pw --version

# Run mypy directly for detailed type errors
./pw mypy src/

# Run ruff with verbose output
./pw ruff check --verbose src/

# Run pytest with verbose output
./pw pytest -v
```

---

## Coverage Report Paths

The coverage report parser searches these paths in order:

| Path | Format |
|------|--------|
| `coverage.xml` | Cobertura XML |
| `htmlcov/coverage.xml` | Cobertura XML (alternate location) |

Generate with: `pytest --cov --cov-report=xml`

---

## Build Status Determination

| Exit Code | Status |
|-----------|--------|
| 0 | SUCCESS |
| != 0 | FAILURE |

Python builds always default to FAILURE status; a zero exit code is required for success.

---

## Log File Handling

Build output is captured to timestamped log files:

```
.plan/temp/build-output/default/python-{YYYY-MM-DD-HHmmss}.log
```

Scope is always `default` (Python builds don't have module-scoped log files like Maven's `-pl`).

---

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

---

## Script Reference

**Notation**: `plan-marshall:build-python:python_build`

| Subcommand | Description |
|------------|-------------|
| `run` | Execute build and auto-parse on failure (primary API) |
| `parse` | Parse pyprojectx build output and categorize issues |
| `coverage-report` | Parse coverage.py XML report |
| `check-warnings` | Categorize build warnings against acceptable patterns |

### run Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `--command-args` | Yes | - | Canonical command (e.g., "verify", "module-tests core") |
| `--format` | No | toon | Output format: toon or json |
| `--mode` | No | actionable | Output mode: actionable, structured, errors |
| `--timeout` | No | 300 | Build timeout in seconds |

**Example:**
```bash
python3 .plan/execute-script.py plan-marshall:build-python:python_build run \
    --command-args "module-tests core" --timeout 600
```

---

## Issue Routing

| Issue Type | Fix Strategy |
|------------|-------------|
| `type_error` | Fix mypy type annotations |
| `lint_error` | Fix ruff violations or configure exceptions |
| `test_failure` | Fix test assertions or implementation |
| `import_error` | Fix module imports or dependencies |
