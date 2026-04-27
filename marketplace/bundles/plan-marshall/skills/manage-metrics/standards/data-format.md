# Metrics Data Format

Storage format specifications for plan metrics collection and reporting.

## Storage Files

| File | Format | Purpose |
|------|--------|---------|
| `work/metrics.toon` | TOON key-value | Intermediate timing and token data per phase |
| `work/metrics-accumulator-{phase}.toon` | TOON key-value | Per-phase running totals of subagent `<usage>` data, written by `accumulate-agent-usage` and read as fallback by `end-phase` / `phase-boundary` |
| `metrics.md` | Markdown | Human-readable report with tables |

All files live in `.plan/plans/{plan_id}/`. Accumulator files are created lazily — only phases that dispatch agents (and call `accumulate-agent-usage`) produce one.

## Intermediate Storage (metrics.toon)

The metrics.toon file stores raw phase timing and token data as flat key-value pairs:

```toon
phase.1-init.start: 2026-03-27T10:00:00Z
phase.1-init.end: 2026-03-27T10:03:00Z
phase.1-init.total_tokens: 25514
phase.1-init.duration_ms: 180000
phase.1-init.tool_uses: 12
phase.2-refine.start: 2026-03-27T10:03:15Z
phase.2-refine.end: 2026-03-27T10:08:45Z
phase.2-refine.total_tokens: 42000
enriched.input_tokens: 450000
enriched.output_tokens: 35000
enriched.total_tokens: 485000
enriched.message_count: 127
```

### Key Naming Convention

> **Phase naming**: TOON keys use the `phase.{N}-{name}.{field}` prefix form (e.g., `phase.1-init.start`). The canonical phase name is `1-init` — see [manage-contract.md](../../ref-workflow-architecture/standards/manage-contract.md) for the standard phase list.

- `phase.{phase_name}.{field}` — per-phase timing/token data
- `enriched.{field}` — session transcript enrichment data (attributed to plan as a whole)

### Per-Phase Fields

