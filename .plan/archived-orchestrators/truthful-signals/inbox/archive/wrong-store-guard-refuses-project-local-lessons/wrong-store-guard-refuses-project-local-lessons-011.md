envelope_version=1
sender_type=plan
sender_id=wrong-store-guard-refuses-project-local-lessons
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T13:00:00Z

# Log effort resolve-target entries to decision.log

component: plan-marshall:manage-config
category: bug
confidence: medium
source_plan: wrong-store-guard-refuses-project-local-lessons

## Context

The execution-context-dispatch-audit's `shape_violation` detection is defined as pairing a
`decision.log` `(plan-marshall:manage-config) effort resolve-target` entry with a subsequent `[DISPATCH]`
line by matching `role`. This plan's `decision.log` carries ZERO `effort resolve-target` entries for any
role, even for the 3 dispatches (phase-3-outline, phase-4-plan, phase-5-execute) that DID emit a correct,
well-formed `[DISPATCH]` line. The detection's own trigger condition never fires in this plan's build.

## Root cause

Either `manage-config effort resolve-target` does not log its resolution to `decision.log` in the build
this plan ran on, or it logs under a different tag/format the audit's pairing rule does not recognize.
Either way, the `shape_violation` category is structurally unable to detect an unpaired resolve for this
plan (and, by extension, for the codebase generally, since all 3 confirmed-correct dispatches also show
this same absence).

## Proposed action

Confirm whether `effort resolve-target` currently emits a `decision.log` entry at all; if not, add one
(role, phase, resolved target/level) so the shape_violation pairing check has real signal to detect an
unpaired resolve when one occurs.

## Evidence

- aspect: execution-context-dispatch-audit — systemic_note / detection_caveat: 0 `effort resolve-target`
  entries in `decision.log` across all 3 confirmed dispatches in this plan.
