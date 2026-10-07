# WS-08: Finalize Accounting & Loop-Back

epic: quality-aspect

> Charter document for one workstream — a coherent slice of the epic with its own goal
> and surface. Lives at `workstreams/WS-08-quality-aspect.md` and is tracked in the epic
> `status.json` `workstreams[]` field.

## Charter

Owns finalize-lane cost and correctness accounting: [VERIFY] emission present,
passage re-review, archive-plan receipts, re-fire cost separated into productive
vs unproductive, merge-queue proof of membership. Closed
when a finalize run's dominant cost line is measured, bounded, and attributed.

## Scope

- In scope: phase-6-finalize VERIFY emission, passage re-review, archive-plan
  receipt, mutates_source reconciliation, re-fire measurement, auto-fix footprint churn, merge-queue enqueue proof.
- Out of scope: verify-first admission rules (WS-02), reviewer yield (WS-03).

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-17-finalize-self-review | staged | VERIFY emission, passage re-review, archive receipt, mutates_source |
| PLAN-18-cost-mergequeue | staged | Re-fire cost split, auto-fix churn, merge-queue membership, derivation comments |

## Sequencing and Surface Notes

- PLAN-17 and PLAN-18 both touch phase-6-finalize; sequenced, PLAN-17 first
  (round semantics precede the cost accounting that reads them).
- Sequences after WS-01/PLAN-01 (reads its ledger-join changes).
