---
name: manage-metrics
description: Plan metrics collection and reporting for duration and token usage per phase
user-invocable: false
---

# Manage Metrics

Collects wall-clock duration and token usage data per phase, generates incremental metrics.md reports in the plan directory.

## Enforcement

**Execution mode**: Script-only skill. All access via `python3 .plan/execute-script.py plan-marshall:manage-metrics:manage_metrics`.

**Prohibited actions:**
- Never read/write metrics files directly — use the script commands
- Never hard-code token values — only use data from Task agent `<usage>` tags

**Constraints:**
- Metrics data stored in `work/metrics.toon` (intermediate TOON format)
- Human-readable output in `metrics.md` (plan directory root)
- Phase names must be one of: 1-init, 2-refine, 3-outline, 4-plan, 5-execute, 6-finalize

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

```bash
python3 .plan/execute-script.py plan-marshall:manage-metrics:manage_metrics end-phase \
  --plan-id {plan_id} --phase {phase} \
  [--total-tokens N] [--duration-ms N] [--tool-uses N]
```

**Parameters:**
- `--total-tokens` — Total tokens from Task agent `<usage>` tag (optional)
- `--duration-ms` — Duration in milliseconds from Task agent `<usage>` tag (optional)
- `--tool-uses` — Tool use count from Task agent `<usage>` tag (optional)

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

Generate or update metrics.md from collected phase data.

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

### enrich

Parse JSONL session transcript to extract token usage for main-context phases.

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

## Integration

**Called by**: `plan-marshall:plan-marshall` workflows (planning.md, execution.md) at phase boundaries.

**Data sources**:
- Wall-clock timing: bash timestamps via start-phase/end-phase
- Token data: Task agent `<usage>` tags (total_tokens, duration_ms, tool_uses)
- JSONL enrichment: `~/.claude/projects/` session transcripts
