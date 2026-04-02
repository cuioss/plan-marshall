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

**Execution mode**: Script-only skill. All access via `python3 .plan/execute-script.py plan-marshall:manage-metrics:manage_metrics`.

**Prohibited actions:**
- Never read/write metrics files directly — use the script commands
- Never hard-code token values — only use data from Task agent `<usage>` tags

**Constraints:**
- Metrics data stored in `.plan/plans/{plan_id}/work/metrics.toon` (intermediate key-value storage for phase timing and token data)
- Human-readable output in `.plan/plans/{plan_id}/metrics.md` (generated markdown with tables showing per-phase duration, tokens, and totals)
- Phase names must be one of: `1-init`, `2-refine`, `3-outline`, `4-plan`, `5-execute`, `6-finalize` (must match `manage-lifecycle` phases exactly)

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

```bash
python3 .plan/execute-script.py plan-marshall:manage-metrics:manage_metrics end-phase \
  --plan-id {plan_id} --phase {phase} \
  [--total-tokens N] [--duration-ms N] [--tool-uses N]
```

**Parameters:**
- `--total-tokens` — Total tokens from Task agent `<usage>` tag (optional, non-negative integer)
- `--duration-ms` — Agent-reported duration in milliseconds from Task agent `<usage>` tag. This is the agent's self-reported time, separate from wall-clock duration computed from start/end timestamps. (optional)
- `--tool-uses` — Tool use count from Task agent `<usage>` tag (optional)

**Token data sources**: Task agents (spawned via Agent tool) report usage in `<usage>` XML tags upon completion. These contain `total_tokens`, `duration_ms`, and optionally `tool_uses`. For main-context phases (not delegated to agents), use the `enrich` command instead.

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

### enrich

Parse JSONL session transcript to extract token usage for main-context phases (phases run in the main conversation, not delegated to agents). Searches `~/.claude/projects/` for JSONL files matching the session_id and sums input/output tokens across all messages.

Token data from enrich is attributed to the plan as a whole (not per-phase), since session transcripts span multiple phases.

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
```

## Storage

```
.plan/plans/{plan_id}/
  work/metrics.toon    # Intermediate timing/token data per phase
  metrics.md           # Human-readable metrics report
```

## Expected Workflow

1. **Phase start**: Call `start-phase` when entering a phase (called by plan-marshall orchestrator)
2. **Phase end**: Call `end-phase` when phase completes, passing token data from agent notifications
3. **Enrich** (optional): Call `enrich` after execution to capture main-context token usage
4. **Generate**: Call `generate` to produce the human-readable metrics.md report

## Error Responses

All errors return TOON with `status: error` and exit code 1.

| Error Code | Cause |
|------------|-------|
| `invalid_plan_id` | plan_id format invalid |
| `invalid_phase` | Phase name not in valid set |
| `no_data` | No metrics collected yet (generate) |
| `write_failed` | File system permission denied |
| `session_not_found` | JSONL file not found for session_id (enrich) |

```toon
status: error
plan_id: my-plan
error: invalid_phase
message: Unknown phase: 7-deploy
```

```toon
status: error
plan_id: my-plan
error: no_data
message: No metrics collected yet
```

```toon
status: error
plan_id: my-plan
error: session_not_found
message: JSONL file not found for session abc123
```

## Integration

### Producers

| Client | Operation | Purpose |
|--------|-----------|---------|
| `plan-marshall:plan-marshall` orchestrator | start-phase, end-phase | Record phase timing at boundaries |
| Phase agents (via Task tool) | end-phase (with token args) | Pass `<usage>` tag data after agent completion |

### Consumers

| Client | Operation | Purpose |
|--------|-----------|---------|
| `phase-6-finalize` | generate | Produce final metrics report |
| User | generate, enrich | Review plan execution statistics |

### Data Sources

- Wall-clock timing: bash timestamps via start-phase/end-phase
- Token data: Task agent `<usage>` tags (total_tokens, duration_ms, tool_uses)
- JSONL enrichment: `~/.claude/projects/` session transcripts

## Related Skills

- `manage-status` — Phase tracking that metrics augment
- `manage-logging` — Work logs that complement metric data
- `phase-5-execute` — Primary phase where metrics are collected
