envelope_version=1
sender_type=plan
sender_id=arm-the-refusal-recovery-that-has-never-run
epic=review-apparatus
kind=candidate-lesson
created=2026-09-07T14:29:18Z

# 6-finalize records neither an accumulator nor a dispatch boundary

component: plan-marshall:manage-metrics
category: bug
confidence: high

## Context

The largest phase of this run is invisible to every measurement channel simultaneously. Three independent channels, all dark, over the phase that did the most work:

1. **No `work/metrics-accumulator-6-finalize.toon`.** `plan-retrospective` Step 2.5 exists specifically to fold that accumulator into `metrics.md` before the efficiency aspect reads, because at `order: 995` the phase is still open. It ran, and had nothing to fold. The `6-finalize` row renders as a dash.
2. **No `work/metrics-dispatch-boundaries-6-finalize.toon`.** The aspect reference singles this file out as carrying the majority of finalize dispatch spend and as the only home for `returned_with_findings` vs `error` rows. This run had 4 loop-back iterations, 5 `pre-submission-self-review` firings and 2 `branch-cleanup` firings; none carries a termination cause. (`5-execute` has no boundary file either — only `4-plan` does, with a single row.)
3. **`check-dispatch-audit` classified 16 of 16 finalize steps as `no_evidence`** — zero `dispatched`, zero `ran_inline` — because the per-step token record was unreadable for every one. `channel_completeness` self-downgraded to `confidence: low` (3 finalize-scoped `[DISPATCH]` lines against 21 completions, ratio 0.143).

## Root cause

Finalize-phase spend is written nowhere durable. Each channel degrades to a shape that reads as benign rather than as unmeasured: a dash in a table cell, an absent file that skips a precondition-guarded rule, and a `no_evidence` bucket whose count is a floor. Individually each is a defensible degradation; jointly they mean the phase that consumed the most tokens contributes zero to every figure.

## Proposed action

The reported total (4,734,349 tokens, `n=4/6` phases) is a **floor**, and nothing in `metrics.md` says so for the token column specifically — the partiality banner reports an `end_time` absence, which is a different claim. Two changes:

1. Write the finalize accumulator durably as each finalize step completes, so Step 2.5's reconcile has something to fold and the phase carries at least its floor.
2. Where a phase contributes no measurement to a total, mark the **total** as a floor rather than only listing the phase in `phases_missing_end_time`. A reader currently sees `4.73M` beside `(n=4/6)` and must reconstruct that the missing 2 include the biggest one.

## Evidence

- aspect: plan_efficiency — `6-finalize` row is `unmeasured` for both duration and tokens after an explicit `manage-metrics generate` reconcile.
- aspect: logging_gap_analysis — `DISPATCH_TERMINATION_CAUSE` evaluated over a population of 1 (the `4-plan` row); the `>50%` agent-initiated-re-dispatch rule's clean result carries no weight.
- aspect: execution_context_dispatch_audit — `dispatch_coverage` 0 dispatched / 0 inline / 16 no-evidence of 16; `channel_completeness` `confidence: low`.
- scale of what is missing: `loop_back_iteration: 4`, 27 build logs in `build-results/` against the 1 build the change-ledger oracle recorded.
