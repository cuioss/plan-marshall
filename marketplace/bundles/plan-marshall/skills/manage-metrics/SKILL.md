---
name: manage-metrics
description: Plan metrics collection and reporting for duration and token usage per phase
user-invocable: false
mode: script-executor
scope: hybrid
---

# Manage Metrics

Collects wall-clock duration and token usage data per phase, generates incremental metrics.md reports in the plan directory.

**Scope: hybrid** means this skill stores data per-plan (`.plan/plans/{plan_id}/`) but can also enrich from the host platform's session transcripts on disk.

## Enforcement

> **Base contract**: See [manage-contract.md](../ref-workflow-architecture/standards/manage-contract.md) for shared enforcement rules, TOON output format, and error response patterns.

**Skill-specific constraints:**
- Script-only skill — all access via the script API
- Never hard-code token values — only use data from Task agent `<usage>` tags
- Metrics data stored in `.plan/plans/{plan_id}/work/metrics.toon`; human-readable output in `.plan/plans/{plan_id}/metrics.md`
- Phase names must be one of: `1-init`, `2-refine`, `3-outline`, `4-plan`, `5-execute`, `6-finalize` (must match `manage-status` phases exactly)

## Operations

### start-phase

Record phase start timestamp.

```bash
python3 .plan/execute-script.py plan-marshall:manage-metrics:manage-metrics start-phase \
  --plan-id {plan_id} --phase {phase}
```

**Output:**
```toon
status: success
plan_id: EXAMPLE-PLAN
phase: 1-init
start_time: 2026-03-27T10:00:00+00:00
```

### end-phase

Record phase end timestamp with optional token data from Task agent notifications.

**Prerequisite**: `start-phase` must have been called for this phase. If no start time exists, duration cannot be calculated (the phase is silently recorded without duration).

**Idempotency**: Calling `end-phase` multiple times for the same phase replaces the previous end data (does not accumulate).

**Accumulator fallback**: When any of `--total-tokens`, `--tool-uses`, `--duration-ms`, or `--retrospective-tokens` is omitted, `end-phase` reads `work/metrics-accumulator-{phase}.toon` (written by `accumulate-agent-usage`) and uses its running totals for the missing fields. Explicitly passed flags always win over accumulator values. Phases that ran without any agent dispatch (no accumulator file, no flags) are recorded with timestamps only — same behaviour as before; this is the inline-phase recording mode documented under `phase-boundary` (a timestamps-only closed row is fully recorded, never `unrecorded`). The `retrospective_tokens` field is carried alongside the others: the finalize retrospective step seeds it via `accumulate-agent-usage --retrospective-tokens`, and `end-phase` reads it back here so `[6-finalize].retrospective_tokens` is recorded without an explicit flag at the `end-phase` call site.

```bash
python3 .plan/execute-script.py plan-marshall:manage-metrics:manage-metrics end-phase \
  --plan-id {plan_id} --phase {phase} \
  [--total-tokens N] [--duration-ms N] [--tool-uses N] [--retrospective-tokens N]
```

**Parameters:**
- `--total-tokens` — Total tokens from Task agent `<usage>` tag (optional, non-negative integer)
- `--duration-ms` — Agent-reported duration in milliseconds from Task agent `<usage>` tag. This is the agent's self-reported time, separate from wall-clock duration computed from start/end timestamps. (optional)
- `--tool-uses` — Tool use count from Task agent `<usage>` tag (optional)
- `--retrospective-tokens` — Tokens attributable to the plan-retrospective dispatch within this phase window, recorded as the `retrospective_tokens` sub-field (optional; the explicit override for the accumulator-carried value the finalize retrospective step seeds)

**Token data sources**: Task agents (spawned via Agent tool) report usage in `<usage>` XML tags upon completion. These contain `total_tokens`, `duration_ms`, and optionally `tool_uses`. The orchestrator may forward each return's totals via the optional flags above, or rely on `accumulate-agent-usage` to persist them on disk between agent dispatches (recommended for `phase-5-execute` and `phase-6-finalize` — see below).

**Output:**
```toon
status: success
plan_id: EXAMPLE-PLAN
phase: 1-init
end_time: 2026-03-27T10:03:00+00:00
duration_seconds: 180.0
total_tokens: 25514
```

