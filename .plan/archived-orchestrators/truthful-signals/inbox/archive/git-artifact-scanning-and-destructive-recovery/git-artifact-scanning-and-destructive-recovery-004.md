envelope_version=1
sender_type=plan
sender_id=git-artifact-scanning-and-destructive-recovery
epic=truthful-signals
kind=candidate-lesson
created=2026-08-31T08:03:23Z

component=plan-marshall:phase-3-outline
category=improvement
created=2026-08-31
bundle=plan-marshall
confidence=high
source_plan=git-artifact-scanning-and-destructive-recovery

# Intersect each deliverable's declared file surface with the plan's own out-of-scope boundary

## Context

Deliverable 7 ("Publish the exempted half of the layer-D filter, and make every dispatch site emit") declared 19 write-replace files and realized 11 — 57.9%, the only partial deliverable in a nine-deliverable plan. Every other deliverable came in at 100% of its modification-intent surface.

The eight unrealized files are:

- `marshall-steward/references/wizard-flow.md`
- `persona-plan-orchestrator/standards/orchestration-model.md`
- `phase-5-execute/SKILL.md`
- `phase-6-finalize/SKILL.md`
- `phase-6-finalize/standards/dispatch-inline-split.md`
- `phase-6-finalize/workflow/adr-propose.md`
- `phase-6-finalize/workflow/lessons-capture.md`
- `workflow-pr-doctor/SKILL.md`

Six of the eight live under `phase-6-finalize/` or are finalize machinery that this plan's OWN "Out of scope" boundary reserved for a sibling plan in the same epic. The plan repeatedly and correctly declined to edit them at execute time and at triage time — each declination was recorded with the boundary as its stated reason (see findings `1d50df`, `3102a0`, `cbd010`, `a7d7af`, `ec87de`).

So the deliverable was **born partial at outline time**. It was declared over a surface the plan was never permitted to touch.

## Root cause

The outline phase composes a deliverable's declared file surface from the change's logical extent, and separately records an "Out of scope" boundary. Nothing intersects the two. A deliverable can therefore declare files the same document forbids, and the contradiction is invisible until the coverage measurement at finalize reports a shortfall that is really an outline error.

The downstream cost is measurement noise, not just an unrealized file: `affected_files_recall` reported 70.4%, `artifact-consistency` reported `missing[8]`, and `outline-vs-shipped` reported `touched_but_unassessed: 21/21`. All three are measuring an outline error and presenting it as an execution shortfall.

## Proposed action

At outline validation (and again at the outline Q-gate), intersect each deliverable's declared modification-intent bullets against the plan's declared out-of-scope paths. A non-empty intersection is a hard finding, with two admissible resolutions:

- **Re-scope the deliverable** to the files the plan may touch, and record the remainder as an explicit hand-off to the named sibling plan; or
- **Widen the boundary**, if the sibling assignment was wrong.

Silently declaring both is the state to remove — it guarantees a partial deliverable and then reports it as if execution had fallen short.

## Evidence

- aspect: request_result_alignment — D7 partial at 11/19; every other deliverable at 100%
- aspect: artifact_consistency — `affected_files_recall` 70.4%, `missing[8]` reached independently and matching D7's misses exactly
- Findings `1d50df`, `3102a0`, `cbd010`, `a7d7af`, `ec87de` — five separate declinations, each citing the Out of scope boundary as the reason
