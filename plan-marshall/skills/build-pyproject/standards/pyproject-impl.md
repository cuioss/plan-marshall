# Pyproject Implementation Standards

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
| `compile` | Type-check production sources only (mypy) |
| `test-compile` | Type-check the `test/` tree only (mypy) |
| `verify` | Full verification: `quality-gate` + `test-compile` + `module-tests`, in that order |
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

## Timeout bound ordering

Two independent timeouts bound a pyprojectx test run, and their ordering is a hard invariant:

| Bound | Where | Value | Role |
|-------|-------|-------|------|
| Outer wrapper floor | `_pyproject_execute.PYTEST_OUTER_FLOOR_SECONDS` (fed to `ExecuteConfig.min_timeout`) | 600 s | Floor under the adaptive/learned timeout applied to the whole `./pw` subprocess |
| Inner backstop | `pyproject.toml` `[tool.pytest.ini_options]` `timeout` | 300 s | Per-test watchdog that fails the hanging test with a traceback at the hang point |

**Invariant**: `PYTEST_OUTER_FLOOR_SECONDS` (600 s) > `[tool.pytest.ini_options]` `timeout` (300 s).

The inner backstop is the diagnosable one — it names the test that hung and prints its stack. The outer bound only kills the process. If the outer bound can expire first, the inner backstop is dead: every hang surfaces as an opaque outer kill with no attribution, which is exactly the failure the backstop exists to prevent. Because the outer value is adaptive (learned per command key, then floored), the floor is what guarantees the ordering — the learned value can only move the outer bound up, never below the floor.

Changing either value requires re-checking the inequality. Raising the inner `timeout` at or above the outer floor silently disables attribution.

---

## Verification-Target Trust

A verification target that CI does not run gates nothing — it can be latently broken tree-wide for an extended period, and the breakage lands on whichever unrelated plan first happens to invoke it directly. `verify` now wires `test-compile` in as a mandatory stage precisely to close this gap; the same discipline applies to any future lane that is not yet folded into `verify`:

- **Treat a non-gated target as un-trusted-green.** Before relying on any lane that `verify` does not run for a plan's own verification, confirm it currently passes tree-wide on a clean checkout — do not assume its green state.
- **Validate against a CLEAN mypy cache before trusting a local pass when wiring a new mypy-based gate.** mypy's incremental cache narrows what gets re-checked; a local run that finishes in a couple of seconds over hundreds of files is a red flag that the cache, not the code, produced the green. Delete/ignore `.mypy_cache` (or run in a clean checkout) so the local run re-checks the same file set CI will before trusting it as evidence the new gate is safe to wire in.
- **For import resolution that diverges by environment (e.g. `.claude`-local scripts resolving `import-untyped` locally but `import-not-found` in CI), use a `[tool.mypy]` `exclude` entry for the divergent directory, not a per-code `# type: ignore`.** No single ignore code is valid in both environments simultaneously — mypy flags a per-code ignore as unused in whichever environment does not raise that code.

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

**Notation**: `plan-marshall:build-pyproject:pyproject_build`