### generate

Generate or update metrics.md from collected phase data. The generated markdown contains a table with per-phase rows showing duration (formatted as `Xm Ys`), token counts, and tool uses, plus totals.

```bash
python3 .plan/execute-script.py plan-marshall:manage-metrics:manage-metrics generate \
  --plan-id {plan_id}
```

**Output:**
```toon
status: success
plan_id: EXAMPLE-PLAN
file: metrics.md
phases_recorded: 6
partial: true
unrecorded_phases[1]:
  - 6-finalize
total_worked_seconds: 572.5
total_wall_seconds: 640.0
total_idle_seconds: 67.5
total_tokens: 86754
total_worked_formatted: 9m32s
total_wall_formatted: 10m40s
total_idle_formatted: 1m7s
total_tokens_formatted: 86.8K
```

The `total_worked_formatted` / `total_wall_formatted` / `total_idle_formatted` fields are produced by `format_duration` (shared with the metrics.md Phase Breakdown table) and `total_tokens_formatted` is produced by `format_tokens_short` from `tools-file-ops` (abbreviated decimal-suffix form, e.g. `599K`, `1.2M`). The raw `total_worked_seconds` / `total_wall_seconds` / `total_idle_seconds` / `total_tokens` seconds-and-count figures are kept alongside them — consumers that want the human-readable form for an `[OK]` row should read the `_formatted` fields instead of re-formatting.

**Partiality (floor-not-truth)**: `partial` and `unrecorded_phases` make the report's completeness first-class. A canonical phase is *recorded* iff its `metrics.toon` row carries an `end_time` (the boundary-close marker); a phase with no row at all is unrecorded too. `unrecorded_phases` lists every canonical phase (from the six-phase model) that lacks that marker, and `partial` is `true` whenever the list is non-empty. A `partial: true` total is a **floor, not a truth** — at least the listed phases' tokens/durations are under-counted (the canonical case is a `6-finalize` whose terminal close never folded its accumulator in). A fully-recorded six-phase plan reports `partial: false` with an empty `unrecorded_phases`. The same verdict is persisted as top-level keys in `metrics.toon` and rendered as a `> Partial: unrecorded phases — …` marker under the `## Phase Breakdown` heading in `metrics.md`; the Phase Breakdown Total uses the canonical-six baseline as its completeness denominator, so an entirely-absent phase renders the Total as partial (`n=k/6`) instead of looking complete.

Returns `status: error, error: no_data` if no metrics have been collected yet (no start-phase/end-phase calls made).

### print-phase-breakdown

Read `metrics.md` from the live plan directory, extract only the `## Phase Breakdown` section (table content from the heading to the next `## ` heading or end-of-file), and persist it. The default behavior writes the section verbatim to the plan-relative artifact path `work/phase-breakdown-output.txt` and emits a TOON envelope `{status, plan_id, file, bytes_written}` — the `finalize-step-print-phase-breakdown` skill consumes the envelope directly with no intermediate stdout capture.

```bash
python3 .plan/execute-script.py plan-marshall:manage-metrics:manage-metrics print-phase-breakdown \
  --plan-id {plan_id} [--output-file PATH | -]
```

**Modes:**

- **Default (no `--output-file`)**: writes `work/phase-breakdown-output.txt` under the plan directory and emits the TOON envelope below.
- **Explicit relative path (`--output-file work/foo.txt`)**: writes the section to the supplied plan-relative path (parent directories are created as needed) and emits the same TOON envelope. Absolute paths are rejected.
- **Legacy stdout (`--output-file -`)**: writes the section verbatim to stdout with no TOON envelope; useful for ad-hoc inspection from a shell.

**Output (success, default + explicit relative)**:
```toon
status: success
plan_id: EXAMPLE-PLAN
file: work/phase-breakdown-output.txt
bytes_written: 412
```

**Output (success, `--output-file -`)**: stdout contains the verbatim section. No TOON status is emitted.

**Output (error, TOON to stdout)**:
```toon
status: error
error: metrics_md_not_found
plan_id: EXAMPLE-PLAN
message: metrics.md not found at {path}
```
or
```toon
status: error
error: phase_breakdown_section_not_found
plan_id: EXAMPLE-PLAN
message: ## Phase Breakdown heading not found in metrics.md
```
or
```toon
status: error
error: output_file_must_be_relative
plan_id: EXAMPLE-PLAN
message: --output-file must be a plan-relative path (no absolute paths, no traversal): {value}
```

