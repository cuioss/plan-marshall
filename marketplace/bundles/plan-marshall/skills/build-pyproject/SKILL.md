---
name: build-pyproject
description: Python/pyprojectx build operations — mypy type-checking, ruff linting, pytest with Cobertura coverage, and test-directory-based module discovery
user-invocable: false
mode: script-executor
implements: plan-marshall:extension-api/standards/ext-point-build
---

# Build Pyproject

Python build execution via pyprojectx (`./pw` wrapper) with output parsing for mypy, ruff, and pytest. Wrapper resolution prefers the project wrapper (`pw`) and falls back to the system `pwx` when no checked-in wrapper is present. See [`build-api-reference.md`](../extension-api/standards/build-api-reference.md) § Wrapper Detection for the detection table.

## Enforcement

See `build-api-reference.md` § Enforcement for shared rules.
All commands use `python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build {command} {args}`.

## Scripts

| Script | Purpose |
|--------|---------|
| `pyproject_build.py` | CLI dispatcher |
| `_pyproject_execute.py` | Execution config via factory (uses shared `default_command_key_fn`, `default_build_command_fn`) |
| `_pyproject_cmd_parse.py` | Multi-parser registry for mypy, ruff, pytest |
| `_pyproject_cmd_discover.py` | Module discovery via test directory detection |

## Subcommands

Supports: **run**, **parse**, **coverage-report**, **check-warnings**, **discover**, **resolve-test-scope**.
See `build-api-reference.md` for the full subcommand API and availability matrix.

### Pyproject-Specific Behavior

- **run**: `--command-args` takes pyprojectx commands, e.g., `"verify"`, `"module-tests core"`, `"quality-gate"`. Result includes `wrapper` field showing resolved executable path
- **coverage-report**: Searches `coverage.xml`, `htmlcov/coverage.xml`. Generate with `pytest --cov --cov-report=xml`
- **discover**: Modules are directories containing `test/` or `tests/` subdirectories. Metadata from `pyproject.toml` via `tomllib`. Excludes `.venv`, `venv`, `.tox`, cache directories
- **resolve-test-scope**: Resolves the scoped module set the plan's live footprint would cover and whether a scoped run could diverge from a whole-tree run. The derivation mirrors the bundle-derivation in [`phase-6-finalize/standards/pre-push-quality-gate.md`](../phase-6-finalize/standards/pre-push-quality-gate.md) (fnmatch each footprint entry against the `build.map` globs; `marketplace/bundles/{bundle}/…` → segment 2, `test/{bundle}/…` → segment 1) via the pure `_test_scope_divergence.resolve_test_scope` helper. `divergence_possible` is true when the footprint spans more than one module or touches shared cross-module test infrastructure (`script-shared/scripts/build/…`, `test/**/conftest.py`); a single isolated module yields `recommended_target` = that module (scoped-equals-whole-tree by equivalence). Consumed by the phase-6-finalize whole-tree module-tests divergence gate, mirroring the escalate-only-on-trigger discipline of the `finalize-step-plugin-doctor` reference behavior (PLAN-02)

### Producer-Side Finding Storage (`run --plan-id`)

When `run` is invoked with `--plan-id <P>`, every parsed issue from a failed build is auto-stored via the producer path (always-on — there is no separate `--store-findings` flag). Without `--plan-id`, the build parses and formats only (no finding storage). The pyproject-specific issue→finding-type routing is:

| Parsed `category` (Issue) | Finding type |
|---------------------------|--------------|
| `test_failure`, `test_*` | `test-failure` |
| categories containing `lint` or `style` (e.g., `lint_error`) | `lint-issue` |
| everything else (compile, type_error, dependency, plugin) | `build-error` |

Severity is mapped from `Issue.severity`: `error` → `error`, `warning` → `warning`. The finding's `module` carries the build tool name (`python`), `rule` carries the original parser category, and `detail` carries the full message plus any stack trace.

> For the producer→store→consumer→gate flow including the producer-mismatch fidelity contract, see [`ref-workflow-architecture/standards/findings-pipeline.md`](../ref-workflow-architecture/standards/findings-pipeline.md). This SKILL.md owns the per-tool issue→finding-type routing only.

## Parser Architecture

Unlike Maven/Gradle (single parser) and npm (single-match registry), Python runs **all matching parsers** and combines results. This handles pyprojectx `verify` which runs mypy + ruff + pytest in sequence, producing mixed output in a single log file.

