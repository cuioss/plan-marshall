envelope_version=1
sender_type=plan
sender_id=cloud-lane-build-gate-reads-one-field-short
epic=truthful-signals
kind=candidate-lesson
created=2026-08-23T22:09:05Z

component=plan-marshall:phase-6-finalize
category=bug
confidence=high
source_plan=cloud-lane-build-gate-reads-one-field-short
source_aspects=logging_gap_analysis,execution_context_dispatch_audit

# A re-fired finalize step emits Completed without Executing, inflating completion counts

## Context

In this plan's `6-finalize`, at least four steps emitted a second
`[STEP] (plan-marshall:phase-6-finalize) Completed step: X` line with no paired
`[STEP] ... Executing step: X` before it:

| Step | Executing | Completed | Second Completed |
|---|---|---|---|
| create-pr | 19:18:03 | 19:22:15 | 19:22:52 |
| pre-push-quality-gate | (earlier) | 19:16:59 | 20:29:32 |
| automatic-review | 19:43:49 | 19:50:57 | 20:29:55 |
| ci-verify | 19:24:23 | 19:43:25 | 20:47:19 |

The re-fires are legitimate — `pre-push-quality-gate` re-fired per its head-dependent contract
after HEAD advanced by four commits, and `status.json` records `firing_count: 3` for it. What is
defective is the instrumentation: the bracket is closed without being opened.

## Root cause

The re-fire path emits the completion log line but not the entry line. `status.json` models
re-firing correctly (`prior_firings[]`, `firing_count`), so the state store knows; only the work
log does not.

## Proposed action

Emit the `Executing step` line on every firing, not only the first — or, if the re-fire path is
deliberately quiet on entry, emit a distinct `Re-firing step: X` marker so the bracket is
balanced and re-fires stay countable.

## Evidence

- aspect: logging_gap_analysis — 4 unpaired completion lines enumerated with timestamps
- `status.json` `phase_steps["6-finalize"]`: `pre-push-quality-gate.firing_count: 3`,
  `automatic-review.firing_count: 2`, `ci-verify.firing_count: 2`, `create-pr.firing_count: 2`
