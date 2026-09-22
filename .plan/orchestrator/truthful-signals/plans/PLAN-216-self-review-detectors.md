# PLAN-13: Self-review detectors and finding closure

epic: truthful-signals
workstream: WS-07

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-13-self-review-detectors.md` and is queued in the epic
> `status.json` `plans[]` field. The orchestrator EMITS the command below; it never
> launches the plan inline. This spec is SELF-SUFFICIENT.

## Objective

See every user-facing site and close every finding: docstring/adoc detectors,
mirrored-table classes, plugin-doctor precision, prompt validation before dispatch,
terminal states with owners for advisory and refuted findings. G05 + G12 + G31 + G16
(9 lessons).

## Deliverables

1. Module and async-def docstring detection (2026-09-02-14-003).
2. AsciiDoc user-documentation detectors (2026-09-07-13-002).
3. Hand-mirrored-table surfacer class (2026-09-09-01-001).
4. Authored-claim verification for sweeps (2026-09-08-06-001).
5. Plugin-doctor precision on underivable surfaces (2026-09-06-10-002).
6. Flag-loop break on unknown analyzer scope (2026-09-16-17-002).
7. Discharge-owned advisory findings (2026-09-04-17-015).
8. Refuted review findings recorded rejected (2026-09-08-13-007).
9. Bulk resolve for triage passes (2026-09-13-12-012).

## Claim Labels

- OBSERVED: docstring detector misses module and async-def docstrings — read at `lessons-archive/2026-09-02-14-003.md` § The defect.
- OBSERVED: surfacer clean on 194 candidates where a reviewer found gate-addressable defects — read at `lessons-archive/2026-09-09-01-001.md` § Observed.
- HYPOTHESIS: extended detector set plus prompt validation plus owned terminal states closes the class — confirm/refute at `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/_self_review_detectors.py` § detectors (verify-at-outline).

## Expected Surface

- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/` — detectors, surfacer.
- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/` — argument naming.
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-findings/` — resolve/reject paths.

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: none (disjoint from PLAN-14 retrospective surfaces).
- Adjacent to: WS-03 refusal detectors read surfacer output without touching it.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/truthful-signals/plans/PLAN-216-self-review-detectors.md"
```

## Write-Boundary

The plan touches only its own repository source and tests. It creates and edits NO
file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}`
message, and reports its outcome through its PR and its inbox message.
