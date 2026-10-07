# PLAN-05: Review-bot pacing and yield primitives

epic: quality-aspect
workstream: WS-03

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-05-review-yield-a.md` and is queued in the epic `status.json`
> `plans[]` field. The orchestrator EMITS the command below; it never launches the
> plan inline. This spec is SELF-SUFFICIENT.

## Objective

Replace unexecutable review pacing and establish the yield/evidence primitives:
dispatch-safe waits, three-valued head_sha evidence, per-source yield recording,
FIND-time size-cap recognition, and invocations that survive their runtime. G13
first part (8 lessons).

## Deliverables

1. Dispatch-executable wait replacing standalone sleep pacers (2026-09-03-06-002).
2. Three-valued head_sha evidence instead of bare bool (2026-09-03-06-001).
3. Per-plan review yield recorded by source (2026-09-03-07-003).
4. Declined-claim bucketing by rationale effect (2026-09-03-16-004).
5. Size-cap refusal recognition at FIND time (2026-09-04-17-002).
6. Automatic-review invocations surviving their runtime (2026-09-07-13-005).
7. Narrowing remedy with named limit for two-remedy findings (2026-09-07-15-009).
8. Invocation-scoped review-producer refusals (2026-09-08-13-003).

## Claim Labels

- OBSERVED: SKILL prescribes bare-sleep pacing a dispatched leaf cannot execute — read at `lessons-archive/2026-09-03-06-002.md` § Context.
- OBSERVED: size-cap refusal recognized only after the operator reads it — read at `lessons-archive/2026-09-04-17-002.md` (title triage; body verified at outline).
- HYPOTHESIS: collector-side waits plus FIND-time refusal matchers retire both classes — confirm/refute at `marketplace/bundles/plan-marshall/skills/automatic-review/` § poll/refusal registry (verify-at-outline).

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/` — pacing, detectors, yield.

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: PLAN-06 (same skill) — PLAN-05 runs first (primitives before persistence).
- Adjacent to: none.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/quality-aspect/plans/PLAN-05-review-yield-a.md"
```

## Write-Boundary

The plan touches only its own repository source and tests. It creates and edits NO
file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}`
message, and reports its outcome through its PR and its inbox message.