### phase-boundary

Atomically end the previous phase, start the next phase, and regenerate
`metrics.md` in a single call. Equivalent to running `end-phase {prev}` (with
optional `--total-tokens` / `--duration-ms` / `--tool-uses` forwarded from the
caller), then `start-phase {next}`, then `generate`. Persisted output
(`work/metrics.toon` and `metrics.md`) is identical to the three-call sequence
— see [data-format.md](standards/data-format.md) for the boundary record
shape.

```bash
python3 .plan/execute-script.py plan-marshall:manage-metrics:manage-metrics phase-boundary \
  --plan-id {plan_id} \
  --prev-phase {prev} --next-phase {next} \
  [--total-tokens N] [--duration-ms N] [--tool-uses N] [--retrospective-tokens N]
```

**Parameters:**
- `--prev-phase` — phase being closed (must be a valid phase name)
- `--next-phase` — phase being entered (must be a valid phase name)
- `--total-tokens`, `--duration-ms`, `--tool-uses` — optional, forwarded
  verbatim to the `end-phase` step. Omit when the closing phase ran in main
  context (no agent `<usage>` data to record).
- `--retrospective-tokens` — optional, recorded as the closing phase's
  `retrospective_tokens` sub-field; the explicit override for the
  accumulator-carried value.

**Output:**
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

The fused call is the canonical path at orchestrator phase boundaries —
prefer it over a manual `end-phase` + `start-phase` + `generate` sequence
whenever the caller knows the exact `prev → next` transition.

`phase-boundary` shares the same accumulator-fallback semantics as
`end-phase`: when `--total-tokens` / `--tool-uses` / `--duration-ms` /
`--retrospective-tokens` are omitted, the closing phase row is filled from
`work/metrics-accumulator-{prev_phase}.toon` if the file exists. Explicit
flags always override accumulator values.

**Inline-phase recording mode (omit the `<usage>` flags)**: a phase that runs
*inline* in the main orchestrator context — rather than as a dispatched
`execution-context` leaf — produces no agent `<usage>` envelope, so the caller
OMITS `--total-tokens` / `--duration-ms` / `--tool-uses` (and has no accumulator
file to fall back on). Omitting them is the sanctioned recording mode for an
inline phase, NOT an incomplete call: the closing phase's `end_time` is stamped
unconditionally, and `generate`'s partiality verdict keys a phase's *recorded*
status solely off that `end_time` marker (see the `generate` "Partiality"
paragraph). A timestamps-only closed row is therefore treated as fully recorded
— it is never listed under `unrecorded_phases` and never flips `partial` to
`true`, preserving the #812 floor-not-truth semantics. This is the path the
inline **1-init → 2-refine** boundary takes (phase-1-init runs inline in the
orchestrator, so its close carries no `<usage>` data), and equally the
recipe-inline **2-refine → 3-outline** / **3-outline → 4-plan** boundaries. The
same guarantee holds for the standalone `end-phase` close.

### boundary-status

**Read-only.** Classify a metrics phase boundary as `stamped`, `missing`, or
`not_applicable` — the detection half of resume-time boundary reconciliation.
On cross-session resume the orchestrator calls this BEFORE dispatching the
current phase: if the prior session's phase skill self-transitioned the status,
the resuming orchestrator's `manage-status transition` is a no-op and the paired
`phase-boundary` call is skipped along with it, silently dropping a whole phase's
token/duration attribution. `boundary-status` inspects `work/metrics.toon` and
reports whether the boundary is half-stamped so the orchestrator can stamp the
missing `phase-boundary` even though the transition already happened. The verb
performs **zero mutation** — `work/metrics.toon` is byte-identical before and
after the call.

```bash
python3 .plan/execute-script.py plan-marshall:manage-metrics:manage-metrics boundary-status \
  --plan-id {plan_id} --next-phase {next} [--prev-phase {prev}]
```

**Parameters:**
- `--next-phase` — phase being entered on resume (required; must be a valid phase name).
- `--prev-phase` — phase that should have been closed before entering `--next-phase`
  (optional; must be a valid phase name). Supply it for a full boundary check;
  omit it to check only the "current phase has no start" condition against
  `--next-phase`.

