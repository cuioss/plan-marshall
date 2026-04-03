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
