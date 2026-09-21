envelope_version=1
sender_type=plan
sender_id=exit-code-convention-stops-at-the-skill-boundary
epic=review-apparatus
kind=candidate-lesson
created=2026-09-06T19:31:15Z

# A phase loop-back stamps no metrics boundary, so re_entered_phases reports an empty list

component: plan-marshall:plan-marshall
category: bug
confidence: high
source_plan: exit-code-convention-stops-at-the-skill-boundary
source_pr: 1423, 1429

## Context

This run looped back from finalize into execute and re-ran two tasks:

- `13:32:36` — `[MANAGE-STATUS] Phase: 6-finalize -> 5-execute`
- `13:46:53` — `[STATUS] (phase-5-execute) Re-entering execute phase — 2 tasks pending`
- `14:00`–`15:41` — TASK-005 and TASK-006 execute; TASK-005 alone rewrites 134 files
- `15:41:14` — `[OUTCOME] Completed TASK-006`

No `manage-metrics phase-boundary` was stamped for that re-entry. The 5-execute
row still reads:

```toon
[5-execute]
  end_time: 2026-09-05T13:14:10Z
  close_count: 1
  value_scope: single_close
```

and `generate` reports `re_entered_phases[0]:` — an **empty list**.

So roughly two hours of execute work, the single largest edit of the plan, and its
token spend are attributed to `6-finalize` instead. `6-finalize` shows 1,168,241
tokens and becomes the "dominant phase" of the efficiency analysis as a direct
artifact of the missing boundary.

## Root cause

`manage-metrics` has a fully-specified re-entry model — accumulate-on-re-entry,
`close_count`, `value_scope: mixed_cumulative_and_last_close`,
`cumulative_fields` / `last_close_fields` — and its SKILL.md calls `close_count`
"the **authoritative** re-entry signal … written at the write site".

All of that machinery is correct and none of it fired, because it is driven
entirely by a `phase-boundary` / `end-phase` call that the loop-back path does not
make. The status transition (`6-finalize -> 5-execute`) and the metrics boundary
are two independent writes with nothing binding them, so a transition can happen
without its paired stamp — the same half-stamped-boundary class that
`boundary-status` was built to detect on *resume*, occurring here on *loop-back*
where nothing checks for it.

The weaker fallback signal misses it too: `boundary_monotonicity` is also empty,
because it infers re-entry from timestamp ordering and 5-execute has no later
`end_time` to be out of order with.

## Proposed action

1. Stamp a `phase-boundary` on every loop-back transition, not only on forward
   phase advance. The finalize→earlier-phase transition is the known trigger.
2. Reuse the existing detector: call `manage-metrics boundary-status
   --prev-phase {current} --next-phase {target}` before a loop-back transition and
   stamp the missing boundary when it returns `missing`. The verb already exists
   and already classifies exactly this condition — it is simply not consulted on
   this path.
3. Make `re_entered_phases` non-vacuous: when a plan's status history records a
   backward phase transition that no `close_count` reflects, `generate` should
   report that disagreement rather than an empty list. An empty list currently
   means both "no re-entry" and "re-entry that was never stamped".

## Evidence

- `work/metrics.toon` `[5-execute]` — `close_count: 1`, `end_time: 2026-09-05T13:14:10Z`,
  `value_scope: single_close`; store `updated: 2026-09-05T13:14:10Z`
- `manage-metrics generate` — `re_entered_phases[0]:`, `boundary_monotonicity[0]:`
- `work.log` — the four lines quoted above spanning 13:32 to 15:41
- `manage-metrics/SKILL.md` — "`close_count` … this is the **authoritative** re-entry signal"
- `manage-metrics boundary-status` — the existing, unconsulted detector for this exact class
