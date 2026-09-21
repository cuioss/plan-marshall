envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-09-04-01
epic=truthful-signals
kind=candidate-lesson
created=2026-09-15T13:46:50Z

component=plan-marshall:plan-marshall
category=bug

# Light planning lane never sets pr_title, so the 2-refine handshake capture refuses with pr_title_missing

Relayed from Token-Sheriff epic `lessons-handling-26-09-04-01`, drain of plan
`lessons-handling-epic-residual-cleanup` (PR cuioss/TokenSheriff#744, 2026-09-15), inbox message
`lessons-handling-epic-residual-cleanup-001.md`. The orchestrator confirmed the cited log entry
exists in the archived plan before relaying.

## Observation

With `planning_lane=light`, the plan runs one collapsed refine+outline+derive envelope and never
reaches `phase-2-refine` Step 13, the only producer of `status.metadata.pr_title`. The 2-refine
`phase_handshake capture` then refuses with `pr_title_missing`. The executing orchestrator had to
set `pr_title` through `manage-status metadata --set` and re-run capture.

Evidence (archived plan `2026-09-15-lessons-handling-epic-residual-cleanup`): decision.log
`5f9d50` (2026-09-15T09:27:31Z, WARNING) "light-lane 2-refine capture refused with
pr_title_missing (light lane never runs phase-2-refine Step 13)"; work.log `9eee57` records the
manual metadata set.

## Why it matters

This is deterministic: every light-lane plan hits it. A handshake invariant that the lane it
guards can never satisfy is a false-RED gate, and the only way past it is a hand-authored value.

## Candidate direction

Either the light-lane envelope derives and persists `pr_title` with Step 13's derivation, or the
2-refine handshake invariant becomes lane-aware. Check `plan-marshall:plan-marshall`
`workflow/planning.md` (light-lane branch) against the `pr_title_missing` invariant in the
phase-handshake capture.
