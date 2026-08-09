# Check: metrics

Detects metrics anomalies per archived plan. The deterministic parsing and
anomaly computation live in `scripts/audit.py`; this sub-document is the
interpretation guide for the emitted flags.

## Inputs the check reads

Per scanned plan, the script parses `work/metrics.toon` — the INI-shaped
per-phase block written by `manage-metrics`. Each `[phase-name]` section
contributes `total_tokens`, `duration_seconds` (wall-clock), `idle_duration_ms`,
and `agent_duration_seconds` (worked). When `work/metrics.toon` is absent the
plan is reported as an incomplete recording.

**#812 `end_time`-presence markers**: the script ALSO reads the top-level
`any_phase_missing_end_time` / `phases_missing_end_time` scalars `manage-metrics`
stamps (parsed by `parse_metrics_end_time_presence`). A canonical phase whose row
carries no `end_time` boundary marker is listed in `phases_missing_end_time`, and
`any_phase_missing_end_time` is true whenever that set is non-empty. This is the
recorded signal that a zero-token phase was never closed **by design**, not an
accidental blindness — the metrics check consumes it so a marker-explained
zero-token phase is reported as an informational explained gap rather than an
incomplete-recording anomaly.

**Read the markers for what they say.** They report ONE predicate: does each
canonical phase's row carry an `end_time`? A phase absent from
`phases_missing_end_time` carries the marker, which says nothing about whether
its figures are complete or internally consistent. Do not read the pair as a
completeness verdict — it is not one, and the keys are named for the predicate so
this is checkable at the point of use.

### The three marker states

`parse_metrics_end_time_presence` returns a **three-state** verdict, and every
consuming column reports all three distinctly. Archived `metrics.toon` files are
immutable history, so a record can be in any of them:

| State | Condition | What the check does |
|-------|-----------|---------------------|
| `current` | the new keys are present | reads the values normally |
| `old-schema` | the new keys are absent AND a retired `partial` / `unrecorded_phases` key is present | reports the record as old-schema and explains NO phase. The markers exist under names this reader deliberately does not interpret |
| `pre-#812` | neither the new nor the retired keys are present | reports the record as pre-#812 and explains NO phase |

The two unreadable states are **never collapsed**. Reading an `old-schema` record
as the `pre-#812` degrade — or either as a clean verdict — would manufacture a
verdict out of an absent key, which is the defect the rename exists to remove.
On both unreadable states the explained-phase set is EMPTY, so every zero-token
phase surfaces as unexplained: the loud direction, never the quiet one. The
check appends a distinct anomaly line naming which unreadable state applied.

**Where the flooring happens — not here.** This check floors nothing: it emits no
floor column (see § Emitted columns), and the only thing an unreadable state adds
to its output is that anomaly line. The three-state verdict's `forces_floor` flag
is instead consumed downstream by the **billing-composition** collector, which ORs
it with the `input-integrity` check's `metrics_blind` verdict and an
omitted-canonical-row test to set the `floor` field on each billing-composition
row; any figure a floored row contributed to is then labelled `floor` rather than
`measured`. So `input-integrity` and this check each contribute an INPUT to that
decision, and `billing-composition` is where the flooring is applied. Attributing
the floor to the `metrics` check misreads which surface carries the label.

## Anomaly classes

The check detects four anomaly classes:

| Class | Column | Rule |
|-------|--------|------|
| Disproportionate token usage | `disproportionate_token` | A single phase consuming ≥ 45% of the plan's total tokens. Reported as `{phase}={share%}`. Computed on **effective** tokens — plan-retrospective spend is excluded from BOTH the per-phase numerator and the plan-total denominator (see below). |
| Incomplete recordings | `incomplete_recording` | Missing `metrics.toon` (reported as `true`) or one or more **unexplained** zero-token phases that should carry data (reported as the `,`-joined phase names). Uses raw `total_tokens` (not retrospective-excluded). A zero-token phase listed in #812's `phases_missing_end_time` marker was never closed BY DESIGN and is EXCLUDED from this column — it is surfaced instead as an informational `zero-token phases explained by the phases_missing_end_time marker: …` anomaly note. Only a zero-token phase the markers do NOT explain fills `incomplete_recording`. On an `old-schema` or `pre-#812` record no phase is explained, so every zero-token phase fills this column and the anomaly list names the unreadable state. |
| Impossible values | `impossible_value` | A phase whose worked time exceeds wall-clock (`agent_duration_seconds > duration_seconds + 1s`), reported as `{phase}:worked>{wall}s`; or a negative `idle_duration_ms`, reported as `{phase}:negative_idle`. Genuine recording inconsistency (not a token-spend check; retrospective exclusion does not apply). |
| Optimization signals | `optimization_signal` | A phase whose tokens-per-second ratio is ≥ 3× the median non-zero phase ratio, reported as `{phase}:{ratio}tok/s`. Requires ≥ 3 phases with non-zero duration and effective tokens. Computed on **effective** tokens — a phase whose entire spend is retrospective is excluded from the ratio set and the median. |

