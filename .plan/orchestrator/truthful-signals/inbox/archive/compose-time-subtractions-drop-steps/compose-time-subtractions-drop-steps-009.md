envelope_version=1
sender_type=plan
sender_id=compose-time-subtractions-drop-steps
epic=truthful-signals
kind=candidate-lesson
created=2026-07-30T12:41:42Z

## Proposed lesson metadata

- `component`: `plan-marshall:manage-metrics`
- `category`: `bug`
- `title`: Three token ledgers describe one run, disagree row by row, and one is surfaced as unqualified `actual_tokens`

## Observation

`compose-time-subtractions-drop-steps` produced **three** independent token
ledgers. No two agree, and none of them is a subset of another:

| Ledger | Total | What it actually covers |
|---|---|---|
| `work/metrics.toon` → `metrics.md` | 3,309,881 | phases 2-refine … 5-execute. 1-init and 6-finalize contribute nothing. |
| `execution.toon` `execution_log[]` | 1,700,331 | 6-finalize dispatched steps only. The four phase-5 `verify:*` rows are recorded as `0`. |
| `metrics-dispatch-boundaries-{phase}.toon` | 2,842,524 | 4-plan + 5-execute + 6-finalize dispatch terminations. |

The 6-finalize window is where the divergence is checkable row by row.
`execution_log` records **12** non-zero finalize dispatches; the dispatch-boundary
file records **10**. Eight rows are common. `187,697` and `189,335` appear **only**
in the dispatch-boundary file; `249,909`, `45,391`, `103,096` and `110,737` appear
**only** in `execution_log`.

The consequence is concrete: `pre-submission-self-review` ran **four** times on
this plan. `execution_log` shows two of those runs. The dispatch-boundary file
shows three. **Only the union of the two ledgers shows all four** — and nothing
tells a reader to take the union.

## The part that is a live defect, not just untidiness

`check-routing-decisions.evaluate_cost_preview` sums `execution_log[].total_tokens`
and emits it under the field name **`actual_tokens`**, then compares it against
`status.metadata.execution_profile_cost_preview` — a **whole-plan** prediction —
and feeds the signed delta into the §4.6a `cost_size_token_table` recalibration
loop.

On this run `predicted_tokens` was `null`, so no delta was computed and nothing
was recalibrated. The mechanism is latent, not dormant: any run that *does* carry
a preview gets its cost model recalibrated against roughly **half** its real
spend, under a field name that claims to be the actual.

Two corroborating symptoms in the same substrate:

1. **Every** per-dispatch context-load column (`input_tokens`, `output_tokens`,
   `cache_read_input_tokens`, `cache_creation_input_tokens`) is `0` on **all 15**
   recorded rows across three phases. A consumer reads a confident zero where the
   honest value is "not captured". (This overlaps the `dispatch_boundaries`
   producerless-row item already owed to this epic — recorded here as fresh
   evidence, not as a second claim.)
2. The retrospective's own **Phase Dispatch Boundaries** section was reported as
   `sections_omitted` — the *benign* bucket, documented as "nothing was lost" —
   even though `analyze-logs` had computed the full per-phase payload and nested
   it under `log-analysis`. The section's trigger key `dispatch_boundaries` is not
   a registerable aspect any documented workflow produces, so real payload is
   lost through the channel that exists to say nothing was.

## Rule

A token figure must carry its **population** or it must not be named "actual".
Concretely:

1. Rename `cost_preview.actual_tokens` to name what it sums
   (`finalize_step_tokens`), or widen it to the whole-plan union before comparing
   it against a whole-plan prediction. Comparing a partial actual to a total
   prediction is a recalibration bug that produces plausible numbers.
2. Add a deterministic cross-ledger reconciliation joining the three sources on
   `(phase, step, timestamp window)` and emitting one finding per row present in
   one ledger and absent from another. It is pure arithmetic — no judgement.
3. `metrics.md` already does this right: it prints `(n=4/6)` beside its totals.
   That partiality marker is the shape the other two ledgers lack.

## Why it belongs to this epic

It is the theme in its purest arithmetic form. Three confident totals, each
correct about its own population, none of them stating that population, and a
recalibration loop downstream that will read the smallest one as the truth.
