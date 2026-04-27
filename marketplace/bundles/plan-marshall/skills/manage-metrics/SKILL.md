---
name: manage-metrics
description: Plan metrics collection and reporting for duration and token usage per phase
user-invocable: false
scope: hybrid
---

# Manage Metrics

Collects wall-clock duration and token usage data per phase, generates incremental metrics.md reports in the plan directory.

**Scope: hybrid** means this skill stores data per-plan (`.plan/plans/{plan_id}/`) but can also enrich from global session transcripts (`~/.claude/projects/`).

## Enforcement

> **Base contract**: See [manage-contract.md](../ref-workflow-architecture/standards/manage-contract.md) for shared enforcement rules, TOON output format, and error response patterns.

**Skill-specific constraints:**
- Script-only skill — all access via the script API; script uses underscore (`manage_metrics`) for Python module compatibility
- Never hard-code token values — only use data from Task agent `<usage>` tags
- Metrics data stored in `.plan/plans/{plan_id}/work/metrics.toon`; human-readable output in `.plan/plans/{plan_id}/metrics.md`
- Phase names must be one of: `1-init`, `2-refine`, `3-outline`, `4-plan`, `5-execute`, `6-finalize` (must match `manage-status` phases exactly)

## Operations

### start-phase

Record phase start timestamp.

```bash
python3 .plan/execute-script.py plan-marshall:manage-metrics:manage_metrics start-phase \
  --plan-id {plan_id} --phase {phase}
```

**Output:**
```toon
status: success
plan_id: my-plan
phase: 1-init
start_time: 2026-03-27T10:00:00+00:00
```

### end-phase

Record phase end timestamp with optional token data from Task agent notifications.

**Prerequisite**: `start-phase` must have been called for this phase. If no start time exists, duration cannot be calculated (the phase is silently recorded without duration).

**Idempotency**: Calling `end-phase` multiple times for the same phase replaces the previous end data (does not accumulate).

**Accumulator fallback**: When any of `--total-tokens`, `--tool-uses`, or `--duration-ms` is omitted, `end-phase` reads `work/metrics-accumulator-{phase}.toon` (written by `accumulate-agent-usage`) and uses its running totals for the missing fields. Explicitly passed flags always win over accumulator values. Phases that ran without any agent dispatch (no accumulator file, no flags) are recorded with timestamps only — same behaviour as before.

```bash
python3 .plan/execute-script.py plan-marshall:manage-metrics:manage_metrics end-phase \
  --plan-id {plan_id} --phase {phase} \
  [--total-tokens N] [--duration-ms N] [--tool-uses N]
```

**Parameters:**
- `--total-tokens` — Total tokens from Task agent `<usage>` tag (optional, non-negative integer)
- `--duration-ms` — Agent-reported duration in milliseconds from Task agent `<usage>` tag. This is the agent's self-reported time, separate from wall-clock duration computed from start/end timestamps. (optional)
- `--tool-uses` — Tool use count from Task agent `<usage>` tag (optional)

**Token data sources**: Task agents (spawned via Agent tool) report usage in `<usage>` XML tags upon completion. These contain `total_tokens`, `duration_ms`, and optionally `tool_uses`. The orchestrator may forward each return's totals via the optional flags above, or rely on `accumulate-agent-usage` to persist them on disk between agent dispatches (recommended for `phase-5-execute` and `phase-6-finalize` — see below). For main-context phases (no agent dispatch), use `enrich` to capture session tokens.

**Output:**
```toon
status: success
plan_id: my-plan
phase: 1-init
end_time: 2026-03-27T10:03:00+00:00
duration_seconds: 180.0
total_tokens: 25514
```

### generate

Generate or update metrics.md from collected phase data. The generated markdown contains a table with per-phase rows showing duration (formatted as `Xm Ys`), token counts, and tool uses, plus totals.

```bash
python3 .plan/execute-script.py plan-marshall:manage-metrics:manage_metrics generate \
  --plan-id {plan_id}
```

**Output:**
```toon
status: success
plan_id: my-plan
file: metrics.md
phases_recorded: 4
total_duration_seconds: 572.5
total_tokens: 86754
```

Returns `status: error, error: no_data` if no metrics have been collected yet (no start-phase/end-phase calls made).