**Classification** (computed from the `start_time` / `end_time` fields that
`end-phase` writes):
- `not_applicable` — a `--prev-phase` was supplied but that phase has no row at
  all (it never started); there is no boundary to reconcile. Never applies when
  `--prev-phase` is omitted.
- `missing` — the boundary is half-stamped: the prev phase has a `start_time` but
  no `end_time`, OR the next phase has no `start_time`. The offending field(s) are
  named in `missing_fields`.
- `stamped` — the boundary is complete; proceed unchanged.

**Output (missing):**
```toon
status: success
plan_id: EXAMPLE-PLAN
prev_phase: 4-plan
next_phase: 5-execute
classification: missing
missing_fields: 4-plan.end_time,5-execute.start_time
reason: half-stamped boundary — stamp the missing phase-boundary on resume
```

**Output (stamped):**
```toon
status: success
plan_id: EXAMPLE-PLAN
prev_phase: 4-plan
next_phase: 5-execute
classification: stamped
reason: boundary fully recorded — proceed unchanged
```

**Output (not_applicable):**
```toon
status: success
plan_id: EXAMPLE-PLAN
prev_phase: 4-plan
next_phase: 5-execute
classification: not_applicable
reason: prev phase has no metrics row (never started)
```

### accumulate-agent-usage

Persist running per-phase totals of subagent `<usage>` data to disk. Designed
to be called from `phase-5-execute` and `phase-6-finalize` SKILL.md
immediately after every Task-agent return — the on-disk file replaces the
fragile model-context-only `agent_usage_totals` discipline that lost data
across context compactions and inline-only step runs.

```bash
python3 .plan/execute-script.py plan-marshall:manage-metrics:manage-metrics accumulate-agent-usage \
  --plan-id {plan_id} --phase {phase} \
  [--total-tokens N] [--tool-uses N] [--duration-ms N] [--retrospective-tokens N]
```

**Parameters:**
- `--phase` — Phase being accumulated (must be a valid phase name).
- `--total-tokens`, `--tool-uses`, `--duration-ms` — Subagent `<usage>` values to add to the running totals (each optional). Pass the values parsed from the agent's returned `<usage>...</usage>` block.
- `--retrospective-tokens` — Tokens attributable to the plan-retrospective dispatch to add to the running `retrospective_tokens` total (optional). Forwarded by `phase-6-finalize` ONLY when the just-returned dispatched step is the opt-in retrospective step — this is the producer side of the `retrospective_tokens` attribution that `end-phase` / `phase-boundary` read back from the accumulator.

**Behaviour:**
- Reads `.plan/plans/{plan_id}/work/metrics-accumulator-{phase}.toon`, initialising it when absent.
- Sums any provided flags into the existing totals (including `retrospective_tokens`) and increments the `samples` counter.
- Writes the file back atomically. The on-disk file is the only source of truth — the call is idempotent across context compactions.
- `cmd_end_phase` and `cmd_phase_boundary` read the same file when their corresponding flags are omitted.

**Output:**
```toon
status: success
plan_id: EXAMPLE-PLAN
phase: 6-finalize
total_tokens: 84211
tool_uses: 38
duration_ms: 412390
retrospective_tokens: 31200
samples: 4
accumulator_file: work/metrics-accumulator-6-finalize.toon
```

See [data-format.md](standards/data-format.md) for the on-disk schema.

### record-dispatch-boundary

Record one TOON-tabular row per phase Task dispatch termination. Designed to
be called by the orchestrator (`plan-marshall` workflows) immediately after
every phase Task return so the audit trail captures *why* the dispatch
ended — voluntary checkpoint, bare `task_complete` echo, harness
cancellation, error, or clean exit on an empty queue — together with the
dispatched agent's `<usage>` totals at termination time. The accumulating
file is the audit trail that `plan-retrospective` correlates with
`[OUTCOME]`-log coverage gaps to detect agent-initiated re-dispatch
See `plan-retrospective` for the correlation logic.

