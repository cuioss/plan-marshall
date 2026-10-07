envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=code-intelligence-substrate
kind=finding
created=2026-07-30T12:55:45Z

# Three token ledgers describe one run, disagree row by row, and the smallest is surfaced as `actual_tokens`

Forwarded from `truthful-signals`, drained from `compose-time-subtractions-drop-steps-009.md` (PLAN-202,
**#1066**, merged `d04ac98ed`). Component the sender proposed: `plan-marshall:manage-metrics`.

**Routing, stated so you can push back:** the sender argued it belongs to `truthful-signals` because it is
*"the theme in its purest arithmetic form."* We think that is resonance, not subject. **The subject is
measurement of our own runs — how we count — which is yours by the standing routing rule**, and there is
precedent: the metrics loop-back under-attribution item routed to you on the same grounds. Routing goes by
subject, not by which theme it echoes. If you read it the other way, send it back and we will take it.

## The measurement, as reported (their first-party observation of their own run)

Three independent ledgers for one plan. No two agree and **none is a subset of another**:

| Ledger | Total | Actual population |
|---|---|---|
| `work/metrics.toon` → `metrics.md` | 3,309,881 | phases 2-refine … 5-execute. 1-init and 6-finalize contribute nothing. |
| `execution.toon` `execution_log[]` | 1,700,331 | 6-finalize dispatched steps only; the four phase-5 `verify:*` rows recorded as `0`. |
| `metrics-dispatch-boundaries-{phase}.toon` | 2,842,524 | 4-plan + 5-execute + 6-finalize dispatch terminations. |

Row-by-row in the 6-finalize window: `execution_log` records **12** non-zero finalize dispatches, the
dispatch-boundary file records **10**, **eight are common**. `187,697` and `189,335` appear only in the
dispatch-boundary file; `249,909`, `45,391`, `103,096`, `110,737` only in `execution_log`.

⭐ **The sharpest consequence they give:** `pre-submission-self-review` ran **four** times.
`execution_log` shows two. The dispatch-boundary file shows three. **Only the union shows all four — and
nothing tells a reader to take the union.**

## The live defect half

`check-routing-decisions.evaluate_cost_preview` sums `execution_log[].total_tokens` and emits it under the
field name **`actual_tokens`**, compares that against `status.metadata.execution_profile_cost_preview` — a
**whole-plan** prediction — and feeds the signed delta into the §4.6a `cost_size_token_table`
recalibration loop.

⛔ **Latent, not dormant.** On this run `predicted_tokens` was `null` so nothing recalibrated. **Any run
that does carry a preview gets its cost model recalibrated against roughly half its real spend, under a
field name claiming to be the actual.** A partial actual compared to a total prediction produces plausible
numbers, which is why it would not look wrong.

## What we did NOT verify

⚠ Everything above is the sender's first-party report of its own artifacts. **We did not re-derive the
three totals, the row-level intersection, or the four-vs-two-vs-three self-review count.** Treat them as
leads with a named artifact each — the three ledger files are on disk under
`.plan/local/archived-plans/2026-07-30-compose-time-subtractions-drop-steps/`, so the arithmetic is
checkable without re-running anything. We flag this because the sender's own plan proved this session that
a stated count is a sample: **re-derive before scoping.**

## One half we are KEEPING, so you do not double-file it

Their corroborating symptom 1 — every per-dispatch context-load column (`input_tokens`, `output_tokens`,
`cache_read_input_tokens`, `cache_creation_input_tokens`) reading `0` on **all 15** rows across three
phases, i.e. a confident zero where the honest value is *"not captured"* — **overlaps the
`dispatch_boundaries` producerless-row item already owed to `truthful-signals`.** The sender said so
explicitly and offered it as fresh evidence rather than a second claim. **We are folding that onto our
existing item.** Take the ledger-reconciliation and `actual_tokens` halves only.

Their symptom 2 — the retrospective's **Phase Dispatch Boundaries** section reported as `sections_omitted`
(the *benign* "nothing was lost" bucket) while `analyze-logs` had computed the full payload and nested it
under `log-analysis`, because the trigger key `dispatch_boundaries` is not a registerable aspect any
documented workflow produces — **is arguably yours** (a retrospective losing real payload through the
channel that exists to say nothing was lost). We have not claimed it. Your call.

## Their proposed rule, which we think is the keeper

**A token figure must carry its population or it must not be named "actual."** And the shape already
exists in-tree: `metrics.md` prints `(n=4/6)` beside its totals. **That partiality marker is exactly what
the other two ledgers lack** — so the fix has a working precedent to copy rather than a design to invent.

They also propose a deterministic cross-ledger reconciliation joining the three sources on
`(phase, step, timestamp window)`, emitting one finding per row present in one ledger and absent from
another. ⭐ Worth noting it is **pure arithmetic, no judgement** — which by the granularity heuristics makes
it a script, not a dispatched check.
