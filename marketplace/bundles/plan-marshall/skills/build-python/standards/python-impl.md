# Python Implementation Standards

Python/pyprojectx-specific standards for build execution, output parsing, and issue handling. For shared standards (timeouts, warnings, log files), see `extension-api/standards/build-systems-common.md`.

---

## Build Command Construction

### Base Command

All Python builds use the pyprojectx wrapper from the project root:

```bash
./pw {command} {args}
```

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

## Output Parsing

### Parser Registry

Python build output is parsed using the shared `ParserRegistry` with tool-specific parsers:

| Parser | Detects | Category |
|--------|---------|----------|
| mypy | `file.py:line: error:` | `type_error` |
| ruff | `file.py:line:col: CODE` | `lint_error` |
| pytest | `FAILED file.py::test` | `test_failure` |

Since pyprojectx verify runs multiple tools in sequence (mypy + ruff + pytest), all matching parsers are applied and results are combined.

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

### Environment Configuration

```bash
CI=true ./pw verify              # CI environment
./pw module-tests core           # Specific module testing
./pw coverage core               # Coverage generation
```

---

## CI/CD Standards

```bash
export CI=true
export PYTHONDONTWRITEBYTECODE=1
```

Cache `.pyprojectx/` between CI runs.

---

## Metadata Extraction

Discovery extracts metadata from `pyproject.toml` when available:

| Field | Source |
|-------|--------|
| `name` | `[project].name` |
| `version` | `[project].version` |
| `description` | `[project].description` |
| `requires_python` | `[project].requires-python` |

Dependencies are extracted from `[project].dependencies` (runtime) and `[project].optional-dependencies.dev` (dev).

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `FileNotFoundError` for wrapper | Ensure `./pw` or `pwx` exists |
| mypy import errors | Check `[tool.mypy]` in `pyproject.toml` for `mypy_path` configuration |
| ruff configuration | Verify `[tool.ruff]` in `pyproject.toml` |
| pytest collection errors | Check for `__init__.py` in test directories |
| Timeout on first run | pyprojectx downloads tools on first invocation |

See SKILL.md for wrapper detection, issue routing, and coverage report paths. See `build-api-reference.md` for shared build documentation.

**Notation**: `plan-marshall:build-python:python_build`