```bash
python3 .plan/execute-script.py plan-marshall:manage-metrics:manage-metrics record-dispatch-boundary \
  --plan-id {plan_id} --phase {phase} \
  --termination-cause {voluntary_checkpoint|task_complete_returned_verbatim|budget_yield|harness_cancellation|error|clean_exit_queue_empty} \
  [--total-tokens N] [--tool-uses N] [--duration-ms N] \
  [--input-tokens N] [--output-tokens N] [--cache-read-input-tokens N] [--cache-creation-input-tokens N]
```

**Parameters:**
- `--phase` — Phase whose dispatch terminated (must be a valid phase name; in practice this is `5-execute`, but the subcommand accepts any valid phase).
- `--termination-cause` — Why the dispatch ended. Required — missing or unrecognised values are rejected as script errors (there is no implicit fallback). One of:
  - `voluntary_checkpoint` — the agent emitted a "Returning control to orchestrator" / "progress checkpoint" line and stopped with pending work in the queue.
  - `task_complete_returned_verbatim` — the agent returned `execute-task`'s bare `task_complete` payload without wrapping it.
  - `budget_yield` — the dispatch yielded because its assigned `envelope_id` group was exhausted (plan-time bin-packing) after completing ≥1 task — the wrapped terminal payload (`budget_yield: true`, `tasks_remaining > 0`) and the `budget_yield` decision-log entry distinguish it from `task_complete_returned_verbatim`.
  - `harness_cancellation` — the host platform cancelled the dispatch (timeout, context-window limit, etc.).
  - `error` — the dispatch raised a fatal error captured via the skill's Error Handling section.
  - `clean_exit_queue_empty` — canonical value for a clean exit where the loop drove to completion AND `manage-tasks loop-exit-guard` confirmed the pending queue is empty.
- `--total-tokens`, `--tool-uses`, `--duration-ms` — Subagent `<usage>` totals at termination (each optional, default 0).
- `--input-tokens`, `--output-tokens`, `--cache-read-input-tokens`, `--cache-creation-input-tokens` — Per-dispatch context-load totals from the dispatched agent's four-field `message.usage` view at termination (each optional, default 0). These are the per-DISPATCH counterpart to the per-PHASE four-field view `enrich` writes; they are recorded as four columns appended at the END of each row so the legacy five columns stay positionally unchanged. See [data-format.md](standards/data-format.md) § Per-Dispatch Context-Load Attribution for the canonical column order, count, and defaults.

**Behaviour:**
- Appends one row to `.plan/plans/{plan_id}/work/metrics-dispatch-boundaries-{phase}.toon`.
- The file's first three lines are a TOON-tabular header followed by CSV-style data rows; the canonical row-header schema (column order, count, defaults) is owned by [data-format.md](standards/data-format.md) § Per-Dispatch Context-Load Attribution.
- Atomic write — partial files are not visible to readers.
- The same shared file-write helpers as `accumulate-agent-usage` are used.

**Output:**
```toon
status: success
plan_id: EXAMPLE-PLAN
phase: 5-execute
termination_cause: voluntary_checkpoint
total_tokens: 84211
tool_uses: 38
duration_ms: 412390
input_tokens: 38000
output_tokens: 4000
cache_read_input_tokens: 210000
cache_creation_input_tokens: 12000
timestamp: 2026-05-08T14:23:11Z
rows_recorded: 4
dispatch_boundary_file: work/metrics-dispatch-boundaries-5-execute.toon
```

### enrich

Parse JSONL session transcripts to attribute token usage per phase. `enrich`
performs two complementary walks against the host platform's
session-transcript directory:

1. **Parent-transcript `<usage>`-tag walk** — searches for the JSONL file
   matching `session_id` and walks `tool_result` content for embedded
   `<usage>...</usage>` return tags, attributing each tag's single-figure
   totals to the phase whose timestamp window contains the `Task` tool call.
2. **Subagent-transcript walk** — discovers every subagent transcript
   (`{project_dir}/{parent_session_id}/subagents/agent-*.jsonl`) and sums the
   four raw `message.usage` fields across each whole transcript.

All attribution uses the `start_time` / `end_time` windows recorded in
`work/metrics.toon`. Usage outside any recorded phase window is ignored.

```bash
python3 .plan/execute-script.py plan-marshall:manage-metrics:manage-metrics enrich \
  --plan-id {plan_id} --session-id {session_id}
```