### Plan-retrospective token exclusion

Plan-retrospective spend is deliberate analysis, not ordinary phase work, so the
three token-spend checks (`disproportionate_token`, `optimization_signal`, and
the cross-plan `token-efficiency-trend`) exclude it. The exclusion source is the
`retrospective_tokens` sub-field that `manage-metrics` records on the
`[6-finalize]` phase section (the plan-retrospective dispatches under
`--phase phase-6-finalize`, so its spend is otherwise folded into the finalize
total with no separator). Each check computes on the **effective** token value
`total_tokens - retrospective_tokens` (never negative).

**Best-effort degrade**: the producer wiring that populates `retrospective_tokens`
(the finalize retrospective step forwarding its `<usage>` total through the
`6-finalize` accumulator, which `end-phase` reads back) landed only when this
attribution was wired — before it, NO plan ever recorded the field, so the spend
was irrecoverably co-mingled in `[6-finalize]`. Plans archived before the wiring
carry no `retrospective_tokens` field: the effective value equals the raw
`total_tokens` and the exclusion is a no-op (no crash, no negative values). Plans
archived after the wiring — and only those whose opt-in retrospective step
actually ran — carry the attributed value, so the exclusion subtracts the real
retrospective spend. The exclusion is therefore live only going forward, not for
the existing archived corpus.

**Exclusion scope**: ONLY plan-retrospective spend is excluded. q-gate-validation,
the audit itself, and any other operation landing inside a phase window stay
fully counted — the exclusion keys strictly on the `retrospective_tokens`
attribution, not on a broad "finalize" exclusion.

## Emitted columns

```
rows[N]{plan_id,phases_recorded,disproportionate_token,incomplete_recording,impossible_value,optimization_signal}
```

| Column | Meaning |
|--------|---------|
| `plan_id` | The scanned plan's directory basename. |
| `phases_recorded` | Count of `[phase]` sections parsed from `metrics.toon` (0 when absent). |
| `disproportionate_token` | Empty, or `{phase}={share%}` for the first phase over the 45% share threshold. |
| `incomplete_recording` | Empty, `true` (no metrics file), or the `,`-joined zero-token phase names. |
| `impossible_value` | Empty, or the first impossible-value flag (`{phase}:worked>{wall}s` or `{phase}:negative_idle`). |
| `optimization_signal` | Empty, or `{phase}:{ratio}tok/s` for the first token/s outlier phase. |

## How the orchestrator interprets the rows

- **`disproportionate_token`** — surface the phase; a single phase dominating the
  token budget is a candidate optimization target (often phase-3-outline or
  phase-6-finalize). Informational unless it recurs across many plans. The share
  is computed on retrospective-excluded (effective) tokens, so a finalize phase
  is not flagged merely because the plan-retrospective ran inside it.
- **`incomplete_recording: true`** — the plan never recorded metrics; distinguish
  "metrics wrong" from "metrics never written". A zero-token named phase in this
  column is an **unexplained** gap (the #812 markers did not account for it) —
  a genuine recording defect worth investigating in `manage-metrics`. A
  marker-explained zero-token phase does NOT appear here: it is surfaced as a
  `zero-token phases explained by the phases_missing_end_time marker: …` note and
  read as a by-design gap, not a defect. Do NOT re-flag such a phase as a
  recording gap — the recorder deliberately declared it never closed.
  **Before reading this column, read the anomaly list for an unreadable-marker
  line.** On an `old-schema` or `pre-#812` record the markers explain nothing, so
  the column lists every zero-token phase; those entries mean "not explained by a
  marker this reader could read", NOT "the recorder failed". The two unreadable
  states are reported separately, so an `old-schema` archive (recoverable by
  re-reading the record under its retired keys) stays distinguishable from a
  `pre-#812` one (nothing to recover).
- **`impossible_value`** — a genuine recording inconsistency (worked time cannot
  exceed wall-clock for a single agent; idle cannot be negative). Surface it; a
  recurrence across the corpus is a candidate systemic signal that flows into
  the recurring-pattern detector and the three-gate lesson-filing path.
- **`optimization_signal`** — informational; a token/s outlier phase may indicate
  a tight, efficient phase or an under-instrumented one. Cross-read with
  `disproportionate_token` before concluding.

## Critical rules

- The script is the single source of truth for the anomaly flags. Do not
  re-parse `metrics.toon` or re-derive the thresholds in chat.
- This check is read-only; it never edits `.plan/` files.
