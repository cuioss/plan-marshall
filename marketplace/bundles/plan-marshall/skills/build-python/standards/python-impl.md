# Python Implementation Standards

Python/pyprojectx-specific standards for build execution, output parsing, and issue handling. For shared standards (timeouts, warnings, log files), see `extension-api/standards/build-systems-common.md`. For canonical commands, see `build-api-reference.md`.

---

## Build Command Construction

### Base Command

All Python builds use the pyprojectx wrapper from the project root:

```bash
./pw {command} {args}
```

Omit `{module}` to run against all modules.

---

## Module Targeting

### Single Module Build

Use the module name as the second argument:

```bash
./pw module-tests core           # Test specific module
./pw coverage core               # Coverage for specific module
./pw quality-gate core           # Quality checks for specific module
```

### All Modules

Omit the module argument to target all:

```bash
./pw verify                      # Full verification (all modules)
./pw module-tests                # Test all modules
./pw quality-gate                # Quality checks for all modules
```

---

## Quality Configuration

### Quality Commands

| Command | Purpose |
|---------|---------|
| `quality-gate` | Run mypy + ruff without tests |
| `compile` | Type-checking only (mypy) |
| `verify` | Full verification (quality-gate + tests) |
| `module-tests {module}` | Run tests for a specific module |
| `coverage {module}` | Tests with coverage collection |

### Tool Configuration

Quality tools are configured in `pyproject.toml`:

```toml
[tool.mypy]
strict = true

[tool.ruff]
line-length = 120

[tool.pytest.ini_options]
testpaths = ["test"]
```

---

## CI/CD Standards

```bash
export CI=true
export PYTHONDONTWRITEBYTECODE=1
```

Cache `.pyprojectx/` between CI runs.

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `FileNotFoundError` for wrapper | Ensure `./pw` or `pwx` exists |
| mypy import errors | Check `[tool.mypy]` in `pyproject.toml` for `mypy_path` configuration |
| ruff configuration | Verify `[tool.ruff]` in `pyproject.toml` |
| pytest collection errors | Check for `__init__.py` in test directories |
| Timeout on first run | pyprojectx downloads tools on first invocation |

### Diagnostic Commands

```bash
python3 --version
./pw --version
./pw mypy --version
./pw ruff --version
./pw pytest --version
```

See SKILL.md for coverage report paths and parser details. See `build-api-reference.md` for shared build documentation.

**Notation**: `plan-marshall:build-python:python_build`
