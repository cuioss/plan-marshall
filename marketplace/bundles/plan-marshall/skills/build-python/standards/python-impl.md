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
- **Default**: 300 seconds (5 minutes)
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
- Lines containing mypy patterns → type error parsing
- Lines containing ruff codes → lint error parsing
- Lines containing pytest markers → test failure parsing

---

## Acceptable Warnings

Warnings can be suppressed per-project via `.plan/acceptable-warnings-python.txt`. One pattern per line. Lines starting with `#` are comments. The file is loaded from `{project_dir}/.plan/`.

---

## Coverage Report Paths

The coverage report parser searches these paths in order:

| Path | Format |
|------|--------|
| `coverage.xml` | Cobertura XML |
| `htmlcov/coverage.xml` | Cobertura XML (alternate location) |

Generate with: `pytest --cov --cov-report=xml`

---

## Log File Handling

Build output is captured to timestamped log files:

```
.plan/temp/build-output/default/python-{YYYY-MM-DD-HHmmss}.log
```

Scope is always `default` (Python builds don't have module-scoped log files like Maven's `-pl`).
