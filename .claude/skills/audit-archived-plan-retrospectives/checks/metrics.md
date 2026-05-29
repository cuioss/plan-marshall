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

## Anomaly classes

The check detects four anomaly classes:

| Class | Column | Rule |
|-------|--------|------|
| Disproportionate token usage | `disproportionate_token` | A single phase consuming ≥ 45% of the plan's total tokens. Reported as `{phase}={share%}`. Computed on **effective** tokens — plan-retrospective spend is excluded from BOTH the per-phase numerator and the plan-total denominator (see below). |
| Incomplete recordings | `incomplete_recording` | Missing `metrics.toon` (reported as `true`) or one or more zero-token phases that should carry data (reported as the `,`-joined phase names). Uses raw `total_tokens` (not retrospective-excluded). |
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

**Best-effort degrade**: archived plans recorded BEFORE the `retrospective_tokens`
attribution change have the spend irrecoverably co-mingled in `[6-finalize]`.
Their phases carry no `retrospective_tokens` field, so the effective value equals
the raw `total_tokens` and the exclusion is a no-op — the checks behave exactly as
they did before the change, with no crash and no negative values.

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
  "metrics wrong" from "metrics never written". Zero-token named phases are a
  recording gap worth investigating in `manage-metrics`.
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