### phase-boundary

Atomically end the previous phase, start the next phase, and regenerate
`metrics.md` in a single call. Equivalent to running `end-phase {prev}` (with
optional `--total-tokens` / `--duration-ms` / `--tool-uses` forwarded from the
caller), then `start-phase {next}`, then `generate`. Persisted output
(`work/metrics.toon` and `metrics.md`) is identical to the three-call sequence
— see [data-format.md](standards/data-format.md) for the boundary record
shape.

```bash
python3 .plan/execute-script.py plan-marshall:manage-metrics:manage_metrics phase-boundary \
  --plan-id {plan_id} \
  --prev-phase {prev} --next-phase {next} \
  [--total-tokens N] [--duration-ms N] [--tool-uses N]
```

**Parameters:**
- `--prev-phase` — phase being closed (must be a valid phase name)
- `--next-phase` — phase being entered (must be a valid phase name)
- `--total-tokens`, `--duration-ms`, `--tool-uses` — optional, forwarded
  verbatim to the `end-phase` step. Omit when the closing phase ran in main
  context (no agent `<usage>` data to record).

**Output:**
```toon
status: success
plan_id: my-plan
prev_phase: 1-init
next_phase: 2-refine
end_time: 2026-03-27T10:03:00+00:00
start_time: 2026-03-27T10:03:00+00:00
prev_duration_seconds: 180.0
prev_total_tokens: 25514
metrics_file: metrics.md
phases_recorded: 2
```

The fused call is the canonical path at orchestrator phase boundaries —
prefer it over a manual `end-phase` + `start-phase` + `generate` sequence
whenever the caller knows the exact `prev → next` transition.

`phase-boundary` shares the same accumulator-fallback semantics as
`end-phase`: when `--total-tokens` / `--tool-uses` / `--duration-ms` are
omitted, the closing phase row is filled from `work/metrics-accumulator-{prev_phase}.toon`
if the file exists. Explicit flags always override accumulator values.

### accumulate-agent-usage

Persist running per-phase totals of subagent `<usage>` data to disk. Designed
to be called from `phase-5-execute` and `phase-6-finalize` SKILL.md
immediately after every Task-agent return — the on-disk file replaces the
fragile model-context-only `agent_usage_totals` discipline that lost data
across context compactions and inline-only step runs.

```bash
python3 .plan/execute-script.py plan-marshall:manage-metrics:manage_metrics accumulate-agent-usage \
  --plan-id {plan_id} --phase {phase} \
  [--total-tokens N] [--tool-uses N] [--duration-ms N]
```

**Parameters:**
- `--phase` — Phase being accumulated (must be a valid phase name).
- `--total-tokens`, `--tool-uses`, `--duration-ms` — Subagent `<usage>` values to add to the running totals (each optional). Pass the values parsed from the agent's returned `<usage>...</usage>` block.

**Behaviour:**
- Reads `.plan/plans/{plan_id}/work/metrics-accumulator-{phase}.toon`, initialising it when absent.
- Sums any provided flags into the existing totals and increments the `samples` counter.
- Writes the file back atomically. The on-disk file is the only source of truth — the call is idempotent across context compactions.
- `cmd_end_phase` and `cmd_phase_boundary` read the same file when their corresponding flags are omitted.

**Output:**
```toon
status: success
plan_id: my-plan
phase: 6-finalize
total_tokens: 84211
tool_uses: 38
duration_ms: 412390
samples: 4
accumulator_file: work/metrics-accumulator-6-finalize.toon
```

See [data-format.md](standards/data-format.md) for the on-disk schema.

### enrich

Parse JSONL session transcript to extract token usage for main-context
phases AND attribute subagent `<usage>` totals to the phase whose timestamp
window contains each `Task` tool call. Searches `~/.claude/projects/` for
JSONL files matching the `session_id`, sums main-context input/output
tokens across all messages, and walks `tool_result` content for embedded
`<usage>...</usage>` blocks.

Main-context tokens are attributed to the plan as a whole; subagent totals
are attributed per-phase via the `start_time` / `end_time` recorded in
`work/metrics.toon`. Subagent calls outside any recorded phase window are
ignored.

