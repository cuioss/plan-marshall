# PLAN-07: Footprint capture and declaration containment

epic: quality-aspect
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-07-footprint-surface.md` and is queued in the epic `status.json`
> `plans[]` field. The orchestrator EMITS the command below; it never launches the
> plan inline. This spec is SELF-SUFFICIENT.

## Objective

Diff the realized footprint against the right base with honest declarations:
creation-SHA bookkeeping, one shared containment rule, unevaluated states reported
as such, surfacing against origin/main. G01 + G26 + G30 (8 lessons).

## Deliverables

1. Footprint diffs against upstream base, not local main (2026-08-25-09-010).
2. plan_creation_sha in references.json for scope_creep_check (2026-09-04-14-007).
3. Retired references keys unlinked from step inputs (2026-09-07-13-004).
4. Mechanical-sweep sizing on realized single-run throughput (2026-09-03-07-004).
5. Shared containment rule for twin declaration comparisons (2026-09-13-12-013).
6. Classified unevaluated state, never row-builder default (2026-09-13-12-014).
7. Self-review surfacing against origin/main with behind-upstream fail-loud (2026-09-07-15-002).
8. Hoisted-binding shadowing check in surfacing scope (2026-09-03-07-006).

(Retired 2026-09-19: realized-footprint capture at branch-cleanup — the
capture-footprint verb persisting realized_footprint, called by branch-cleanup
before worktree removal, is documented at manage-references/SKILL.md and
implemented in scripts/_cmd_compute_footprint.py; verified in-tree before
retiring.)

## Claim Labels

- OBSERVED: five footprint consumers inconclusive for lack of a captured realized footprint — read at `lessons-archive/2026-08-25-09-001.md` § Context.
- OBSERVED: stale local main inflated the review surface 64x with 76 phantom files; recurrence confirmed next day — read at `lessons-archive/2026-09-07-15-002.md` § Context + Recurrence; corroborated at `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/_self_review_diff.py` § merge-base on bare base_branch.
- HYPOTHESIS: upstream-base resolution plus creation-SHA bookkeeping plus one containment rule closes all three — confirm/refute at `marketplace/bundles/plan-marshall/skills/manage-references/scripts/` § resolve_base_ref (verify-at-outline).

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-references/` — footprint capture, references keys.
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/` — corpus surfaces, containment.
- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/` — surfacer base ref.

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: none (disjoint from PLAN-08 git surfaces).
- Adjacent to: WS-06/PLAN-10 absorb mechanics read the captured footprint.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/quality-aspect/plans/PLAN-07-footprint-surface.md"
```

## Write-Boundary

The plan touches only its own repository source and tests. It creates and edits NO
file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}`
message, and reports its outcome through its PR and its inbox message.