## Module Discovery

Directories with `test/` or `tests/` subdirectories. Searches one level deep from project root, plus root itself.

## Canonical invocations

The canonical argparse surface for `pyproject_build.py`. The plugin-doctor analyzer (`_analyze_manage_invocation.py`) reads this section as source-of-truth for the `manage-invocation-invalid` and `missing-canonical-block` rules. Consuming docs xref this section by name instead of restating the command inline. See [`pm-plugin-development:plugin-script-architecture` cross-skill-integration.md](../../../pm-plugin-development/skills/plugin-script-architecture/standards/cross-skill-integration.md) § "Script invocation in documentation".

### run

```bash
python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run \
  --command-args COMMAND_ARGS \
  [--timeout SECONDS] [--mode {actionable,structured,errors}] [--format {toon,json}] \
  (--project-dir PROJECT_DIR | --plan-id PLAN_ID)
```

`--project-dir` and `--plan-id` are mutually exclusive.

**Two independent budgets — distinct, non-confusable failure envelopes.** `run` is governed by two separate ceilings that do NOT extend one another:

1. **`--timeout` (build-EXECUTION deadline).** `--timeout` — falling back to the config default when omitted — is the subprocess execution deadline. An overrun surfaces as `status: timeout`.
2. **`--plan-id` slot (build-QUEUE concurrency limiter).** When `--plan-id` is set, the build is additionally enrolled in the `manage-locks` build-queue concurrency limiter. Its slot-acquisition ceiling is a separate `manage-locks` knob (`build.queue.max_retries × 60s`, ~600s default) that `--timeout` does NOT extend. Under sustained saturation past that retry ceiling the build returns `status: error` / `error: queue_saturated` (exit 1) WITHOUT ever running the build — this envelope is DISTINGUISHABLE from a `status: timeout` execution timeout, never confusable with it. A `status: timeout` under `--plan-id` is therefore always an execution-deadline overrun, never a slot-acquisition timeout.

**Escape hatch.** The `--project-dir` path (mutually exclusive with `--plan-id`) makes the queue slot a NO-OP passthrough, bypassing the concurrency limiter entirely. On a contended machine where a saturated queue is starving a build, switching from `--plan-id` to `--project-dir` is the documented way to bypass the queue and let the build run.

### parse

```bash
python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build parse \
  --log LOG \
  [--mode {default,errors,structured}] [--format {toon,json}] \
  [--failures-detail] [--test TEST] \
  (--project-dir PROJECT_DIR | --plan-id PLAN_ID)
```

`--failures-detail` slices the deduped per-signature traceback detail for ALL failing tests; `--test TEST` slices the traceback for one named failing test. Both are additive to the standard parse surface — with neither set, `parse` behaves exactly as before.

### coverage-report

```bash
python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build coverage-report \
  [--project-path PROJECT_PATH] [--report-path REPORT_PATH] [--threshold PERCENT] \
  (--project-dir PROJECT_DIR | --plan-id PLAN_ID)
```

### check-warnings

```bash
python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build check-warnings \
  [--warnings WARNINGS] [--acceptable-warnings ACCEPTABLE_WARNINGS] \
  (--project-dir PROJECT_DIR | --plan-id PLAN_ID)
```

### discover

```bash
python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build discover \
  [--root ROOT] [--format {toon,json}]
```

### resolve-test-scope

```bash
python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build resolve-test-scope \
  (--project-dir PROJECT_DIR | --plan-id PLAN_ID)
```

`--project-dir` and `--plan-id` are mutually exclusive; `--plan-id` is required to resolve the live footprint (the `--project-dir`-only escape hatch cannot resolve a plan footprint on its own). Prints TOON: `scoped_modules[]`, `divergence_possible`, `recommended_target`, `whole_tree_available`. Consumed by the phase-6-finalize whole-tree module-tests divergence gate ([`phase-6-finalize/standards/pre-push-quality-gate.md`](../phase-6-finalize/standards/pre-push-quality-gate.md)).

### run-config-key

```bash
python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run-config-key \
  --command-args COMMAND_ARGS [--format {toon,json}]
```

## References

- `build-api-reference.md` — Shared subcommand API, error categories, issue routing, wrapper detection
- `build-execution.md` — Execution contract and lifecycle
- `standards/pyproject-impl.md` — Python/pyprojectx execution details