| Field | Type | Source |
|-------|------|--------|
| `start` | ISO 8601 timestamp | `start-phase` command |
| `end` | ISO 8601 timestamp | `end-phase` command |
| `total_tokens` | int | Task agent `<usage>` tag (forwarded explicitly OR read from accumulator file) |
| `duration_ms` | int | Task agent `<usage>` tag (agent-reported, distinct from wall-clock) |
| `tool_uses` | int | Task agent `<usage>` tag |
| `subagent_total_tokens` | int | `enrich` post-hoc transcript walk (sum of `<usage>` totals for Task calls inside this phase's window) |
| `subagent_tool_uses` | int | `enrich` post-hoc transcript walk |
| `subagent_duration_ms` | int | `enrich` post-hoc transcript walk |
| `subagent_samples` | int | `enrich` post-hoc transcript walk — count of attributed Task-agent calls |

`subagent_*` fields exist independently of the closed-phase `total_tokens` row. The closed-phase row is filled at `end-phase` time from explicit flags (preferred) or the accumulator file (fallback). The `subagent_*` fields are written by `enrich` as a post-hoc safety net so that even when the orchestrator never called `accumulate-agent-usage`, the transcript walk surfaces the missed totals.

### Enrichment Fields

| Field | Type | Source |
|-------|------|--------|
| `input_tokens` | int | JSONL session transcript parsing |
| `output_tokens` | int | JSONL session transcript parsing |
| `total_tokens` | int | Sum of input + output |
| `message_count` | int | Number of messages in transcript |

## Generated Report (metrics.md)

The `generate` command produces a markdown report with per-phase rows:

```markdown
# Plan Metrics: my-feature

| Phase | Duration | Tokens | Tool Uses |
|-------|----------|--------|-----------|
| 1-init | 3m 0s | 25,514 | 12 |
| 2-refine | 5m 30s | 42,000 | 8 |
| 3-outline | 8m 15s | 68,000 | 25 |
| **Total** | **16m 45s** | **135,514** | **45** |

## Session Enrichment

- Input tokens: 450,000
- Output tokens: 35,000
- Total tokens: 485,000
- Messages: 127
```

### Duration Formatting

Duration is computed as wall-clock time from start/end timestamps and formatted as `Xm Ys`.

## Valid Phase Names

> Phase names follow the standard 6-phase model. See [manage-contract.md](../../ref-workflow-architecture/standards/manage-contract.md) § Phase Names for the canonical definition.

## Phase Boundary Record

The fused `phase-boundary` subcommand writes the same persisted state as the
sequence `end-phase {prev}` → `start-phase {next}` → `generate`. After a
boundary call, the per-phase fields recorded for the previous phase are
exactly those `end-phase` would have written, and the next phase has a
`start_time` field as if `start-phase` had been called next. `metrics.md` is
regenerated from the resulting state.

### Persisted Fields After `phase-boundary`

For the **previous phase** (closed):

| Field | Source |
|-------|--------|
| `end_time` | Timestamp at boundary call |
| `duration_seconds` | Computed from `start_time` - `end_time` if `start_time` present |
| `agent_duration_ms` | `--duration-ms` (when forwarded) |
| `agent_duration_seconds` | Derived from `--duration-ms` (when forwarded) |
| `total_tokens` | `--total-tokens` (when forwarded) |
| `tool_uses` | `--tool-uses` (when forwarded) |

For the **next phase** (entered):

| Field | Source |
|-------|--------|
| `start_time` | Timestamp at boundary call (always equal to or just after the previous phase `end_time`) |

### Equivalence Guarantee

The fused call produces output that is byte-equivalent to the prior
three-call sequence for the same inputs at the same instant. The only
observable difference is fewer script invocations and a single timestamp
reused for both `end_time` (previous phase) and `start_time` (next phase) —
removing the small wall-clock gap that would otherwise appear between two
separate calls. Treat the gap removal as intentional: phase transitions are
modelled as instantaneous handoffs.

### Boundary Output (TOON)

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

If `generate` cannot run (no phase data at all — only possible at plan
start), the boundary call still writes the start/end records and surfaces the
generate status in `generate_status` / `generate_message` instead of
`metrics_file` / `phases_recorded`.

## Token Data Sources

| Source | When Used | Granularity |
|--------|-----------|-------------|
| Task agent `<usage>` tags (forwarded to `end-phase` flags) | Agent-delegated phases — single agent per phase | Per-phase |
| `accumulate-agent-usage` per-phase accumulator file | Phases that dispatch multiple agents (`5-execute`, `6-finalize`) | Per-phase, summed across agent returns |
| JSONL session transcript (`enrich` main-context) | Main-context phases | Per-plan (spans phases) |
| JSONL session transcript (`enrich` subagent attribution) | Any phase whose timestamp window contains Task tool calls | Per-phase (`subagent_*` fields) |

## Per-Phase Subagent Accumulator (`work/metrics-accumulator-{phase}.toon`)

Written by `accumulate-agent-usage`, read as fallback by `end-phase` and `phase-boundary` when explicit token flags are omitted. One file per phase that dispatches agents (e.g., `work/metrics-accumulator-5-execute.toon`, `work/metrics-accumulator-6-finalize.toon`). Other phases never produce one.

### Format

```toon
plan_id: my-plan
phase: 6-finalize
total_tokens: 84211
tool_uses: 38
duration_ms: 412390
samples: 4
updated: 2026-03-27T10:25:00+00:00
```

### Fields

| Field | Type | Notes |
|-------|------|-------|
| `plan_id` | string | Echoed for sanity-checking against the parent plan directory |
| `phase` | string | Must be one of the canonical phase names |
| `total_tokens` | int | Running sum across every `accumulate-agent-usage` call for this phase |
| `tool_uses` | int | Running sum |
| `duration_ms` | int | Running sum |
| `samples` | int | Number of `accumulate-agent-usage` calls — reflects how many Task-agent returns were rolled in |
| `updated` | ISO 8601 timestamp | Updated atomically on every write |

### Idempotency & Lifecycle

- The file is the only authoritative state for the running totals — model-context numbers are not preserved across context compactions.
- `accumulate-agent-usage` always reads-then-writes: missing flags do not zero a field, they leave it unchanged. Each call increments `samples` by 1 regardless of which flags were provided.
- The file is left in `work/` after `end-phase` consumes it — the audit trail (per-call `samples` count, last `updated` timestamp) is useful when investigating drift between accumulator totals and the closed-phase row.
- `archive-plan` moves `work/` along with the rest of the plan directory; archived accumulator files therefore remain available for retrospective analysis.
