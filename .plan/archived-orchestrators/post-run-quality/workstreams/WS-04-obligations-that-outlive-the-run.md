# WS-04: Obligations that outlive the run

epic: post-run-quality

> Charter document for one workstream. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the tier contract.

## Charter

A finalize run routinely ends with something still owed — a deferred daemon reconcile, an unissued
`architecture enrich insight` call, a step whose configured lane says it should not have run. Today those
obligations are recorded in prose by whoever noticed, and the plan that owed them is archived minutes
later. This workstream gives a post-run obligation a typed carrier and a tracker that outlives its plan.
It closes when an owed item is machine-readable at the landing and re-checkable afterwards.

## Scope

- In scope: the post-run obligation record itself (where an owed item is written and by whom), the
  landing payload's carriage of it, the deferred-reconcile marker, the archived-plan hand-off, and the
  config-versus-run divergence that lets a step configured `off` report `done`.
- Out of scope: the content of any individual obligation (the architecture store is the operator's, and
  the orchestrator does not mutate it); the retrospective producers (WS-01); reviewer participation
  state, which is `review-apparatus`'s — named here only where it crosses this seam.

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-PRQ-04-an-obligation-that-outlives-its-plan-has-no-owner | staged | The owed-item carrier, plus the `lane: off` step that reported `done` and the reviewer-state handoff that fails closed |

## Sequencing and Surface Notes

- ⛔ **PLAN-PRQ-04 D0 must settle the `lane: "off"` question BEFORE anything else in it is scoped**, because
  the two readings imply different fixes in different components: either lane resolution does not drop a
  non-ceremony step at `off` (a `manage-execution-manifest` defect), or the landing's step list is not
  derived from the composed manifest (a `phase-6-finalize` / landing-payload defect).
- Declares `manage-execution-manifest/**` and `phase-6-finalize/**`, which several `truthful-signals`
  specs also declare (`-145`, `-147`, `-158`). Cross-epic, therefore **invisible to both gates** — recorded
  here and in the spec.
- The reviewer-state handoff (`bot_states` not persisted where an `order: 990` step can read it) sits on
  the `review-apparatus` boundary: PRQ-04 names the seam and the consumer's fail-closed behaviour; the
  reviewer-side producer change is theirs to make.
