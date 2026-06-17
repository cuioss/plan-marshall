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
phase.2-refine.input_tokens: 38000
phase.2-refine.output_tokens: 4000
phase.2-refine.cache_read_input_tokens: 210000
phase.2-refine.cache_creation_input_tokens: 12000
phase.2-refine.billing_weighted_total: 78000
session_message_count: 127
```

### Key Naming Convention

> **Phase naming**: TOON keys use the `phase.{N}-{name}.{field}` prefix form (e.g., `phase.1-init.start`). The canonical phase name is `1-init` — see [manage-contract.md](../../ref-workflow-architecture/standards/manage-contract.md) for the standard phase list.

- `phase.{phase_name}.{field}` — per-phase timing/token data, including the four-field usage view (`input_tokens`, `output_tokens`, `cache_read_input_tokens`, `cache_creation_input_tokens`) and the derived `billing_weighted_total` written by `enrich`
- `session_message_count` — plan-level count of transcript messages carrying usage data, written by `enrich`

### Per-Phase Fields

| Field | Type | Source |
|-------|------|--------|
| `start` | ISO 8601 timestamp | `start-phase` command |
| `end` | ISO 8601 timestamp | `end-phase` command |
| `total_tokens` | int | Task agent `<usage>` tag (forwarded explicitly OR read from accumulator file) |
| `duration_ms` | int | Task agent `<usage>` tag (agent-reported, distinct from wall-clock) |
| `tool_uses` | int | Task agent `<usage>` tag |
| `retrospective_tokens` | int | Tokens attributable to the plan-retrospective dispatch within the phase window (forwarded explicitly via `--retrospective-tokens` OR read from the accumulator when the finalize retrospective step seeded it). Default-absent — present only on `[6-finalize]` rows of plans where the opt-in retrospective step ran |
| `subagent_total_tokens` | int | `enrich` post-hoc transcript walk (sum of `<usage>` totals for Task calls inside this phase's window) |
| `subagent_tool_uses` | int | `enrich` post-hoc transcript walk |
| `subagent_duration_ms` | int | `enrich` post-hoc transcript walk |
| `subagent_samples` | int | `enrich` post-hoc transcript walk — count of attributed Task-agent calls |
| `input_tokens` | int | `enrich` four-field walk — sum of `message.usage.input_tokens` across the parent orchestrator turns AND every subagent transcript attributed to this phase |
| `output_tokens` | int | `enrich` four-field walk — sum of `message.usage.output_tokens` (same dual-source attribution) |
| `cache_read_input_tokens` | int | `enrich` four-field walk — sum of `message.usage.cache_read_input_tokens` (same dual-source attribution) |
| `cache_creation_input_tokens` | int | `enrich` four-field walk — sum of `message.usage.cache_creation_input_tokens` (same dual-source attribution) |
| `billing_weighted_total` | int | Derived by `enrich` from the four-field view: `input + output + round(0.1 × cache_read) + round(1.25 × cache_creation)`. A billing-cost figure, NOT a work-comparable measure |
| `idle_duration_ms` | int | Derived by `generate` — the per-phase idle residual `max(0, wall_clock_ms - worked_ms)` |

The four-field usage view (`input_tokens`, `output_tokens`, `cache_read_input_tokens`, `cache_creation_input_tokens`) lives only in the raw `message.usage` dicts inside the transcripts — the single-figure `<usage>` return tag carries no input/output split and no cache fields. `enrich` accumulates these four fields per phase from BOTH the parent orchestrator turns and every discovered subagent transcript, then records `billing_weighted_total` per phase. These fields exist independently of `total_tokens`, which `enrich` leaves untouched.

#### Whole-transcript attribution and slug-gap robustness

Each subagent transcript is summed as a whole and attributed to the single phase window containing its spawn/first-message timestamp (latest-window-wins on a boundary tie). Transcripts are NOT split by slug boundaries — the whole transcript is attributed to the one phase that spawned it. Subagent discovery is anchored to the *resolved parent transcript location* (`{parent_transcript_path.parent}/{session_id}/subagents/agent-*.jsonl`) rather than re-derived from the current git root, so the worktree-vs-main-checkout cwd at `enrich` time no longer changes the answer. The direct-session-file fallback branch retains the legacy cwd-slug path.

#### Billing weights

| Field | Weight | Rationale |
|-------|--------|-----------|
| `input_tokens` | 1.0 | Baseline input cost |
| `output_tokens` | 1.0 | Counted at par in the weighted total |
| `cache_read_input_tokens` | 0.1 | A cached read is ~0.1× the cost of an input token (request-stated approximation) |
| `cache_creation_input_tokens` | 1.25 | A cache-creation write is ~1.25× the cost of an input token (request-stated approximation) |

`subagent_*` fields exist independently of the closed-phase `total_tokens` row. The closed-phase row is filled at `end-phase` time from explicit flags (preferred) or the accumulator file (fallback). The `subagent_*` fields are written by `enrich` as a post-hoc safety net so that even when the orchestrator never called `accumulate-agent-usage`, the transcript walk surfaces the missed totals.

### Worked, Reported (Wall), and Idle Time

`generate` derives three time quantities per phase from already-persisted fields — no new pause/resume or user-gate API is introduced:

- **Worked** — effort actually spent on the phase: `worked_ms = max(agent_duration_ms, subagent_duration_ms)` (missing operands treated as `0`). The `max(...)` form is the non-double-counting definition: when a main-context (orchestrating) turn dispatches a subagent, the subagent's wall span overlaps with the orchestrator's own wall span — the orchestrator is awaiting the subagent return, not doing independent compute. Summing the two values would double-count that overlap and could produce `Worked > Reported (wall)`. Taking the maximum lets the longer attribution span subsume the shorter overlap so the per-phase **`Worked <= Reported (wall)`** invariant always holds.
- **Reported (wall)** — wall-clock span of the phase: `duration_seconds` (or, when absent, the span between `start_time` and `end_time`). This is calendar time between the phase's recorded `start_time` and `end_time` (a conversation boundary, not a compute measure). Calendar time is the right basis for the Idle residual because it is the only quantity that captures user-wait gaps — a compute-time wall would collapse Idle to zero by construction.
- **Idle** — the residual user-wait/idle time, persisted into `metrics.toon` as `idle_duration_ms`: `idle = max(0, wall_clock - worked)`. Because Worked is now bounded above by the longer of the two attribution sources rather than their sum, `wall_clock - worked` is non-negative for every phase whose subagent dispatches stay within the phase window, so the `max(0, …)` clamp is a safety net rather than a routine path. Idle time is computed post-hoc via session-boundary inference — `generate` reads the persisted phase window and effort fields and writes `idle_duration_ms` back before rendering.

#### Worked <= Reported (wall) Invariant

For every phase row that carries both signals, `Worked <= Reported (wall)` MUST hold. The invariant is what makes the `Idle` column non-blank for subagent-dispatching phases — when Worked could exceed wall (the prior additive formula), Idle clamped to zero and the column rendered `-`, hiding all user-wait time. The `max(agent_duration_ms, subagent_duration_ms)` definition guarantees the invariant for any phase whose dispatched subagents return within the phase window; out-of-window attribution (a subagent that overruns the boundary) cannot occur because `enrich` only attributes `<usage>` totals to phases whose `start_time..end_time` window contains the subagent's timestamp.

### Enrichment Fields

`enrich` writes the four-field usage view and `billing_weighted_total` per phase (under the `phase.{phase_name}.{field}` prefix — see Per-Phase Fields above), plus one plan-level field:

| Field | Type | Source |
|-------|------|--------|
| `session_message_count` | int | Plan-level count of transcript messages that carried usage data (input/output/total) |

The four-field usage view is no longer stored as plan-level `enriched.{field}` keys — it is attributed per phase by the transcript walks. See the Per-Phase Fields table for `input_tokens`, `output_tokens`, `cache_read_input_tokens`, `cache_creation_input_tokens`, and `billing_weighted_total`.

## Generated Report (metrics.md)

The `generate` command produces a markdown report with per-phase rows:

```markdown
# Plan Metrics: my-feature

