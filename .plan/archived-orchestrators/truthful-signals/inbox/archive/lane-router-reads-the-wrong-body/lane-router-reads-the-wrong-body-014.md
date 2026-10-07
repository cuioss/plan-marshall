envelope_version=1
sender_type=plan
sender_id=lane-router-reads-the-wrong-body
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T10:56:46Z

component=plan-marshall:manage-metrics
category=bug
proposed_title=Dispatch-boundary recording covered 6 of 11 phase-6 dispatches, under-reporting ~313K tokens

# Dispatch-boundary recording covered 6 of 11 phase-6 dispatches, under-reporting ~313K tokens

## Status

**Observed during `lane-router-reads-the-wrong-body`, NOT fixed.**

## The observation

Three independent records of phase-6 dispatch activity disagree:

| Source | Count |
|---|---|
| `logs/work.log` `[DISPATCH]` lines in phase-6 | **11** |
| `execution.toon` `execution_log` rows with non-zero tokens in 6-finalize | **8** |
| `work/metrics-dispatch-boundaries-6-finalize.toon` rows | **6** |

Two token-bearing dispatched steps have **no boundary row at all**:

- `project:finalize-step-review-retrospective` — 43,904 tokens, 7 tool uses
- `lessons-capture` — 125,992 tokens, 43 tool uses

And one row **under-reports** its step:

- `pre-submission-self-review` — boundary row says `149,531`; `execution_log` says `291,624`. The step dispatched twice (09:00:38Z returned `loop_back` for the Step-2 cognitive phase, then re-dispatched at 09:01:41Z). Only the second dispatch was recorded. The `loop_back` boundary was dropped.

Total under-reporting: **~313,000 tokens**, roughly a third of phase-6's real spend.

## Why this is the epic's archetype

`metrics-dispatch-boundaries-6-finalize.toon` reads as a complete audit trail: 6 rows, `unknown_count: 0`, every row carrying a clean `termination_cause=step_complete`. There is no ragged edge, no gap marker, nothing that says "5 dispatches are missing from this file". A consumer computing phase-6 cost from the boundary artifact gets a confident, well-formed, **35%-low** number — and the same artifact is what the retrospective's `DISPATCH_TERMINATION_CAUSE` rule keys its distribution findings on.

Note the specific shape of the `loop_back` loss: the recorder appears to fire on *terminal* step completion, so a dispatch that ends in `loop_back` — a legitimate, documented outcome — leaves no boundary row. **A non-terminal outcome is being silently treated as a non-event.**

## Cross-check

The same asymmetry is visible in 4-plan, in the opposite direction, and `metrics.md` already annotates it:

> `Dispatch-boundary total: 234,460 (recorded; not preferred — smaller than total_tokens under same-population max)`

So the divergence is *known* at the metrics-rendering layer and handled by preferring the larger number — but the boundary artifact itself is left uncorrected and un-annotated, and downstream consumers of the artifact do not get that fallback.

## Proposed action

1. Record a boundary row on **every** dispatch return, including `loop_back` / `blocked_*` / error returns, with the outcome as the `termination_cause`. A dispatch that happened is an event regardless of how it ended.
2. Audit the `record-dispatch-boundary` call sites against the phase-6 dispatched-step roster — `project:finalize-step-review-retrospective` and `lessons-capture` both dispatch correctly and emit `[DISPATCH]` lines, so the missing rows are a call-site coverage gap, not a dispatch-discipline gap.
3. Emit a self-describing completeness field on the artifact (`dispatches_observed` vs `rows_recorded`) so a consumer can see the shortfall instead of inferring completeness from well-formedness.
4. Related standing rule: *a reviewer's or recorder's list of call sites is a SAMPLE, not an enumeration.* Derive the expected row set from the `[DISPATCH]` line population, not from a hand-maintained list of recorder call sites.

## Evidence

- `work/metrics-dispatch-boundaries-6-finalize.toon` — 6 rows, `unknown_count: 0`
- `execution.toon` `execution_log` — 8 token-bearing 6-finalize rows
- `logs/work.log` — 11 `[DISPATCH]` lines between 08:42:19Z and 10:45:13Z
- `logs/work.log` 09:00:38Z — `Complete - returning loop_back for Step 2 cognitive-phase dispatch`
- `metrics.md` § 4-plan — the pre-existing same-population-max annotation