**Output:**
```toon
status: success
plan_id: EXAMPLE-PLAN
enriched: true
message_count: 127
subagent_phases_attributed: 3
subagent_calls_attributed: 8
main_phases_attributed: 6
subagent_transcripts_walked: 4
four_field_phases_attributed: 5
```

**Four-field usage view + billing-weighted total**: The four distinct Claude
API usage fields — `input_tokens`, `output_tokens`, `cache_read_input_tokens`,
and `cache_creation_input_tokens` — live only in the raw `message.usage` dicts
inside the transcripts; the single-figure `<usage>` return tag carries no
input/output split and no cache fields. `enrich` accumulates these four fields
per phase from BOTH the parent orchestrator turns AND every discovered subagent
transcript, then records a `billing_weighted_total` per phase computed as
`input + output + round(0.1 × cache_read) + round(1.25 × cache_creation)`. The
weighted total is a **billing-cost figure, NOT a work-comparable measure** —
`cache_read_input_tokens` sums context re-reads across turns, so a long agent
that re-reads its context many times accumulates large `cache_read` that
reflects API billing rather than independent work performed.

**Whole-transcript attribution**: Each subagent transcript is summed as a whole
and attributed to the single phase window containing its spawn/first-message
timestamp (latest-window-wins on a boundary tie). Transcripts are NOT split by
slug boundaries — the whole transcript is attributed to the one phase that
spawned it.

**Slug-gap robustness**: Subagent discovery is anchored to the *resolved parent
transcript location* (`{parent_transcript_path.parent}/{session_id}/subagents`)
rather than re-derived from the current git root. Phase-5 pins cwd to the plan's
worktree, so subagent transcripts produced during phase-5+ live under a
worktree-derived project-dir slug, while `enrich` (run at finalize) may resolve
a main-checkout git root; re-deriving the slug from the git root would look
under the wrong directory and silently return `[]`, zeroing every field. The
direct-session-file fallback branch retains the legacy cwd-slug path.

The per-phase rows in `work/metrics.toon` gain `subagent_total_tokens`,
`subagent_tool_uses`, `subagent_duration_ms`, and `subagent_samples` (from the
`<usage>`-tag walk) plus `input_tokens`, `output_tokens`,
`cache_read_input_tokens`, `cache_creation_input_tokens`, and
`billing_weighted_total` (from the four-field walks) — see
[data-format.md](standards/data-format.md). The existing `total_tokens` field
is left untouched. When the orchestrator called `accumulate-agent-usage` for
the same agent dispatches the on-disk totals are independent of `enrich`'s
per-phase subagent fields, so double-counting does not occur in the closed-phase
row (`total_tokens`), which is filled from the accumulator at `end-phase` time.

## Storage

```text
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
```

### Generated metrics.md

The `generate` command produces a markdown report with:
- Per-phase table (duration formatted as `Xm Ys`, token counts, tool uses)
- Totals row with aggregate values

## Canonical invocations

The canonical argparse surface for `manage-metrics.py`. The D4 plugin-doctor analyzer
(`_analyze_manage_invocation.py`) reads this section as source-of-truth for markdown
notation occurrences across the marketplace. Consuming skills xref this section by
name (e.g., "see `manage-metrics` Canonical invocations → `phase-boundary`") instead
of restating the command inline.

### start-phase

```bash
python3 .plan/execute-script.py plan-marshall:manage-metrics:manage-metrics start-phase \
  --plan-id PLAN_ID --phase PHASE
```

### end-phase

```bash
python3 .plan/execute-script.py plan-marshall:manage-metrics:manage-metrics end-phase \
  --plan-id PLAN_ID --phase PHASE \
  [--total-tokens N] [--duration-ms N] [--tool-uses N] [--retrospective-tokens N]
```

### generate

```bash
python3 .plan/execute-script.py plan-marshall:manage-metrics:manage-metrics generate \
  --plan-id PLAN_ID
```

### print-phase-breakdown

```bash
python3 .plan/execute-script.py plan-marshall:manage-metrics:manage-metrics print-phase-breakdown \
  --plan-id PLAN_ID
```

### phase-boundary

