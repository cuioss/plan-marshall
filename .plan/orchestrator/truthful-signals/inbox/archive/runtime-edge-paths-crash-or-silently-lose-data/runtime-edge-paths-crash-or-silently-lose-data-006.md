envelope_version=1
sender_type=plan
sender_id=runtime-edge-paths-crash-or-silently-lose-data
epic=truthful-signals
kind=candidate-lesson
created=2026-08-09T20:26:09Z

component=plan-marshall:phase-6-finalize
category=bug
confidence=high
source_plan=runtime-edge-paths-crash-or-silently-lose-data
source_aspects=logging_gap_analysis,log_analysis

# Finalize [STEP] Executing/Completed pairing is unguarded and one pair is broken

## Context

`work.log` records finalize steps as an `Executing` / `Completed` pair. In this plan, one pair
is broken:

```
line 429: [2026-08-09T19:57:50Z] [STEP] ... Executing step: project:finalize-step-sync-plugin-cache
line 430: [2026-08-09T20:03:03Z] [STEP] ... Executing step: project:finalize-step-review-retrospective
```

No `Completed step: project:finalize-step-sync-plugin-cache` line was ever written. The step
did complete — `status.metadata.phase_steps["6-finalize"]["project:finalize-step-sync-plugin-cache"]`
records `outcome: done` with `display_detail: "10 bundles synced, on-main executor regenerated"`.
All fifteen other completed finalize steps carry their matching pair.

## Root cause

Nothing checks this class of gap for phase 6. The equivalent guard exists for phase 5 and works:
`analyze-logs.py` emits

```
phase5_logging_gaps:
  outcome_pairing:
    paired: 9
    unpaired_completed[0]:
    unpaired_outcome[0]:
```

pairing `[OUTCOME]` lines against completed tasks, and it came back clean here. The same
pairing engine simply is not applied to the phase-6 `[STEP]` pair, so a step that completes in
state but not in log is invisible.

## Proposed action

Extend `analyze-logs.py`'s existing `outcome_pairing` engine to the phase-6
`[STEP] Executing` / `[STEP] Completed` pair, and cross-check the result against
`status.metadata.phase_steps["6-finalize"]` — a step recorded `done` in state with no
`Completed` line is `unpaired_state_only`, and a `Completed` line with no state record is
`unpaired_log_only`. Both directions matter; this plan exhibits the first.

## Why it matters beyond tidiness

The finalize log is the reconstruction surface for what a plan did after execute. The
retrospective, the audit workflow, and any operator debugging a stuck finalize all read it. A
step that runs, mutates the developer machine (this one synced 10 bundles and regenerated the
on-main executor) and leaves no completion trace is the kind of silent gap that makes a later
"the cache was never synced" investigation start from the wrong premise.

## Evidence

- artifact: `logs/work.log` lines 429-430, and `status.json` `phase_steps` for the same step
- aspect: log_analysis — `phase5_logging_gaps.outcome_pairing` demonstrates the guard exists and passes for phase 5
- aspect: logging_gap_analysis — 15 of 16 completed finalize steps carry the pair
