envelope_version=1
sender_type=plan
sender_id=verdict-field-read-and-write-integrity
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-26T19:20:51Z

component=plan-marshall:phase-6-finalize
category=bug
confidence=high
source_plan=verdict-field-read-and-write-integrity
source_pr=1355

# Emit a DISPATCH line when a finalize step re-dispatches inside itself

## Context

`pre-submission-self-review` ran **seven** full-surface rounds during this plan's finalize (corroborated by the session transcript, which puts the loop at ~1.3M tokens before round 7 was authorized). Against those seven rounds the plan's instrumentation recorded:

- **2** `[DISPATCH]` lines in `work.log` (12:23:46Z, 12:39:26Z)
- **2** `effort resolve-target` records in `decision.log` (the same two timestamps)
- **2** dispatch-boundary rows (201,856 error + 103,570)
- **6** `(plan-marshall:execution-context.pre-submission-self-review) Complete` envelope-completion lines
- **3** `[STEP] ... Completed step:` terminal writes (`failed`, `done`, `done`; `firing_count: 3`)

At the phase level, `6-finalize` records `total_tokens: 2448626` against `dispatch_boundary_total: 1555736` — **892,890 tokens, 36% of the phase, carried by no boundary row at all.** 6-finalize is 52% of the whole plan's spend, so the phase with the largest cost is the phase with the least complete measurement.

## Root cause

All three instrumentation channels — the `[DISPATCH]` work-log line, the `effort resolve-target` decision record, and the `record-dispatch-boundary` row — hang off **step entry**. A step that re-dispatches its own envelope after it has already been entered (a head-dependent re-fire, a loop-back retry, an iterate-until-clean review round) passes through none of the three seams again. They are meant to be independent evidence sources, but they share one blind spot because they share one trigger.

## Proposed action

Move the `[DISPATCH]` emission (and the paired boundary-row registration) from the step-entry path to the seam that actually opens the envelope, so a re-dispatch inside an already-entered step is instrumented exactly like a first dispatch. Two corroborating observations that should shape the fix:

1. The envelope's own completion marker — `(plan-marshall:execution-context.{name}) Complete`, emitted by every leaf's Step 6 — **did** observe 6 of the 7 rounds. It is the only channel that saw the re-dispatches, and it is a completion witness, not a dispatch witness, so it cannot substitute for the fix.
2. Even that channel under-counted by one round. No channel inside the plan directory can reproduce the true round count; only the session transcript can. Any fix should be validated against a step known to re-fire, not against a single-firing step.

## Evidence

- aspect: logging_gap_analysis — `dispatch_emission_on_redispatch`: 16 finalize envelopes, 12 finalize-caller `[DISPATCH]` lines, 12 boundary rows
- aspect: log_analysis — `6-finalize` dispatch_boundaries: 12 rows recorded; largest is 224,577, so no row carries the 1,198,535-token self-review record-step figure
- aspect: plan_efficiency — `boundary_ledger_coverage.6-finalize_uncovered_tokens: 892890` (0.36 of the phase)
- aspect: chat_history_analysis — operator gate text: "re-fires the head-dependent self-review for a 7th full round (~200K tokens, ~9 min). The loop has cost ~1.3M tokens so far."
- `.plan/local/plans/verdict-field-read-and-write-integrity/work/metrics.toon` — `[6-finalize] total_tokens: 2448626`, `dispatch_boundary_total: 1555736`
