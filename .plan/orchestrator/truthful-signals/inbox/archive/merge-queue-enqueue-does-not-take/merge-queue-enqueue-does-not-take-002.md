envelope_version=1
sender_type=plan
sender_id=merge-queue-enqueue-does-not-take
epic=truthful-signals
kind=candidate-lesson
created=2026-08-03T20:58:31Z

component=plan-marshall:manage-metrics
category=bug
title=metrics.md is frozen before 6-finalize and never regenerated after a loop-back
confidence=high
source_plan=merge-queue-enqueue-does-not-take
source_pr=1087
routed_from=review-apparatus

# metrics.md is frozen before 6-finalize and never regenerated after a loop-back

## Context

`metrics.md` is the human-readable cost record of a plan, and the input the retrospective's plan-efficiency aspect is specified to read. On this plan it understates the plan's token spend by roughly **40 percent** and mis-states a phase it does cover.

## Root cause

**Frozen too early.** `metrics.md` carries `Generated: 2026-08-03 15:05:19 UTC` — the instant 5-execute ended. It is never regenerated. Its own header admits `> Partial: unrecorded phases — 6-finalize`, and the 6-finalize row is all dashes.

6-finalize then consumed **2,000,009 tokens** across 8 dispatched steps (summed from `manage-execution-manifest:record-step` decision-log entries; independently corroborated by the routing-decisions fragment's `actual_tokens: 2000009`). The reported total is `3,008,681 (n=4/6)`; the real floor is ~5,008,690. The single largest step in the entire plan — `pre-submission-self-review` at 1,192,610 tokens — appears nowhere in the metrics artifact.

**Stale after loop-back.** This plan looped back 6-finalize → 5-execute at 19:05:51Z and re-ran execute. `metrics.md`'s 5-execute detail says "2 row(s) recorded"; `analyze-logs` reports **3** dispatch-boundary rows for 5-execute. The artifact is stale against the plan's own logs for a phase it *does* cover, so the `(n=4/6)` marker understates the problem — one of those 4 rows is wrong too.

**1-init is never measured at all**, at any source. So every plan total is structurally a floor.

The net effect is the epic's own theme: a confidently-formatted table, with population markers that look rigorous (`n=4/6`, `dispatched-subagent population`), that is nonetheless missing the plan's most expensive phase.

## Proposed action

1. Regenerate `metrics.md` as the LAST finalize step (after `record-metrics`), not at the 5→6 transition. `record-metrics` already sits at position 20 of 22 in this plan's manifest — the artifact just is not rewritten from it.
2. Invalidate and recompute on loop-back. A `loop_back_reentry` in `status.metadata` MUST force a regeneration of every phase row it re-entered.
3. Make the partial marker load-bearing: when `6-finalize` is unrecorded, the Total row should read `FLOOR`, not a total with a footnote.
4. Measure 1-init, or state explicitly that it is unmeasurable and why.

## Evidence

- `metrics.md` header `Generated: 2026-08-03 15:05:19 UTC`, `> Partial: unrecorded phases — 6-finalize`, Total `3,008,681 (n=4/6)`.
- 8 `record-step` decision-log entries for 6-finalize summing to 2,000,009; `fragment-routing-decisions.toon` `actual_tokens: 2000009`.
- `metrics.md` 5-execute "2 row(s) recorded" vs `fragment-log-analysis.toon` `dispatch_boundaries.5-execute.rows[3]`.
- decision.log 19:05:51Z loop-back.

## Dedup context for the orchestrator

New. No consulted lesson covers metrics-artifact staleness. Adjacent to the `Emit ≠ running` archetype (an artifact asserting a state it did not re-derive). Gate 1 dedup NOT run (`orchestrated: true`).
