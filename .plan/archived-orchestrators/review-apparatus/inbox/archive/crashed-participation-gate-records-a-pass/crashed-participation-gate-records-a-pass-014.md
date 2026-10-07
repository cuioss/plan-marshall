envelope_version=1
sender_type=plan
sender_id=crashed-participation-gate-records-a-pass
epic=review-apparatus
kind=candidate-lesson
created=2026-08-01T19:36:41Z

# Emit [DISPATCH] on re-fired and project-local dispatched finalize steps

component: plan-marshall:phase-6-finalize
category: improvement
confidence: high
source: plan-retrospective (aspect: execution-context-dispatch-audit)
suggested_epic: truthful-signals

## Context

Three envelope runs in this plan left no `[DISPATCH]` work-log line, while demonstrably having run inside an `execution-context` envelope (each is proved by its own `[SKILL] (plan-marshall:execution-context.{role}) Loaded ...` line):

1. `automatic-review` trigger-B re-fire at 17:45:58 (re-review iteration 2 after the loop-back HEAD advance). The only automatic-review `[DISPATCH]` in the run is the 16:01:51 first fire.
2. The second `verification-feedback` / `wait-region-unified-triage` at 18:04:37. The only one is the 16:09:02 first fire.
3. `project:finalize-step-review-retrospective` at 18:57:54, which reached `outcome=done` with no `[DISPATCH]` line at any point.

## Root cause

The emission is attached to the first-fire path only. Two distinct gaps share the symptom:

- **Re-fire path**: a step re-fired after a loop-back re-enters its dispatch without re-emitting. Note the asymmetry — INLINE steps re-fired after the loop-back DID log correctly (`[STEP] Re-fired default:pre-push-quality-gate ...` at 16:55:29, `[STEP] Re-fired default:push ...` at 17:12:52). So the re-fire path is instrumented for inline steps and not for dispatched ones.
- **Project-local wrapper path**: `project:finalize-step-review-retrospective` never emitted even on its first and only fire, suggesting project-local (`project:`) finalize-step wrappers do not go through the emitting dispatch site at all. Whether the other `project:` steps in this plan (`lessons-housekeeping`, `plugin-doctor`, `era-stamp-fill`) share this is only partly answerable — `plugin-doctor` DID emit at 15:00:21, so the gap is not uniform across `project:` steps and needs a real sweep, not an inference from this one case.

## Why it matters

`plan-retrospective/standards/execution-context-dispatch-audit.md` uses `[DISPATCH]` presence as the evidence for BOTH audit directions. A missing emission makes a compliant dispatch look like a `dispatch_coverage_violation` (inline-where-dispatch-required). The audit's inverse-coverage direction is therefore only as trustworthy as the emission coverage — and right now a green inverse-coverage result partly reflects missing evidence rather than confirmed compliance.

## Proposed action

1. Move the `[DISPATCH]` emission to the single dispatch site so re-fires and `project:`-prefixed wrappers cannot bypass it, rather than adding a second emit call at each known-missing site.
2. Sweep the `project:` finalize-step wrapper path to establish which of them emit — `plugin-doctor` does, `review-retrospective` does not, and the discriminator is not yet established.

## Evidence

- aspect: execution-context-dispatch-audit — 3 `shape_violation` findings, 16 `[DISPATCH]` lines observed, all with `target=execution-context-level-{3,5}` (zero envelope or generic-subagent violations)
- `logs/work.log:384, 392, 395` — the three `execution-context.{role}` SKILL lines with no paired `[DISPATCH]`
- `logs/work.log:359, 377` — the two correctly-logged inline `[STEP] Re-fired` lines, establishing the asymmetry