```bash
python3 .plan/execute-script.py plan-marshall:manage-metrics:manage_metrics enrich \
  --plan-id {plan_id} --session-id {session_id}
```

**Output:**
```toon
status: success
plan_id: my-plan
enriched: true
input_tokens: 450000
output_tokens: 35000
total_tokens: 485000
message_count: 127
subagent_phases_attributed: 3
subagent_calls_attributed: 8
```

The per-phase rows in `work/metrics.toon` gain `subagent_total_tokens`,
`subagent_tool_uses`, `subagent_duration_ms`, and `subagent_samples` fields
— see [data-format.md](standards/data-format.md). When the orchestrator
called `accumulate-agent-usage` for the same agent dispatches the on-disk
totals are independent of `enrich`'s per-phase subagent fields, so
double-counting does not occur in the closed-phase row (`total_tokens`),
which is filled from the accumulator at `end-phase` time.

## Storage

```
.plan/plans/{plan_id}/
  work/metrics.toon                        # Intermediate timing/token data per phase
  work/metrics-accumulator-{phase}.toon    # Per-phase subagent <usage> running totals (one per phase that dispatches agents)
  metrics.md                               # Human-readable metrics report
```

### metrics.toon Format

```toon
phases:
  1-init:
    start_time: 2026-03-27T10:00:00+00:00
    end_time: 2026-03-27T10:03:00+00:00
    duration_seconds: 180.0
    total_tokens: 25514
    duration_ms: 23332
    tool_uses: 12
  2-refine:
    start_time: 2026-03-27T10:03:30+00:00
    end_time: 2026-03-27T10:05:00+00:00
    duration_seconds: 90.0
enrichment:
  input_tokens: 450000
  output_tokens: 35000
  total_tokens: 485000
  message_count: 127
```

### Generated metrics.md

The `generate` command produces a markdown report with:
- Per-phase table (duration formatted as `Xm Ys`, token counts, tool uses)
- Totals row with aggregate values
- Enrichment section (if `enrich` was called)

## Expected Workflow

1. **Phase start**: Call `start-phase` when entering a phase (called by plan-marshall orchestrator)
2. **Phase end**: Call `end-phase` when phase completes, passing token data from agent notifications
3. **Enrich** (optional): Call `enrich` after execution to capture main-context token usage
4. **Generate**: Call `generate` to produce the human-readable metrics.md report

## Error Responses

> See [manage-contract.md](../ref-workflow-architecture/standards/manage-contract.md) for the standard error response format.

| Error Code | Cause |
|------------|-------|
| `invalid_plan_id` | plan_id format invalid |
| `invalid_phase` | Phase name not in valid set (start-phase, end-phase, phase-boundary, accumulate-agent-usage) |
| `no_data` | No metrics collected yet (generate) |
| `write_failed` | File system permission denied |
| `session_not_found` | JSONL file not found for session_id (enrich) |

## Integration

### Producers

| Client | Operation | Purpose |
|--------|-----------|---------|
| `plan-marshall:plan-marshall` orchestrator | start-phase, end-phase, phase-boundary | Record phase timing at boundaries |
| `plan-marshall:phase-5-execute` SKILL.md | accumulate-agent-usage | Persist per-task agent `<usage>` totals after each `execute-task` return |
| `plan-marshall:phase-6-finalize` SKILL.md | accumulate-agent-usage | Persist per-step agent `<usage>` totals after each Task-agent return |
| Phase agents (via Task tool) | end-phase (with token args) | Pass `<usage>` tag data after agent completion (alternative to accumulator path) |

### Consumers

| Client | Operation | Purpose |
|--------|-----------|---------|
| `phase-6-finalize` | generate | Produce final metrics report |
| User | generate, enrich | Review plan execution statistics |

### Data Sources

- Wall-clock timing: bash timestamps via start-phase/end-phase
- Token data: Task agent `<usage>` tags (total_tokens, duration_ms, tool_uses)
- JSONL enrichment: `~/.claude/projects/` session transcripts

## Standards

- [data-format.md](standards/data-format.md) — Storage format for metrics.toon and metrics.md

## Related

- `manage-status` — Phase tracking that metrics augment
- `manage-logging` — Work logs that complement metric data
- `phase-5-execute` — Primary phase where metrics are collected
