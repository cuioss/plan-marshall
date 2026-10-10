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

## Exit-code convention for every script call

The exit-code contract for every `python3 .plan/execute-script.py` call in this document — of EVERY notation, not only `manage-*` — is stated once in [`tools-script-executor/standards/exit-code-convention.md`](../tools-script-executor/standards/exit-code-convention.md); it is not restated here.

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

- **run**: `--command-args` takes pyprojectx commands, e.g., `"verify"`, `"module-tests core"`, `"quality-gate"`. Result includes `wrapper` field showing resolved executable path. Also accepts `--env` and `--working-dir` (see [`build-api-reference.md`](../extension-api/standards/build-api-reference.md) § run for the parameter definitions). A build carrying either flag is never daemon-routable — it falls back in-process under `--execution-mode auto` and fails loud under `--execution-mode daemon`. **Fast targeted signal** (sanctioned alternative to direct `.venv/bin/pytest -k`): `run --command-args "module-tests {test_dir} [--no-parallel] [--filter {expr}]"` forwards the module scope and the pytest `-k` expression through the wrapper, keeping basetemp isolation, xdist grouping, and change-ledger attribution intact. Constraint: `--command-args` splits on whitespace (no shell quoting), so only single-token `--filter` expressions travel this path; an empty `--filter` is refused, never silently ignored
- **coverage-report**: Searches `coverage.xml`, `htmlcov/coverage.xml`. Generate with `pytest --cov --cov-report=xml`
- **discover**: Modules are directories containing `test/` or `tests/` subdirectories. Metadata from `pyproject.toml` via `tomllib` — PEP 621 `[project]` first, then `[tool.poetry]` in the same file — and from `setup.cfg` via `configparser` when neither supplies a name. Excludes `.venv`, `venv`, `.tox`, cache directories
- **resolve-test-scope**: Resolves the scoped module set a footprint would cover and whether a scoped run could diverge from a whole-tree run. The footprint source is either the whole-plan live footprint (default, resolved from `--plan-id`) or a **task-scoped footprint** supplied directly via `--changed-paths` (comma-separated; the files a single task's change touched) — the latter supersedes the former when present. Both feed the same pure `_test_scope_divergence.resolve_test_scope` helper; only the footprint list differs. The handler enumerates the **registered targets** through `_test_scope_targets.resolve_registered_targets` — the single derivation of that set — and passes them in as the helper's third argument, so the helper itself stays free of I/O. A registered target is either a bundle (the existing `marketplace_bundles.find_bundles()` + `extract_bundle_name()` walk) or a **test tree holding tests**: a top-level directory under a test root that holds at least one `test_*.py` at any depth and whose name does not start with `_`. A non-bundle test tree is therefore a **named target** — a footprint under `test/{name}/…` resolves to `{name}` in `scoped_modules` even when no `marketplace/bundles/{name}` exists, and the path is not unresolved. ⛔ **Named is not recommended.** Only a **bundle module** — enumerated through `_test_scope_targets.resolve_bundle_modules` and passed in beside the registered targets — is ever a `recommended_target`: `architecture resolve --command module-tests --module {name}` answers `Module not found` for a test tree that is no bundle, so a consumer handed such a name could not run it. A footprint that names a non-bundle test tree, or reaches a module through the declared source-to-test mapping below, lists that module in `named_only_modules` and reports `divergence_possible: true` with `recommended_target: None` — **the whole tree is required**. A name in `named_only_modules` MUST NOT be passed to `architecture resolve --module`. The derivation mirrors the bundle-derivation in [`phase-6-finalize/standards/pre-push-quality-gate.md`](../phase-6-finalize/standards/pre-push-quality-gate.md) (`marketplace/bundles/{bundle}/…` → segment 2, `test/{bundle}/…` → segment 1); a derived name that is not a registered target resolves to **no** module rather than being returned verbatim. Source that lives outside both of those shapes is resolved through the **declared source-to-test mapping**, the `SOURCE_TO_TEST_TARGET` constant in `script-shared/scripts/build/_test_scope_divergence.py` — the one place the mapping is stated, matched by longest prefix and subject to the same registered-target guard; a source path the constant does not cover stays unresolved. An entry names *a* tree holding tests for that source, not the only one, which is why a module reached through it is named only. `divergence_possible` is true when the footprint spans more than one module, touches shared cross-module test infrastructure (`script-shared/scripts/build/…`, `test/_shared/**`, `test/**/conftest.py`), any footprint entry mapped to no registered target, **or** `named_only_modules` is non-empty; a single isolated **bundle** module, every changed path of it owned by a path segment, with nothing unresolved yields `recommended_target` = that module (scoped-equals-whole-tree by equivalence). A **non-empty** footprint that resolves to no module fails closed — `divergence_possible: true`, `recommended_target: None`, and every such path enumerated in `unresolved_paths` (the ADR-014 disclosure) — so a docs-only change routes to a whole-tree run rather than to "no pytest target". The **empty** footprint is the one legitimate benign verdict and still yields `divergence_possible: false` with `recommended_target: None`, so a consumer MUST check `recommended_target` is non-null before interpolating it into a command. A caller that cannot enumerate registered targets reports `modules_resolvable: false` and fails toward the whole tree the same way; a caller that cannot enumerate the bundle modules establishes no name as one, so every scoped module is named only and the verdict is again the whole tree. Beside the module-level answer the verb returns two **narrow-unit** lists and their module for a footprint that resolves to exactly one **bundle** module: `narrow_units` names the `module-tests` targets narrower than the module that the change points at — `{bundle}/{skill}` for a path inside `marketplace/bundles/{bundle}/skills/{skill}/…` when that test directory exists, and a changed `test_*.py` as its own path relative to the test root when that file exists on disk — and `narrow_units_unresolved` names every changed path that contributed none (a skill with no test directory, a document, a helper, a **deleted** test file — a footprint lists a deleted file exactly as it lists an edited one, and a unit no run can collect is not offered). `narrow_unit_module` names the bundle module every entry of `narrow_units` belongs to; it is non-null **exactly when `narrow_units` is non-empty**, and it — not `recommended_target`, which is null whenever the whole tree is warranted while narrow units are still offered — is the module a narrow unit is resolved against. The lists are **advisory for a step**: a narrow unit is a faster first signal a step may run inline, and it never replaces `recommended_target` or the whole-tree verdict, both of which are computed exactly as without them. A changed path named in `narrow_units_unresolved` is not covered by any narrow run. A narrow unit is a **`module-tests` target only**. Both lists are empty and `narrow_unit_module` is null for a footprint spanning more than one module, owning none, or resolving to a single module that is no bundle, and on the fail-toward-whole-tree branch (`footprint_resolvable: false` or `modules_resolvable: false`). The whole-plan mode is consumed by the phase-6-finalize whole-tree module-tests divergence gate (mirroring the escalate-only-on-trigger discipline of the `finalize-step-plugin-doctor` reference behavior, PLAN-02); the task-scoped `--changed-paths` mode is consumed by the `execute-task` implementation profile per-task breakable-test gate

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

## Module-edge derivation (Axis-C derivation resolver)

`extension.py`'s `BuildExtension` subclasses **both** `BuildExtensionBase` (Axis-B, the file-to-build map) and `DerivationResolverBase` (Axis-C, module-edge derivation), so this skill also answers *which modules depend on which* for the `graph` / `path` / `neighbors` / `impact` query family.

The resolver id is `pyproject`. Its derivation is the **distribution-name join**: a Python project publishes no `groupId:artifactId` coordinate, so the Maven join can never match one — what it publishes is its declared distribution name — PEP 621 `[project] name`, else `[tool.poetry] name`, else `setup.cfg [metadata] name` — carried on `metadata.name`. An edge exists wherever one module's `name:scope` dependency string names another module's published distribution, compared in PEP 503 normalised form so the `-`/`_`/`.`/case variants of one name resolve to the same module. Both scopes contribute: a `dev` extra is a real edge, because changing the depended-upon module can break the dependent's tests.

Three behaviours are contract obligations rather than implementation detail:

- **The join is scoped to modules this build system discovered.** Unlike a coordinate, a bare distribution name is a key shape every ecosystem uses, so an unscoped join would claim provenance for another ecosystem's edges and could fabricate an edge between a Python distribution and a same-named package elsewhere.
- **There is no fallback to the module's own name.** A directory that declares a distribution name in none of the three descriptor forms publishes no distribution, so nothing can depend on it; it stays a valid edge *source* but is never a *target*. Falling back to the directory name would invent a key the ecosystem never published. ⚠ A `setup.py`-only module is in this position for a different reason — `setup.py` is executable Python and is deliberately not parsed. A module whose `pyproject.toml` does not parse logs a WARNING naming the file and publishes nothing *from that file*, but the `setup.cfg` fallback still applies, so a module carrying both may still publish a name.
- **An ambiguous distribution name yields no edge and a reported collision**, and the enriched overlay is not consulted — the declaration-wins ruling is core's, applied ahead of the resolver call.

This resolver is distinct from `pm-dev-python`'s `python` resolver, and both are wanted: that one joins AST-parsed imports (language knowledge), this one joins declared distribution dependencies (build-system knowledge).

The contract itself — the four faces, the N-resolver union semantics, the anti-vacuity provenance property, and the generic ambiguous-identity-key obligation — is owned by [`../extension-api/standards/ext-point-derivation-resolver.md`](../extension-api/standards/ext-point-derivation-resolver.md) and is deliberately not restated here.

## Canonical invocations

The canonical argparse surface for `pyproject_build.py`. The plugin-doctor `missing-canonical-block` rule checks that this section is PRESENT, matching its heading only — the body is never read; `manage-invocation-invalid` derives its accept-set from a live `--help` walk rather than from this section. Consuming docs xref this section by name instead of restating the command inline. See [`pm-plugin-development:plugin-script-architecture` cross-skill-integration.md](../../../pm-plugin-development/skills/plugin-script-architecture/standards/cross-skill-integration.md) § "Script invocation in documentation".

### run

```bash
python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run \
  --command-args COMMAND_ARGS \
  [--timeout SECONDS] [--mode {actionable,structured,errors}] [--format {toon,json}] \
  [--env ENV] [--working-dir WORKING_DIR] \
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

`--failures-detail` slices the deduped per-signature traceback detail across the whole failing population; `--test TEST` slices the detail for the records matching one name. Both are additive to the standard parse surface — with neither set, `parse` behaves exactly as before.

**The sliced population is wider than the FAILED lines.** Both flags resolve against the same record set `parse` itself reports: pytest's `FAILED` lines **unioned with** its collection- and setup-level `ERROR` lines. A run whose test modules failed to import produces no `FAILED` line at all, so reading only those would report zero failures over a demonstrably red build. Three consequences of that union are not evident from the flag names:

- **`total_failures` counts collection/setup errors as failures.** It is the size of the whole union, not of the `FAILED` slice alone. `root_causes` is that union deduped by failure signature, and `failures[]` carries one entry per root cause. `--test TEST` reports `matched` and returns the matching records **un-deduped**, matching on the exact test id, on the bare function name (class prefix and `[param]` suffix stripped), or on a suffix.
- **A record's `test` may be a FILE PATH rather than a test id.** A collection error names no test, so `test` falls back to the file whose collection failed — which is also the value `--test` must be given to select it.
- **The slice drops the `category` discriminator (known limitation).** Each `failures[]` entry projects only `test`, `file`, `line` and `detail`, so a `test_failure` record and a `test_collection_error` record are indistinguishable in slice output. The discriminator survives on every other surface: the standard `parse` rows (`data.issues[]` — reachable under `--format json` only, since the default TOON formatter's field whitelist drops `data`) and the failing `run` rows (`errors[]`) both carry `category`, and the `run --plan-id` producer path stores it as the finding's `rule` (see § Producer-Side Finding Storage above). A consumer that must separate the two populations reads one of those, not the slice.

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
  [--changed-paths CHANGED_PATHS] \
  (--project-dir PROJECT_DIR | --plan-id PLAN_ID)
```

`--project-dir` and `--plan-id` are mutually exclusive; they resolve the `build.map` globs. The footprint comes from one of two sources: `--changed-paths` (a comma-separated task-scoped footprint — the files a single task's change touched) supersedes the whole-plan footprint when present; when it is absent `--plan-id` is required to resolve the live plan footprint (the `--project-dir`-only escape hatch cannot resolve a plan footprint on its own). Prints TOON: `scoped_modules[]`, `divergence_possible`, `recommended_target`, `unresolved_paths[]`, `narrow_units[]`, `narrow_units_unresolved[]`, `named_only_modules[]`, `narrow_unit_module`, `whole_tree_available`, `footprint_resolvable`, `modules_resolvable`. A `recommended_target` is always a bundle module: a non-bundle test tree is named in `scoped_modules` and `named_only_modules` and requires the whole tree (see § Pyproject-Specific Behavior → resolve-test-scope). Every entry of `narrow_units` is a `module-tests` target only, is advisory for a step, and is resolved against `narrow_unit_module`. Consumed by the phase-6-finalize whole-tree module-tests divergence gate ([`phase-6-finalize/standards/pre-push-quality-gate.md`](../phase-6-finalize/standards/pre-push-quality-gate.md)) with the whole-plan footprint, and by the `execute-task` implementation profile per-task breakable-test gate with a task-scoped `--changed-paths` footprint.

### run-config-key

```bash
python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run-config-key \
  --command-args COMMAND_ARGS [--format {toon,json}]
```

## References

- `build-api-reference.md` — Shared subcommand API, error categories, issue routing, wrapper detection
- `build-execution.md` — Execution contract and lifecycle
- `standards/pyproject-impl.md` — Python/pyprojectx execution details
