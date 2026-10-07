envelope_version=1
sender_type=plan
sender_id=finalize-step-records-are-prose-not-facts
epic=truthful-signals
kind=candidate-lesson
created=2026-08-02T12:18:19Z

component=plan-marshall:phase-6-finalize
category=bug
confidence=high
source_plan=finalize-step-records-are-prose-not-facts
source_pr=1076
source_aspects=logging_gap_analysis,execution-context-dispatch-audit

# [STEP] Executing markers are absent for lessons-capture and for head-advance re-fires

## Context

Two concrete marker gaps in this plan's own finalize:

1. `lessons-capture` — `[STEP] Completed step: default:lessons-capture` at 11:41:22Z, with **no** matching `[STEP] Executing step` line. The step definitely ran: `[DISPATCH] ... workflow=plan-marshall:phase-6-finalize/workflow/lessons-capture.md` at 11:34:21Z.
2. `pre-push-quality-gate` re-fire — at 09:49:12Z the dispatcher logged `[STATUS] Re-firing head-dependent pre-push-quality-gate: settle-band commits advanced HEAD f4ecc5205 -> 3e3581b45` and ran the gate again. No `[STEP] Executing` and no `[STEP] Completed` pair was emitted for the re-fire.

Totals: 15 `Executing` markers vs 16 `Completed` markers in phase 6 (31 `STEP` entries total, matching `analyze-logs` `top_tags.STEP=31`).

## Root cause

`[STEP]` emission is hand-placed at the dispatcher's step-entry site rather than being a property of the step-execution primitive, so any path that reaches a step body without traversing that site — a dispatched workflow that logs its own `[DISPATCH]` instead, or a conditional re-fire branch — silently skips the marker.

This is not a new observation. This plan's own `request.md` records it as an OBSERVED claim ("the `Executing step` marker appears 33x for `sync-baseline` but 1x for `sonar-roundtrip` across 39 plans, so **marker absence does not imply the step did not run**") and explicitly deferred it to D0's scope call. D0 scoped it out. It then recurred inside this plan's own finalize run, twice.

## Proposed action

1. Emit the `[STEP] Executing` / `[STEP] Completed` pair from one place that every step-execution path traverses — the same site that already writes the step outcome — so the pair is structural rather than hand-placed.
2. Emit the pair for a re-fire as well, with the iteration or the head SHA on the line, so "how many times did this gate run" is answerable from the log.
3. Add the pairing check to `analyze-logs`: it already pairs phase-5 `[OUTCOME]` lines (`phase5_logging_gaps.outcome_pairing`); extend the same helper to phase-6 `[STEP]` markers and emit `unpaired_executing[]` / `unpaired_completed[]`.

## Evidence

- `logs/work.log` — `[STEP] Completed step: default:lessons-capture` at 11:41:22Z with no preceding `Executing`
- `logs/work.log` — `[DISPATCH]` for lessons-capture at 11:34:21Z (the step ran)
- `logs/work.log` — `[STATUS] Re-firing head-dependent pre-push-quality-gate` at 09:49:12Z with no `[STEP]` pair
- aspect: log_analysis — `top_tags: STEP,31` against 16 completed steps
- `request.md` § "Claim Labels" → the OBSERVED-and-deferred claim this recurrence confirms