```bash
python3 .plan/execute-script.py plan-marshall:manage-metrics:manage-metrics phase-boundary \
  --plan-id PLAN_ID --prev-phase PHASE --next-phase PHASE \
  [--total-tokens N] [--duration-ms N] [--tool-uses N] [--retrospective-tokens N]
```

### boundary-status

```bash
python3 .plan/execute-script.py plan-marshall:manage-metrics:manage-metrics boundary-status \
  --plan-id PLAN_ID --next-phase PHASE [--prev-phase PHASE]
```

### accumulate-agent-usage

```bash
python3 .plan/execute-script.py plan-marshall:manage-metrics:manage-metrics accumulate-agent-usage \
  --plan-id PLAN_ID --phase PHASE \
  [--total-tokens N] [--tool-uses N] [--duration-ms N] [--retrospective-tokens N]
```

### record-dispatch-boundary

```bash
python3 .plan/execute-script.py plan-marshall:manage-metrics:manage-metrics record-dispatch-boundary \
  --plan-id PLAN_ID --phase PHASE \
  --termination-cause {voluntary_checkpoint|task_complete_returned_verbatim|budget_yield|harness_cancellation|error|clean_exit_queue_empty} \
  [--total-tokens N] [--tool-uses N] [--duration-ms N] \
  [--input-tokens N] [--output-tokens N] [--cache-read-input-tokens N] [--cache-creation-input-tokens N]
```

### enrich

```bash
python3 .plan/execute-script.py plan-marshall:manage-metrics:manage-metrics enrich \
  --plan-id PLAN_ID --session-id SESSION_ID
```

## Expected Workflow

1. **Phase start**: Call `start-phase` when entering a phase (called by plan-marshall orchestrator)
2. **Phase end**: Call `end-phase` when phase completes, passing token data from agent notifications
3. **Enrich** (optional): Call `enrich` after execution to attribute per-phase subagent `<usage>` totals
4. **Generate**: Call `generate` to produce the human-readable metrics.md report

## Error Responses

> See [manage-contract.md](../ref-workflow-architecture/standards/manage-contract.md) for the standard error response format.

| Error Code | Cause |
|------------|-------|
| `invalid_plan_id` | plan_id format invalid |
| `invalid_phase` | Phase name not in valid set (start-phase, end-phase, phase-boundary, boundary-status, accumulate-agent-usage) |
| `no_data` | No metrics collected yet (generate) |
| `write_failed` | File system permission denied |
| `session_not_found` | JSONL file not found for session_id (enrich) |

## Integration

### Producers

| Client | Operation | Purpose |
|--------|-----------|---------|
| `plan-marshall:plan-marshall` orchestrator | start-phase, end-phase, phase-boundary, boundary-status | Record phase timing at boundaries; reconcile a half-stamped boundary on cross-session resume (boundary-status → conditional phase-boundary) |
| `plan-marshall:phase-5-execute` SKILL.md | accumulate-agent-usage | Persist per-task agent `<usage>` totals after each `execute-task` return |
| `plan-marshall:phase-6-finalize` SKILL.md | accumulate-agent-usage | Persist per-step agent `<usage>` totals after each Task-agent return; forwards `--retrospective-tokens` for the opt-in retrospective step (producer side of the `retrospective_tokens` attribution) |
| Phase agents (via Task tool) | end-phase (with token args) | Pass `<usage>` tag data after agent completion (alternative to accumulator path) |

### Consumers

| Client | Operation | Purpose |
|--------|-----------|---------|
| `phase-6-finalize` | generate | Produce final metrics report |
| User | generate, enrich | Review plan execution statistics |

### Data Sources

- Wall-clock timing: bash timestamps via start-phase/end-phase
- Token data: Task agent `<usage>` tags (total_tokens, duration_ms, tool_uses)
- JSONL enrichment: host-platform session transcripts (per-phase subagent `<usage>` attribution)
- Four-field usage view: raw `message.usage` dicts in the parent and subagent transcripts (input_tokens, output_tokens, cache_read_input_tokens, cache_creation_input_tokens), plus the derived `billing_weighted_total`, attributed per phase by `enrich`

## Standards

- [data-format.md](standards/data-format.md) — Storage format for metrics.toon and metrics.md

## Related

- `manage-status` — Phase tracking that metrics augment
- `manage-logging` — Work logs that complement metric data
- `phase-5-execute` — Primary phase where metrics are collected
