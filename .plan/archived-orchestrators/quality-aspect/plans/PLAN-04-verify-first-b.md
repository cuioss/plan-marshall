# PLAN-04: Verdict admission and context-load plumbing

epic: quality-aspect
workstream: WS-02

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-04-verify-first-b.md` and is queued in the epic `status.json`
> `plans[]` field. The orchestrator EMITS the command below; it never launches the
> plan inline. This spec is SELF-SUFFICIENT.

## Objective

Close the absent-read-as-passing admission holes and plumb the context-load measure
into every call site: no silent absent-verdict pass,
forwarded dispatch columns, checkable closure arithmetic. G02 second half (11 lessons).

## Deliverables

1. Fallback tool for unsweepable lint roots (2026-09-04-17-012).
2. Cross-round defect recurrence detection in self-review (2026-09-04-17-014).
3. Residual-text classification of review_body actionability (2026-09-06-07-001).
4. Population-published signal-gate counts (2026-09-06-08-002).
5. Symmetric-pair comparison within one edit (2026-09-06-08-003).
6. Loop-back re-arm on out-of-band override (2026-09-06-10-001).
7. Could-not-look reporting in assert_test_identifiers (2026-09-07-13-003).
8. Checkable closure arithmetic or no closure claim (2026-09-07-13-007).
9. Absent-verdict admission closed in phase-5-execute (2026-09-07-13-008).
10. Dispatch context-load flags passed at every call site (2026-09-07-13-009).
11. Context-load column forwarding at record-dispatch-boundary (2026-09-08-13-006).

(Retired 2026-09-19: verdict_inputs surface for step currency — the
verdict-currency classifier with opt-in per-step verdict_inputs declarations
exists at phase-6-finalize/scripts/verdict_currency.py and the ext-point
frontmatter; verified in-tree before retiring. Absent-verdict admission stays:
the Re-Grounding Verdict Field admission table is related machinery, not the
phase-5 read path this deliverable closes.)

## Claim Labels

- OBSERVED: two phase-5-execute paths read an absent verdict as passing — read at `lessons-archive/2026-09-07-13-008.md` (title triage; body verified at outline).
- OBSERVED: four dispatch flags optional with zero callers, measure dark — read at `lessons-archive/2026-09-07-13-009.md` (title triage; body verified at outline).
- HYPOTHESIS: closed absent-verdict admission plus mandatory flag forwarding closes both — confirm/refute at `marketplace/bundles/plan-marshall/skills/phase-5-execute/` § verdict admission (verify-at-outline).

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-5-execute/` — verdict admission, dispatch boundary.
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/` — loop-back re-arm.

## Dependencies and Sequencing

- Depends on: PLAN-03 (verification rules it admits on).
- Overlaps with: PLAN-03, PLAN-17 — strictly sequenced after PLAN-03.
- Adjacent to: none.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/quality-aspect/plans/PLAN-04-verify-first-b.md"
```

## Write-Boundary

The plan touches only its own repository source and tests. It creates and edits NO
file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}`
message, and reports its outcome through its PR and its inbox message.
