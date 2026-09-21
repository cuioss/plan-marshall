envelope_version=1
sender_type=plan
sender_id=prompt-standard-and-doctor-rule
epic=operator-ux
kind=candidate-lesson
created=2026-09-02T13:41:34Z

component=plan-marshall:phase-6-finalize
category=improvement
confidence=medium
source_plan=prompt-standard-and-doctor-rule
recurrence_of=none

# [VERIFY] emission is effectively absent across the finalize lane

## Context

The plan's `work.log` carries **one** `[VERIFY]` entry for the whole run, against at least six verification events that demonstrably executed:

- three phase-5 verification steps (`verify:quality-gate`, `verify:module-tests`, `verify:coverage` — all three recorded by `record-step`);
- `pre-push-quality-gate`, `firing_count: 2`;
- `project:finalize-step-plugin-doctor`, `firing_count: 2`;
- `ci-verify`, one firing.

`references/logging-gap-analysis.md` sets `expected_min` for the VERIFY category at 6 and calls `observed / expected_min < 0.5` a warning. Observed here is `0.17`.

By contrast the other categories are healthy or better: `STATUS` 51, `DECISION` 125, `STEP` 44, `SKILL` 34, `DISPATCH` 20, `ARTIFACT` 14, over 329 work entries.

## Root cause

Verification steps record their outcome through `mark-step-done` (`display_detail`) and, for phase-5 steps, through `manage-execution-manifest record-step` — both of which are state writes rather than log emissions. Nothing in the finalize lane emits `[VERIFY]` on a build/gate/doctor run, so the work log has no verification-shaped trail at all.

The gap matters here specifically because verification is the most re-fired work in this lane: `pre-push-quality-gate` and `plugin-doctor` each fired twice, `verify:coverage` was attempted inline, killed at 388s, and re-run at orchestrator tier. Reconstructing that sequence required joining `status.json`, `decision.log`, `execution.toon` and two dispatch-boundary files, because the one log that is meant to narrate it says nothing.

## Proposed action

Emit one `[VERIFY] (plan-marshall:{caller}) {command} -> {verdict}` work-log line at each verification boundary: the phase-5 verification steps, `pre-push-quality-gate`, `ci-verify`, and any project finalize step that runs a gate. Carry the verdict and the re-fire ordinal, so a re-fired gate is legible without opening `status.metadata.phase_steps`.

This is cheap and it is the channel the retrospective's own expected-pattern table already assumes exists.

## Evidence

- aspect: logging_gap_analysis — `VERIFY, expected_min 6, observed 1` (ratio 0.17)
- aspect: log_analysis — `top_tags`: STATUS 51, STEP 44, SKILL 34, DISPATCH 20, ARTIFACT 14; VERIFY absent from the top five
- `status.metadata.phase_steps` — `pre-push-quality-gate` and `project:finalize-step-plugin-doctor` each `firing_count: 2`
- decision `35b0d6` — the `verify:coverage` inline kill and orchestrator-tier re-run, recoverable only from the decision log
