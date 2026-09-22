# PLAN-18: Re-fire cost split and merge-queue proof

epic: quality-aspect
workstream: WS-08

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-18-cost-mergequeue.md` and is queued in the epic `status.json`
> `plans[]` field. The orchestrator EMITS the command below; it never launches the
> plan inline. This spec is SELF-SUFFICIENT.

## Objective

Attribute the finalize lane's dominant cost and prove merge-queue membership:
productive vs unproductive re-fire separated, auto-fix churn out of the declared
footprint accounting, enqueue proving PR membership, derivation comments checked
against code. G24 remainder + G28 (4 lessons).

## Deliverables

1. Productive vs unproductive re-fire separation with round budget (2026-09-13-12-002).
2. Quality-gate auto-fix churn in realized-footprint accounting (2026-09-18-20-004).
3. Merge-queue enqueue proving PR membership (2026-09-13-12-001).
4. Derivation-source comments verified against adjacent code (2026-09-14-05-005).

## Claim Labels

- OBSERVED: finalize re-firing dominates plan cost at 53% of all tokens — read at `lessons-archive/2026-09-13-12-002.md` (title triage; body verified at outline).
- OBSERVED: green PR sat through two merge-queue windows merging nothing — read at `lessons-archive/2026-09-13-12-001.md` § Context.
- HYPOTHESIS: re-fire split plus membership proof bounds the dominant cost line — confirm/refute at `marketplace/bundles/plan-marshall/skills/tools-integration-ci/` § merge-queue enqueue (verify-at-outline).

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/` — re-fire accounting, auto-fix churn.
- OBSERVED: `marketplace/bundles/plan-marshall/skills/tools-integration-ci/` — merge-queue enqueue.

## Dependencies and Sequencing

- Depends on: PLAN-17 (round semantics its cost split reads).
- Overlaps with: PLAN-17 — sequenced after it.
- Adjacent to: none.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/quality-aspect/plans/PLAN-18-cost-mergequeue.md"
```

## Write-Boundary

The plan touches only its own repository source and tests. It creates and edits NO
file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}`
message, and reports its outcome through its PR and its inbox message.
