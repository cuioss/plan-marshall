# PLAN-09: Outline sweep declarations that execution can satisfy

epic: quality-aspect
workstream: WS-05

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-09-outline-sweep.md` and is queued in the epic `status.json`
> `plans[]` field. The orchestrator EMITS the command below; it never launches the
> plan inline. This spec is SELF-SUFFICIENT.

## Objective

Give tree-wide sweeps a declaration form execution can hold: assessment coverage
over every declared path, re-assessment on scope change, criteria operationalizable
from the outline, explicit upper bounds for decline-on-merits. G21 (12 lessons).

## Deliverables

1. Sweep declaration form satisfiable by execution (2026-09-04-17-003).
2. Component-assessment re-run on outline scope addition (2026-09-03-06-007).
3. Per-file assessments for downstream consumers (2026-09-03-07-002).
4. Success criteria operationalizable from the outline alone (2026-09-03-07-005).
5. De-citing review trigger for stale shielded claims (2026-09-07-15-008).
6. Q-gate outline gaps vs refine tension recorded (2026-09-11-19-002).
7. Affected-files synced with Change-per-file promises (2026-09-12-17-002).
8. Assessment coverage over read-intent paths included (2026-09-13-12-006).
9. Deliverable module derived from architecture inventory (2026-09-13-12-007).
10. Member-by-member checks for uniform-shape instructions (2026-09-13-12-008).
11. Title/summary counts re-derived from the request (2026-09-13-12-009).
12. Decline-on-merits mutation list as explicit upper bound (2026-09-14-05-002).

## Claim Labels

- OBSERVED: two tree-wide sweeps declared enumerated snapshots; execution reached 300 files beyond — read at `lessons-archive/2026-09-04-17-003.md` § Context.
- OBSERVED: outline scope addition never re-ran component assessment — read at `lessons-archive/2026-09-03-06-007.md` (title triage; body verified at outline).
- HYPOTHESIS: declaration forms with coverage rules plus re-assessment gates hold sweeps — confirm/refute at `marketplace/bundles/plan-marshall/skills/phase-3-outline/` § scope/assessment (verify-at-outline).

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-3-outline/` — assessment, declarations.

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: none.
- Adjacent to: WS-06 consumes outline declarations without touching them.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/quality-aspect/plans/PLAN-09-outline-sweep.md"
```

## Write-Boundary

The plan touches only its own repository source and tests. It creates and edits NO
file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}`
message, and reports its outcome through its PR and its inbox message.
