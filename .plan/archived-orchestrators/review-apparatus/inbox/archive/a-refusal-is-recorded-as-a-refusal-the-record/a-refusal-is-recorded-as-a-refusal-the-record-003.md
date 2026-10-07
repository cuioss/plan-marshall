envelope_version=1
sender_type=plan
sender_id=a-refusal-is-recorded-as-a-refusal-the-record
epic=review-apparatus
kind=candidate-lesson
created=2026-08-31T08:07:16Z

component=plan-marshall:manage-metrics
category=bug
title=re_entered_phases reports empty on a plan with three recorded loop-backs into 5-execute

# re_entered_phases reports empty on a plan with three recorded loop-backs into 5-execute

## Context

Plan `a-refusal-is-recorded-as-a-refusal-the-record` looped back from `6-finalize` into `5-execute` three times. All three are recorded, twice over:

- `status.metadata.loop_back_iteration` is `"3"`, and `status.metadata.loop_back_reentry` holds the latest re-entry.
- `decision.log` carries three `(plan-marshall:manage-status) Loop-back set-phase 6-finalize -> 5-execute` entries, at `09:27:04Z`, `12:53:17Z` and `20:14:29Z` on 2026-08-30, each followed by real execute work (TASK-014/015, TASK-016, TASK-017) with its own quality-gate runs.

`work/metrics.toon` nevertheless records `5-execute` as:

```
close_count: 1
value_scope: single_close
end_time: 2026-08-30T02:15:02Z
```

— an end_time that precedes all three re-entries. `manage-metrics generate` correspondingly reports `re_entered_phases[0]` (empty).

## Root cause

The loop-back path sets the phase back to `5-execute` but no second `end-phase` / `phase-boundary` close is recorded for it, so the row is never re-closed and `close_count` never increments. `manage-metrics/SKILL.md` names `close_count` the **authoritative** re-entry signal — "Because `close_count` is written at the write site, this is the authoritative re-entry signal" — so on this plan the authoritative signal reports no re-entry over a plan that re-entered three times. The weaker `boundary_monotonicity` inference is also empty, so nothing in the metrics record dissents.

## Impact — this is a measurement defect, not a cosmetic one

Because `5-execute`'s wall span closed at 02:15Z, every one of the three re-entries falls **outside** it and its spend is attributed to the still-open `6-finalize` row instead. That row reports 5,837,690 tokens — 57% of the plan's 10.2M total — and is the basis of this retrospective's `max_phase_token_share` finding and of its `dominant_phase` attribution. An unknown share of that figure is loop-back execute work wearing a finalize label.

The accumulate-on-re-entry machinery documented in `manage-metrics/SKILL.md` (per-close active span, provenance-keyed token fields, `value_scope: mixed_cumulative_and_last_close`) is correct and is simply never reached, because nothing closes the re-entered phase.

## Proposed action

1. Have the loop-back transition record a close for the phase it leaves and re-open the phase it enters, so `close_count` reflects re-entry and the re-entered phase's span is attributed to it. `phase-boundary` already implements exactly this and is documented as the canonical path at phase boundaries; a loop-back is a phase boundary.
2. Failing that, make `generate` cross-check `re_entered_phases` against `status.metadata.loop_back_iteration` and report a discrepancy rather than an empty list — an empty `re_entered_phases` beside `loop_back_iteration: 3` is a detectable contradiction between two records the same plan directory already holds.
3. Either way, a phase whose `end_time` precedes a recorded re-entry into that phase should not read as a single closed phase.

## Evidence

- aspect: plan_efficiency — `phase_attribution_caveat` block: `five_execute_close_count: 1` against `recorded_loop_backs_into_5_execute: 3`
- artifact: `work/metrics.toon` `[5-execute]` — `close_count: 1`, `value_scope: single_close`, `end_time: 2026-08-30T02:15:02Z`
- artifact: `status.json` — `metadata.loop_back_iteration: "3"`
- log: `decision.log` lines 136, 154, 162 — three `Loop-back set-phase 6-finalize -> 5-execute` entries
- contract: `manage-metrics/SKILL.md` § generate — "`close_count` is written at the write site, this is the AUTHORITATIVE re-entry signal"
