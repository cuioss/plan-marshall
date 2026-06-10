# Check: token-efficiency-trend (cross-plan)

Orders archived plans chronologically and tracks tokens-per-phase across the
corpus over time, detecting a sustained upward regression. This is a cross-plan
check — it emits a chronological series plus a single regression verdict rather
than one row per plan. The deterministic computation lives in
`scripts/audit.py`; this sub-document is the interpretation guide.

## Inputs the check reads

For every scanned plan, the script parses `work/metrics.toon` and sums the
**effective** tokens (`total_tokens - retrospective_tokens`, never negative)
across the recorded phases, then divides by the count of phases that carry
implementation spend to get `tokens_per_phase`. Plan-retrospective spend is
excluded so the trend reflects implementation work only (see below). Plans
without a `metrics.toon` are excluded from the series.

### Plan-retrospective token exclusion

Plan-retrospective spend is deliberate analysis and is excluded from both
`total_tokens` and the phases divisor. The exclusion source is the
`retrospective_tokens` sub-field `manage-metrics` records on the `[6-finalize]`
phase section. A phase whose entire spend is retrospective
(`effective_tokens == 0`) is dropped from the phase count, so `tokens_per_phase`
reflects implementation phases only.

**Best-effort degrade**: the producer wiring that populates `retrospective_tokens`
(the finalize retrospective step forwarding its `<usage>` total through the
`6-finalize` accumulator, which `end-phase` reads back) landed only when this
attribution was wired — before it, NO plan ever recorded the field. Archived plans
from before the wiring carry no `retrospective_tokens`, so their effective tokens
equal the raw `total_tokens` and the exclusion is a no-op (no crash, no negative
values). Only plans archived after the wiring, whose opt-in retrospective step
actually ran, carry the attributed value and have real retrospective spend
excluded from the series and regression. The exclusion is therefore live only
going forward, not for the existing archived corpus.

## Chronological ordering

Plans are ordered by their plan-id date prefix (`YYYY-MM-DD`) when present; when
a plan id lacks the prefix the script falls back to `status.json::plan.created`,
and finally to the plan id itself. This yields a stable chronological sequence
across the corpus.

## Regression rule

The check splits the ordered series into thirds and compares the mean
`tokens_per_phase` of the last third against the first third. A regression is
reported when the series has ≥ 3 plans AND the last-third mean exceeds the
first-third mean by more than 25%, rendered as
`tokens/phase rose {first} → {last} (+{pct}%)`. An empty `regression` value
means no sustained upward trend was detected.

## Emitted columns

```
plans_in_series: K
regression: "<verdict or empty>"
rows[K]{plan_id,phases,total_tokens,tokens_per_phase}
```

| Column | Meaning |
|--------|---------|
| `plan_id` | The scanned plan's directory basename (rows are in chronological order). |
| `phases` | Count of phases carrying implementation (effective) spend — phases whose entire spend is retrospective are excluded. |
| `total_tokens` | Sum of **effective** tokens (retrospective-excluded) across the plan's phases. |
| `tokens_per_phase` | `total_tokens / phases` on the effective values, integer-truncated. |

## How the orchestrator interprets the rows

- **`regression` non-empty** — tokens-per-phase has trended upward across the
  corpus. Surface the verdict; a sustained regression is a process-efficiency
  signal worth investigating (e.g. growing skill-load preamble, larger dispatch
  overhead). It may flow into a lesson via the three-gate policy if the cause is
  identifiable and actionable.
- **`regression` empty** — no sustained upward trend; the series rows remain
  available for manual trend inspection.
- The per-row series is informational context; outlier plans (very high or very
  low `tokens_per_phase`) are usually explained by plan size — cross-read with
  `task-count-efficiency` and `scope-estimate-accuracy` before drawing
  conclusions.

## Critical rules

- The script is the single source of truth for the series and the regression
  verdict. Do not re-order plans or re-derive the regression in chat.
- The 25% / first-third-vs-last-third regression rule is the script's; do not
  substitute a different visual reading.
- This check is read-only; it never edits `.plan/` files.
