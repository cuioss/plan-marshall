# `architecture resolve` — Augmented TOON Contract

`architecture resolve --command COMMAND [--module MODULE]` returns the executable form of a project-architecture command. For Bucket B build notations (Maven / Gradle / npm / pyprojectx builds invoked via `python3 .plan/execute-script.py plan-marshall:build-{tool}:{tool} run --command-args "<args>"`), the resolve TOON is augmented with four additional fields so the calling LLM can apply the correct Bash-tool timeout and routing without re-implementing the lookup.

This document is the authoritative source for the augmented fields. The base resolve invocation, options, error contract, and the un-augmented TOON shape are documented in [`client-api.md`](client-api.md) § `resolve`.

## Augmented Fields

When the resolved `executable` matches the Bucket B build shape, the result carries these four fields in addition to the base `status`, `module`, `command`, `executable`, and `resolution_level`:

| Field | Type | Description |
|-------|------|-------------|
| `bash_timeout_seconds` | int | Recommended Bash-tool timeout in seconds. Computed as `timeout_get(command_key, DEFAULT_BUILD_TIMEOUT) + OUTER_TIMEOUT_BUFFER` — identical arithmetic to `cmd_run`. |
| `exceeds_bash_ceiling` | bool | `bash_timeout_seconds > 600`. The Bash tool's `timeout` parameter is capped at 600s (10 minutes) by the host platform; values above this ceiling cannot be invoked synchronously from a sub-agent. |
| `execution_tier` | enum | `"per_task"` when `exceeds_bash_ceiling` is false; `"orchestrator"` when true. Drives the manifest composer's routing decision (per-task verification vs `phase_5.verification_steps`). |
| `hint` | string | Short pinned recognition phrase. See [Hint Strings](#hint-strings) below. |

The four fields are emitted **as a unit** — either all four are present (Bucket B build executable, resolvable timeout) or all four are omitted (non-build executable, or the build skill could not be loaded). Consumers detect their absence and fall back to today's behaviour.

## Hint Strings

The `hint` field is a recognition token for the LLM, not human prose. The pinned phrases are:

| Tier | `hint` value |
|------|--------------|
| `per_task` | `"Bash timeout=<bash_timeout_seconds × 1000>ms"` |
| `orchestrator` | `"Exceeds Bash ceiling; orchestrator-tier only"` |

Example for a per-task build with `bash_timeout_seconds: 330`:

```toon
status: success
module: plan-marshall
command: module-tests
executable: python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run --command-args "module-tests plan-marshall"
resolution_level: module
bash_timeout_seconds: 330
exceeds_bash_ceiling: false
execution_tier: per_task
hint: Bash timeout=330000ms
```

Example for an orchestrator-tier build (`python:verify_plan_marshall` measured at 931s):

```toon
status: success
module: plan-marshall
command: verify
executable: python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run --command-args "verify plan-marshall"
resolution_level: module
bash_timeout_seconds: 1194
exceeds_bash_ceiling: true
execution_tier: orchestrator
hint: Exceeds Bash ceiling; orchestrator-tier only
```

## Threshold Rationale: `> 600`

The 600-second threshold is the Bash tool's `timeout` parameter ceiling on the host platform. A build whose recommended Bash timeout exceeds the ceiling cannot be invoked from a per-task sub-agent's Bash call without auto-backgrounding, which produces ≈ 600K tokens of re-dispatch overhead per 12-task plan.

The threshold is computed from real measurements via the adaptive-timeout infrastructure — nothing hard-codes a list of "long-running" commands:

1. First run of an unmeasured command falls back to `DEFAULT_BUILD_TIMEOUT = 300` → `bash_timeout_seconds = 330` → `per_task` tier.
2. If that run actually exceeds the timeout, `timeout_set` adaptively updates the persisted value (compute_weighted_timeout favours the higher value).
3. The next composition automatically routes the command to `orchestrator` tier without any catalogue maintenance.

The system self-corrects in at most two runs.

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

```
command_key   = compute_command_key(build_skill_CONFIG, command_args)
                # e.g. "python:verify_plan_marshall"
inner_timeout = timeout_get(command_key, DEFAULT_BUILD_TIMEOUT, project_dir)
                # persisted_value * 1.25 safety margin, or DEFAULT_BUILD_TIMEOUT when unmeasured
bash_timeout  = get_bash_timeout(inner_timeout)
                # inner_timeout + 30s OUTER_TIMEOUT_BUFFER
```

The round-trip property holds: the key produced here exactly matches the key persisted by `timeout_set` after a real run, because both paths route through the shared `compute_command_key` helper.

## Behavioural Contract

LLMs that read this TOON MUST follow the rule documented in `dev-agent-behavior-rules`:

- `execution_tier=per_task` → pass `timeout=<bash_timeout_seconds × 1000>` on the Bash call.
- `execution_tier=orchestrator` → do NOT invoke the command via Bash from a sub-agent; return control to the orchestrator per the surrounding workflow.

The `hint` field is a recognition token, not optional prose — its presence in the TOON is the structural signal that the contract applies.

## Cross-References

- The Bash-timeout-from-architecture-resolve failure mode that motivated this surface — see `dev-agent-behavior-rules` § "Bash: Timeout from architecture-resolved canonical command" for the behavioural rule.
- [`client-api.md`](client-api.md) § `resolve` — base resolve invocation and options.
- [`manage-execution-manifest`](../../manage-execution-manifest/standards/decision-rules.md) — manifest composer's `execution_tier` routing rule.
- `dev-agent-behavior-rules` — the agent-side behavioural rule that consumes these fields.
