envelope_version=1
sender_type=plan
sender_id=barrier-override-not-head-bound
epic=review-apparatus
kind=candidate-lesson
created=2026-08-02T13:17:55Z

# Finalize [STEP] logging covers 9 of 16 completed steps

component: plan-marshall:phase-6-finalize
category: improvement
confidence: medium

## Context

Sixteen finalize steps reached `outcome=done` in `status.metadata.phase_steps["6-finalize"]`. The work
log carries:

- 9 `[STEP] ... Completed step:` lines
- 5 `[STEP] ... Executing step:` lines

Seven steps completed with no `[STEP]` evidence at all — `architecture-refresh`, `push`,
`project:finalize-step-era-stamp-fill`, `ci-verify`, `automatic-review`,
`project:finalize-step-review-retrospective`, `lessons-capture`, `finalize-step-preference-emitter`. Four
more have a `Completed` line with no paired `Executing` line.

## Root cause

`[STEP]` emission is per-step-handler rather than driven by the step loop, so steps whose handlers do not
emit produce no trace. The pairing (`Executing` then `Completed`) is by convention, not enforced.

## Proposed action

Emit `[STEP] Executing` and `[STEP] Completed` from the finalize step loop itself rather than from each
handler, so coverage is structural. The retrospective's log-analysis aspect can then assert
`executing_count == completed_count == terminal_step_count` as a real invariant instead of counting tags
that may or may not exist.

## Evidence

- aspect: logging_gap_analysis — `phase-6-finalize,STEP` gap; `expected_vs_actual` STEP 32 expected / 14 observed
- aspect: log_analysis — `top_tags` STEP=14 against 16 terminal steps in `phase_steps`
