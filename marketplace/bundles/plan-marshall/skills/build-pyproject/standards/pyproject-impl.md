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

Three independent bounds constrain a pyprojectx test run, and the pyproject outer floor is squeezed between two of them. The ordering is a hard **two-sided** invariant:

| Bound | Where | Value | Role |
|-------|-------|-------|------|
| Harness Bash ceiling | `tools-file-ops/scripts/constants.HARNESS_BASH_CEILING_SECONDS` | 600 s | Hard cap on any `timeout` a Bash tool call may carry — the buffered stamp must fit under it to be passable at all |
| Outer wrapper floor | `_pyproject_execute.PYTEST_OUTER_FLOOR_SECONDS` (fed to `ExecuteConfig.min_timeout`) | 330 s | Floor under the adaptive/learned timeout applied to the whole `./pw` subprocess |
| Inner backstop | `pyproject.toml` `[tool.pytest.ini_options]` `timeout` | 300 s | Per-test watchdog that fails the hanging test with a traceback at the hang point |

**Invariant (both halves required)**:

1. `PYTEST_OUTER_FLOOR_SECONDS` (330 s) > `[tool.pytest.ini_options]` `timeout` (300 s).
2. `PYTEST_OUTER_FLOOR_SECONDS + OUTER_TIMEOUT_BUFFER` (330 + 30 = 360 s) <= `HARNESS_BASH_CEILING_SECONDS` (600 s).

Half 1 protects attribution. The inner backstop is the diagnosable bound — it names the test that hung and prints its stack; the outer bound only kills the process. If the outer bound can expire first, the inner backstop is dead: every hang surfaces as an opaque outer kill with no attribution, which is exactly the failure the backstop exists to prevent. Because the outer value is adaptive (learned per command key, then floored), the floor is what guarantees the ordering — the learned value can only move the outer bound up, never below the floor.

Half 2 protects **passability**. `bash_timeout_seconds` is not merely a stamp: it is the number a phase-5 leaf is instructed to pass on its Bash call. A floor that pushes the buffered value past the harness ceiling makes that instruction unfollowable and, before the tier followed the measurement, forced every pyprojectx canonical to the orchestrator tier on the floor alone. Stating only half 1 is what permitted the over-provision; both halves are now load-bearing.

Changing any of the three values requires re-checking BOTH halves. Raising the inner `timeout` at or above the outer floor silently disables attribution; raising the outer floor past `ceiling − buffer` silently makes the stamped bound un-passable.

### The outer floor is declared per engine, not owned by pyproject

`PYTEST_OUTER_FLOOR_SECONDS` is pyproject's instance of a **uniform** declaration shape, not a pyproject-only mechanism. Every build engine declares its own named module-level outer floor constant and passes it as `ExecuteConfig.min_timeout`; none inherits the tool-agnostic `MIN_TIMEOUT` dataclass default silently:

| Engine | Constant | Value | What the floor protects against |
|--------|----------|-------|---------------------------------|
| pyproject | `_pyproject_execute.PYTEST_OUTER_FLOOR_SECONDS` | 330 s | The outer kill pre-empting pytest's inner per-test backstop (the invariant above) |
| maven | `_maven_execute.MAVEN_OUTER_FLOOR_SECONDS` | 300 s | A cold-repository dependency/plugin resolve being killed mid-download |
| gradle | `_gradle_execute.GRADLE_OUTER_FLOOR_SECONDS` | 300 s | A cold-daemon start-up plus configuration phase being killed before the first task runs |
| npm | `_npm_execute.NPM_OUTER_FLOOR_SECONDS` | 300 s | A cold-cache install (or an `npx` tool fetch) being killed mid-fetch |

Only pyproject's floor is set by an inner-vs-outer ordering invariant; the other three are set by cold-start cost. Every one of the four additionally satisfies the shared upper bound (`floor + OUTER_TIMEOUT_BUFFER <= HARNESS_BASH_CEILING_SECONDS`), so no engine's floor alone can make its stamped bound un-passable. The shared property is that each is *declared* rather than inherited, so the floor a run enforces is readable at the engine.

**Resolve-stamp parity.** `architecture resolve` computes its `bash_timeout_seconds` stamp from the SAME declared floor the run enforces — `max(timeout_get(command_key, DEFAULT_BUILD_TIMEOUT), config.min_timeout) + OUTER_TIMEOUT_BUFFER` — so the recommended bound can never fall below what `execute_direct_base` will measure against. One declaration, two consumers, zero re-derivation. The derived `execution_tier` does NOT follow that floored value: it follows the MEASUREMENT, with an unmeasured command failing closed to `orchestrator`. The floor's job is to keep the stamp truthful and passable, not to decide the tier. See [`manage-architecture/standards/resolve-command.md`](../../manage-architecture/standards/resolve-command.md) § Augmented Fields for the stamp contract.

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
