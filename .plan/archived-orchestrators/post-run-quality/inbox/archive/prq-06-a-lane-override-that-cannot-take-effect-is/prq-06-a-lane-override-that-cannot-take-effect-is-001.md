envelope_version=1
sender_type=plan
sender_id=prq-06-a-lane-override-that-cannot-take-effect-is
epic=post-run-quality
kind=candidate-lesson
created=2026-09-19T18:37:16Z

component=plan-marshall:manage-execution-manifest
category=bug
confidence=high
source_plan=prq-06-a-lane-override-that-cannot-take-effect-is
source_aspects=manifest_decisions,routing_decisions

# Orchestration detection fails open and silently drops emit-landing

## Context

PLAN-PRQ-06 was launched from the epic spec `.plan/local/orchestrator/post-run-quality/plans/PLAN-PRQ-06-a-lane-override-that-cannot-take-effect-is-accepted-and-reported-set.md` — its `request.md` `hand-off_command` section records exactly that path. At manifest-compose time the composer logged:

```
[STATUS] terminal_emission_orchestration_gate — dropped emit-landing from
phase_6.steps: plan is not orchestrated (detection=not_orchestrator_pointer);
no epic inbox to write a landing to
```

`emit-landing` was consequently absent from the composed `phase_6.steps` (22 steps) while remaining in `candidate_steps` (26). The plan ran to a clean merge (PR #1541, `a1dd4901f`) and epic `post-run-quality` received no landing message for it.

The detection is recoverable and the answer is unambiguous: `orchestrator inbox detect --source-id ".plan/local/orchestrator/post-run-quality/plans/PLAN-PRQ-06-....md"` returns `orchestrated: true, epic: post-run-quality, detection: orchestrated`.

## Root cause

The documented two-call resolution seam is `manage-plan-documents request read --section source_id` followed by `orchestrator inbox detect --source-id {value}`. On this plan the first call fails outright:

```
status: error
error: section_not_found
section: source_id
available_sections[15]: _header, original_input, provenance, ..., plan_id, source, created
```

`phase-1-init` wrote no `source_id` section. The detector then receives something that is not a spec-path pointer and answers a confident `orchestrated: false` rather than an indeterminate. A could-not-look outcome is being reported as a clean negative, and a terminal step is dropped on the strength of it.

## Proposed action

Two independent fixes, both cheap:

1. Make `phase-1-init` write `source_id` into `request.md` whenever the launch task names a plan-spec path — the seam's first call must not be able to return `section_not_found` on an orchestrated plan.
2. Make the gate fail closed. When the `source_id` read fails or the detector cannot classify, the composer must emit `detection: indeterminate` and KEEP `emit-landing` (a spurious landing is recoverable; a missing one is not), rather than treating an unreadable input as proof of non-orchestration.

Optionally add a `--plan-id` form to `orchestrator inbox detect` that recovers the spec pointer from the plan's own `hand-off_command`, so callers stop re-deriving it from prose.

## Evidence

- aspect: manifest_decisions — decision-log entry `[2026-09-18T11:06:37Z] [7f9799] terminal_emission_orchestration_gate — dropped emit-landing ... (detection=not_orchestrator_pointer)`
- aspect: routing_decisions — `emit-landing` present in `candidate_steps[26]`, absent from `phase_6.steps[22]`
- live re-check — same detect verb, spec path as `--source-id`: `orchestrated: true, epic: post-run-quality`
- `manage-plan-documents request read --section source_id` → `section_not_found` over 15 available sections