| Phase | Worked | Reported (wall) | Idle | Tokens | Tool Uses |
|-------|--------|-----------------|------|--------|-----------|
| 1-init | 2m 30s | 3m 0s | 30s | 25,514 | 12 |
| 2-refine | 4m 0s | 5m 30s | 1m 30s | 42,000 | 8 |
| 3-outline | 7m 0s | 8m 15s | 1m 15s | 68,000 | 25 |
| **Total** | **13m 30s** | **16m 45s** | **3m 15s** | **135,514** | **45** |

## 2-refine

- Total tokens: 42,000
- Input tokens: 38,000
- Output tokens: 4,000
- Cache read input tokens: 210,000
- Cache creation input tokens: 12,000
- **Billing-weighted total**: 78,000 (billing-cost figure, not a work-comparable measure — cache_read sums context re-reads across turns)
```

The four-field usage view and the billing-weighted total are rendered per phase (each phase that carries them gets its own bullet list), not as a single plan-level "Session Enrichment" block. Each four-field bullet renders only when its underlying value is present and non-zero.

### Duration Formatting

The Phase Breakdown table carries three time columns in this order — `Worked`, `Reported (wall)`, `Idle` — followed by `Tokens` and `Tool Uses`. Each cell is formatted as `Xm Ys`. A cell renders `-` when its underlying value is absent or zero (the symmetric per-cell present/absent rule), and the Total row sums `Worked`, `Reported (wall)`, and `Idle` independently. See the Worked, Reported (Wall), and Idle Time subsection above for how each quantity is derived.

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
| `retrospective_tokens` | `--retrospective-tokens` (when forwarded) OR the closing phase's accumulator value |

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
plan_id: EXAMPLE-PLAN
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
| JSONL session transcript (`enrich` subagent `<usage>`-tag attribution) | Any phase whose timestamp window contains Task tool calls | Per-phase (`subagent_*` fields) |
| Raw `message.usage` dicts in the parent + subagent transcripts (`enrich` four-field walk) | Any phase whose window contains a parent turn or a spawned subagent transcript | Per-phase (`input_tokens`, `output_tokens`, `cache_read_input_tokens`, `cache_creation_input_tokens`, `billing_weighted_total`) |

## Per-Phase Subagent Accumulator (`work/metrics-accumulator-{phase}.toon`)

Written by `accumulate-agent-usage`, read as fallback by `end-phase` and `phase-boundary` when explicit token flags are omitted. One file per phase that dispatches agents (e.g., `work/metrics-accumulator-5-execute.toon`, `work/metrics-accumulator-6-finalize.toon`). Other phases never produce one.

### Format

```toon
plan_id: EXAMPLE-PLAN
phase: 6-finalize
total_tokens: 84211
tool_uses: 38
duration_ms: 412390
retrospective_tokens: 31200
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
| `retrospective_tokens` | int | Running sum of `--retrospective-tokens` values — non-zero only when the finalize retrospective step forwarded its `<usage>` total. `end-phase` / `phase-boundary` read this as the fallback for the `[6-finalize].retrospective_tokens` row |
| `samples` | int | Number of `accumulate-agent-usage` calls — reflects how many Task-agent returns were rolled in |
| `updated` | ISO 8601 timestamp | Updated atomically on every write |

### Idempotency & Lifecycle

- The file is the only authoritative state for the running totals — model-context numbers are not preserved across context compactions.
- `accumulate-agent-usage` always reads-then-writes: missing flags do not zero a field, they leave it unchanged. Each call increments `samples` by 1 regardless of which flags were provided.
- The file is left in `work/` after `end-phase` consumes it — the audit trail (per-call `samples` count, last `updated` timestamp) is useful when investigating drift between accumulator totals and the closed-phase row.
- `archive-plan` moves `work/` along with the rest of the plan directory; archived accumulator files therefore remain available for retrospective analysis.
