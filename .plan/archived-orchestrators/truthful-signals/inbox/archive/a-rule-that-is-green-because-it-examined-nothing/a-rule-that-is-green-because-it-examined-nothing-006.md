envelope_version=1
sender_type=plan
sender_id=a-rule-that-is-green-because-it-examined-nothing
epic=truthful-signals
kind=candidate-lesson
created=2026-08-08T18:41:19Z

component=plan-marshall:manage-execution-manifest
category=bug
title=Manifest compose gated a plan-level step on one deliverable's change_type
confidence=medium
source_plan=a-rule-that-is-green-because-it-examined-nothing

# Manifest compose gated a plan-level step on one deliverable's change_type

## Context

`manage-execution-manifest compose` logged, at 13:29:06:

```
finalize-step-simplify omitted — change_type=verification affected_files_count=5
```

and a companion line:

```
lane_resolution warning — finalize-step-simplify: ceremony pre-filter (change_type/affected_files gate)
removed this operator-selected step — the lane did not drop it
```

But this plan's `change_type` is **`enhancement`**, not `verification`. It was classified as `enhancement` at 12:53:41 (`decision.log` 4918c5, *"Change type: enhancement (confidence 75)"*) and persisted to `status.metadata.change_type`, where it still reads `enhancement`.

The only `verification` in the plan is **deliverable 1's own metadata** (`### 1. Re-assert the zero arch-rule population as an execution-time gate` → `change_type: verification`). Deliverables 2, 3 and 4 are all `enhancement`.

## Root cause

The evidence supports — but does not by itself prove — that the ceremony pre-filter read a per-deliverable `change_type` rather than the plan-level one, and that it picked deliverable 1 (the first, and the only `verification` one). A plan-level gating decision was made on a value scoped to one of four deliverables, and the log line then states that value as though it were the plan's.

Whichever mechanism produced it, the observable defect is firm: the composer's own log asserts `change_type=verification` for a plan whose recorded `change_type` is `enhancement`, and it dropped an operator-selected finalize step on that basis. The second log line shows the system already knows this drop is unusual enough to warrant a warning — it just attributes it to the pre-filter rather than questioning the input.

## Proposed action

- Confirm which `change_type` the ceremony pre-filter reads (plan-level `status.metadata.change_type` vs a deliverable's metadata). If it reads a deliverable's, change it to the plan-level value.
- Have the pre-filter log line name its **source** as well as its value (e.g. `change_type=verification (source: deliverable 1 metadata)`), so a value that disagrees with `status.metadata` is visible at the point of decision rather than only to a later cross-check.
- Add a consistency assertion: when the value used for a plan-level gate differs from `status.metadata.change_type`, emit a warning naming both.

## Evidence

- aspect: manifest-decisions — `decision.log` e422ab (`change_type=verification`) and 0cb6d9 (the pre-filter warning)
- aspect: routing-decisions — `mis_prune:finalize-step-simplify` recorded as `skip` with `removal_cause: simplify_inactive`, so the prune predicate was never evaluated either
- source: `status.metadata.change_type: enhancement`; `decision.log` 4918c5; `solution_outline.md` deliverable 1 metadata `change_type: verification`
