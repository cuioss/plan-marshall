# `architecture resolve` — Augmented TOON Contract

`architecture resolve --command COMMAND [--module MODULE]` returns the executable form of a project-architecture command. For Bucket B build notations (Maven / Gradle / npm / pyprojectx builds invoked via `python3 .plan/execute-script.py plan-marshall:build-{tool}:{tool} run --command-args "<args>"`), the resolve TOON is augmented with four additional fields so the calling LLM can apply the correct Bash-tool timeout and routing without re-implementing the lookup.

This document is the authoritative source for the augmented fields. The base resolve invocation, options, error contract, and the un-augmented TOON shape are documented in [`client-api.md`](client-api.md) § `resolve`.

## Augmented Fields

When the resolved `executable` matches the Bucket B build shape, the result carries these four fields in addition to the base `status`, `module`, `command`, `executable`, `resolution_level`, and (when authored) `mutating` (see [Authored `mutating` signal](#authored-mutating-signal)):

| Field | Type | Description |
|-------|------|-------------|
| `bash_timeout_seconds` | int | Recommended Bash-tool timeout in seconds. Computed as `max(timeout_get(command_key, DEFAULT_BUILD_TIMEOUT), config.min_timeout) + OUTER_TIMEOUT_BUFFER` — identical arithmetic to `cmd_run`, **including the engine's declared floor**. `config.min_timeout` is the floor the engine declares on its own `ExecuteConfig`: `MAVEN_OUTER_FLOOR_SECONDS` / `GRADLE_OUTER_FLOOR_SECONDS` / `NPM_OUTER_FLOOR_SECONDS` = `300`, `PYTEST_OUTER_FLOOR_SECONDS` = `330`. The clamp is what makes the stamp truthful: without it the stamp can report a bound strictly below what the run will consume. Every engine floor is chosen so the buffered stamp stays at or below the harness ceiling, i.e. the stamped bound is always passable on a Bash call. |
| `exceeds_bash_ceiling` | bool | `bash_timeout_seconds > HARNESS_BASH_CEILING_SECONDS` (600). That constant is declared once in `tools-file-ops/scripts/constants.py`; the Bash tool's `timeout` parameter is capped at 600s (10 minutes) by the host platform, and values above the ceiling cannot be invoked synchronously from a sub-agent. The flag keeps this literal ceiling meaning and nothing more — it is coupled to `execution_tier` on every branch **except** the unmeasured fail-closed branch, where the tier is `orchestrator` while this flag is `false`. That single decoupling is deliberate and documented, not an inconsistency. |
| `execution_tier` | enum | `"per_task"` **only when the command key has actually been measured AND `exceeds_bash_ceiling` is false**; `"orchestrator"` otherwise. Drives the manifest composer's per-command routing decision (per-task verification vs `phase_5.verification_steps`) and the caller's run-inline-vs-hand-back decision. **The tier follows the MEASUREMENT, never the floor** — the floor bounds the stamp, it does not decide the tier. An UNMEASURED command fails closed to `orchestrator` uniformly across all four engines, so a slow first run is never made runnable in-leaf before any measurement of it exists. |
| `hint` | string | Short pinned recognition phrase, selected from the `(execution_tier, exceeds_bash_ceiling)` **pair**. See [Hint Strings](#hint-strings) below. |

The four fields are emitted **as a unit** — either all four are present (Bucket B build executable, resolvable timeout) or all four are omitted (non-build executable, or the build skill could not be loaded). Consumers detect their absence and fall back to today's behaviour.

**All four fields are point-in-time measurements, not durable facts.** `bash_timeout_seconds` reads the adaptive learned duration (see [Threshold Rationale](#threshold-rationale--600)), which every run of the command updates, so `exceeds_bash_ceiling` / `execution_tier` / `hint` all move with it — a ceiling-adjacent command's tier flips in ordinary operation. A consumer that must ROUTE on the tier MUST resolve it at the moment it acts, never from a value persisted earlier. This is why `manage-execution-manifest`'s `phase_5.step_execution_tier` stamp is advisory and `phase-5-execute` re-resolves the tier live before running each verification step.

## Hint Strings

The `hint` field is a recognition token for the LLM, not human prose. There are **three** pinned public tokens, and consumers match on them exactly. The token is selected from the `(execution_tier, exceeds_bash_ceiling)` **pair** — not from `exceeds_bash_ceiling` alone, because the unmeasured fail-closed branch decouples the two and selecting on either component by itself would leave that state carrying a string that contradicts its own tier:

| `exceeds_bash_ceiling` | measured? | `execution_tier` | `hint` value |
|---|---|---|---|
| `true` | either | `orchestrator` | `"Exceeds Bash ceiling; orchestrator-tier only"` |
| `false` | yes | `per_task` | `"Bash timeout=<bash_timeout_seconds × 1000>ms"` |
| `false` | no | `orchestrator` | `"Unmeasured; orchestrator-tier until first measurement"` |

Example for a per-task build with `bash_timeout_seconds: 330` — a **measured** Maven module-tests whose learned value sits under the 300 s Maven floor, leaving headroom below the ceiling:

```toon
status: success
module: my-service
command: module-tests
executable: python3 .plan/execute-script.py plan-marshall:build-maven:maven run --command-args "test -pl my-service"
resolution_level: module
bash_timeout_seconds: 330
exceeds_bash_ceiling: false
execution_tier: per_task
hint: Bash timeout=330000ms
```

Example for an orchestrator-tier build (`python:coverage` measured at 1897s):

```toon
status: success
module: plan-marshall
command: coverage
executable: python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run --command-args "coverage plan-marshall"
resolution_level: module
bash_timeout_seconds: 1927
exceeds_bash_ceiling: true
execution_tier: orchestrator
hint: Exceeds Bash ceiling; orchestrator-tier only
```

Example for the unmeasured fail-closed branch — the stamp is comfortably passable, but the command has never been observed, so it hands off rather than gambling a first run in-leaf:

```toon
status: success
module: plan-marshall
command: compile
executable: python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run --command-args "compile plan-marshall"
resolution_level: module
bash_timeout_seconds: 360
exceeds_bash_ceiling: false
execution_tier: orchestrator
hint: Unmeasured; orchestrator-tier until first measurement
```

## Threshold Rationale: `> 600`

The 600-second threshold is `HARNESS_BASH_CEILING_SECONDS` — the Bash tool's `timeout` parameter ceiling on the host platform, declared once in `tools-file-ops/scripts/constants.py`. A build whose recommended Bash timeout exceeds the ceiling cannot be invoked from a per-task sub-agent's Bash call without auto-backgrounding, which produces ≈ 600K tokens of re-dispatch overhead per 12-task plan.

The threshold bounds `exceeds_bash_ceiling`, and is applied to a value computed from real measurements via the adaptive-timeout infrastructure, floored by the engine's own declaration — nothing hard-codes a list of "long-running" commands:

1. First run of any UNMEASURED command — Maven, Gradle, npm, or pyproject alike — resolves `orchestrator` tier by the fail-closed rule, regardless of where the floored stamp lands relative to the ceiling. No command is made runnable in-leaf before it has ever been observed. The stamp itself is still truthful and passable (`max(DEFAULT_BUILD_TIMEOUT, 300) + 30 = 330` for Maven / Gradle / npm; `max(300, 330) + 30 = 360` for pyproject).
2. The first run persists a real duration via `timeout_set` (compute_weighted_timeout favours the higher value), so the key becomes measured.
3. From the next composition on, the tier follows that measurement without any catalogue maintenance: a measured command whose buffered bound stays within the ceiling routes `per_task`, and one that crosses the ceiling routes `orchestrator`.

The system self-corrects in at most two runs, and it errs toward the orchestrator while it is uninformed: a command that will measure past the ceiling is never mis-tiered as `per_task` merely because no measurement exists yet.

## Detection Rules

A resolved `executable` is classified as a Bucket B build notation when **all** of the following hold:

1. The argv contains a token ending in `.plan/execute-script.py` (or `execute-script.py`).
2. The token immediately following the script path is one of the four recognised build notations:
   - `plan-marshall:build-maven:maven`
   - `plan-marshall:build-gradle:gradle`
   - `plan-marshall:build-npm:npm`
   - `plan-marshall:build-pyproject:pyproject_build`
3. The subcommand following the notation is exactly `run`.
4. The argv carries a `--command-args VALUE` (or `--command-args=VALUE`) pair after the subcommand.

Any other shape — Bucket A `manage-*` notations, raw `./pw` calls, `grep` invocations from the `verification` profile, executables that omit `run`, or executables missing `--command-args` — bypass augmentation and return the base TOON unchanged.

## Lookup Path

For a classified executable, the recommended Bash timeout is derived through the same primitives `cmd_run` uses at execute time:

```text
command_key   = compute_command_key(build_skill_CONFIG, command_args)
                # e.g. "python:verify_plan_marshall"
measured      = timeout_measured(command_key, project_dir) is not None
                # the RAW persisted value, unscaled and unfloored — the only
                # signal that distinguishes "never observed" from "observed".
                # timeout_get cannot express it: it returns an int either way.
inner_timeout = timeout_get(command_key, DEFAULT_BUILD_TIMEOUT, project_dir)
                # persisted_value * 1.25 safety margin, or DEFAULT_BUILD_TIMEOUT when unmeasured
inner_timeout = max(inner_timeout, config.min_timeout)
                # the engine's OWN declared floor — maven / gradle / npm: 300,
                # pyproject: 330. Same clamp execute_direct_base applies at
                # build time, so the stamp cannot under-report the real bound.
bash_timeout  = get_bash_timeout(inner_timeout)
                # inner_timeout + 30s OUTER_TIMEOUT_BUFFER
tier          = 'per_task' if (measured and bash_timeout <= ceiling) else 'orchestrator'
```

`timeout_measured` is owned by `manage-run-config`, which owns the store — see that skill's Canonical invocations → `timeout measured`. The measured-ness lookup reuses the SAME `command_key` computed above; there is no second config load and no duplicated key derivation.

The round-trip property holds: the key produced here exactly matches the key persisted by `timeout_set` after a real run, because both paths route through the shared `compute_command_key` helper. The floor clamp preserves that property rather than breaking it — `execute_direct_base` applies the identical `max(..., min_timeout)` at execute time, so the stamped bound and the enforced bound are computed from one value and can never disagree.

## Behavioural Contract

LLMs that read this TOON MUST follow the rule documented in `persona-plan-marshall-agent`:

- `execution_tier=per_task` → pass `timeout=<bash_timeout_seconds × 1000>` on the Bash call.
- `execution_tier=orchestrator` → do NOT invoke the command via Bash from a sub-agent; return control to the orchestrator per the surrounding workflow.

The `hint` field is a recognition token, not optional prose — its presence in the TOON is the structural signal that the contract applies.

## Authored `mutating` signal

A resolved command MAY carry an optional `mutating: true` field. The field is **authored, never inferred**: the operator lists source-mutating profile ids in the `build.maven.profiles.mutating` ext-defaults key (CSV, symmetric with `build.maven.profiles.skip` / `build.maven.profiles.map.canonical`), build-maven's command-map builder stamps `mutating: true` onto every command-map entry derived from a listed profile, and `resolve` surfaces the field additively from the resolved entry. Absence of the field means "not authored as mutating" — unknown, not safe; there is no inferred `mutating: false`.

The canonical trigger is an OpenRewrite-bearing profile: a `quality-gate` that resolves `verify -Ppre-commit` rewrites tracked sources in place, which is destructive when run against a worktree carrying uncommitted work.

**Gate-context behavioural contract**: a worktree gate context (per-task verification, per-deliverable focused build, end-of-phase sweep, pre-push gate) SHOULD prefer a non-mutating candidate when one resolves for the same canonical, and MUST NOT run a `mutating: true` command as the pre-push worktree gate without operator confirmation. The signal rides through `derive-verification`'s command rows unchanged (the deriver copies the resolved dict), so a derived gate command carries the same field.

Example:

```toon
status: success
module: my-service
command: quality-gate
executable: python3 .plan/execute-script.py plan-marshall:build-maven:maven run --command-args "verify -Ppre-commit"
resolution_level: module
mutating: true
bash_timeout_seconds: 600
exceeds_bash_ceiling: false
execution_tier: per_task
hint: Bash timeout=600000ms
```

The example carries the four-field execution-tier augmentation (`bash_timeout_seconds` / `exceeds_bash_ceiling` / `execution_tier` / `hint`) because its `executable` is a Bucket B build notation — the `mutating` stamp composes with that augmentation, it does not replace it.

## Build-class → verification command

`architecture derive-verification --changed-artifacts PATH1,PATH2,...` is the single deterministic consumer of the `build_map` file-to-build contract. It classifies each changed-artifact path to a `build_class` via the merged `build_map` (seed ∪ user overrides, longest-glob-wins), groups by `build_class`, and emits the architecture-resolved verification command set per the closed mapping below. This table is the **single source of truth** for the build_class → command mapping — `manage-execution-manifest` and `phase-4-plan` consume the deriver, they do not re-derive the table.

The `build_class` value **names the canonical command directly** — there is no indirection map between the `build_class` and the command it resolves. The deriver resolves `build_class` as the canonical command itself (via `resolve --command {build_class}`), handling `none` as the only non-`resolve` case. The same word — `compile`, `module-tests`, `verify` — spans `build_map`, this deriver, `architecture resolve`, and the `per_deliverable_build` list of `default:verify:{canonical}` step IDs.

| `build_class` | role it attaches to | derived verification command(s) |
|---|---|---|
| `compile` | production | `architecture resolve --command compile --module {M}` |
| `module-tests` | test | `architecture resolve --command test-compile --module {M}` **+** `architecture resolve --command module-tests --module {M}` |
| `verify` | config | `architecture resolve --command verify --module {M}` (full reactor for the affected module) |
| `none` | any | (no command — a changed set whose only role yields `none` derives no build) |

**Maven IT-signature routing note**: Maven test paths matching the Failsafe naming signature (`*IT.java` / `IT*.java` / `*ITCase.java` under `src/test`) route to the `verify` build_class — the Failsafe-bound full-module gate — rather than `module-tests`, because Surefire's default include patterns exclude them and the plain `test` goal would execute zero of the changed tests. The routing lives in the build-maven extension's `classify_build_class` override; the enum itself is unchanged.

`{M}` is the module resolved per changed path by longest `paths.module` prefix (the finest granularity the architecture API resolves). Derived commands are de-duplicated by their resolved `executable`, so N changed production files in one module derive **one** `compile`, not N. A changed set whose only classification is `none` derives **zero** Python builds — this is the structural property that ends the docs-only build recurrence.

Each architecture-resolved command in the output carries the same four-field execution-tier augmentation documented above (`bash_timeout_seconds` / `exceeds_bash_ceiling` / `execution_tier` / `hint`) when its `executable` is a Bucket B build notation, so the per-task timeout routing applies to derived commands exactly as it does to a direct `resolve`.

### Output

```toon
status: success
changed_count: 3
classified_count: 3
command_count: 2
unclaimed[0]:
commands[2]{build_class,path,module,command,executable,resolution_level,bash_timeout_seconds,exceeds_bash_ceiling,execution_tier,hint}:
  compile,marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/architecture.py,plan-marshall,compile,"python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run --command-args ""compile plan-marshall""",module,360,false,per_task,"Bash timeout=360000ms"
  module-tests,test/plan-marshall/manage-architecture/test_derive_verification.py,plan-marshall,module-tests,"python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run --command-args ""module-tests plan-marshall""",module,360,false,per_task,"Bash timeout=360000ms"
```

Both rows resolve `per_task` because both keys are MEASURED and their buffered bounds stay under the ceiling. Both also land on the same `360`, because the `max(inner_timeout, config.min_timeout)` floor clamp dominates each one's learned value: `compile` at 120 s and `module-tests` at 203 s (`203 × 1.25 = 254`) are both below the 330 s pyproject floor, so both clamp to 330 and buffer to `360`. A learned value only binds the bound once it exceeds the floor — `coverage` at 1897 s is the canonical that does, and it buffers to `1927`, above the ceiling, so it resolves `orchestrator`. The same two rows would resolve `orchestrator` while either key is still unmeasured — see the `execution_tier` row in [Augmented Fields](#augmented-fields).

The `unclaimed` array lists changed paths that no `build_map` glob matched (they derive no build).

## Cross-References

- The Bash-timeout-from-architecture-resolve failure mode that motivated this surface — see `persona-plan-marshall-agent` § "Bash: Timeout from architecture-resolved canonical command" for the behavioural rule.
- [`manage-config`](../../manage-config/standards/data-model.md) § build_map — the file-to-build contract schema the deriver consumes.
- [`client-api.md`](client-api.md) § `resolve` — base resolve invocation and options.
- [`manage-execution-manifest`](../../manage-execution-manifest/standards/decision-rules.md) — manifest composer's `execution_tier` routing rule.
- `persona-plan-marshall-agent` — the agent-side behavioural rule that consumes these fields.
