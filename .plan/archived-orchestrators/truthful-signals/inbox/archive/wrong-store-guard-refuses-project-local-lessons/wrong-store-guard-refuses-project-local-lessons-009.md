envelope_version=1
sender_type=plan
sender_id=wrong-store-guard-refuses-project-local-lessons
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T12:59:59Z

# Emit [DISPATCH] lines for phase-6-finalize dispatched steps

component: plan-marshall:phase-6-finalize
category: bug
confidence: high
source_plan: wrong-store-guard-refuses-project-local-lessons

## Context

`standards/dispatch-inline-split.md` classifies 9 of this plan's phase-6-finalize steps as DISPATCHED
(project:finalize-step-plugin-doctor, pre-submission-self-review, finalize-step-simplify,
architecture-refresh, create-pr, automatic-review, project:finalize-step-review-retrospective,
lessons-capture, project:finalize-step-lessons-housekeeping). All 9 reached `outcome=done` in
`status.metadata.phase_steps["6-finalize"]`. Yet `logs/work.log` carries ZERO `[DISPATCH]
(plan-marshall:...) target=execution-context...` lines anywhere in the phase-6-finalize portion of the run
— the only 3 `[DISPATCH]` lines in this plan's entire history cover phase-3-outline, phase-4-plan, and
phase-5-execute. 5 of the 9 steps DO carry a self-emitted
`[STATUS] (plan-marshall:execution-context.{step}) Complete` marker proving the envelope actually ran, so
only the CALLER-side `[DISPATCH]` emission (owned by the phase-6-finalize dispatcher itself, per
`dispatch-logging.md`) is missing — 3 steps (plugin-doctor, create-pr, automatic-review) carry neither
marker.

## Root cause

The phase-6-finalize dispatcher's Execute Step Pipeline DISPATCHED-step dispatch branch does not emit the
standardized `[DISPATCH]` work-log line before spawning the `execution-context-{level}` envelope, unlike
the phase-3/4/5 dispatch call sites which do emit it correctly. This is a caller-side instrumentation gap,
not an envelope-routing defect (the envelopes with a completion marker prove they rode the canonical
envelope correctly).

## Proposed action

Add the `[DISPATCH]` emission (per `dispatch-logging.md` § Emission contract) to the phase-6-finalize
dispatcher's Execute Step Pipeline DISPATCHED-step branch, immediately before the `Task:
execution-context-{level}` call, mirroring the phase-3/4/5 call sites.

## Evidence

- aspect: execution-context-dispatch-audit — 9 `dispatch_coverage_violation` findings, one per
  DISPATCHED step reaching terminal `outcome=done` with zero matching `[DISPATCH]` work-log evidence.
