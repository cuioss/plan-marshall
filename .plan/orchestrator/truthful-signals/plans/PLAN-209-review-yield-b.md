# PLAN-06: Review quota persistence and refusal currency

epic: truthful-signals
workstream: WS-03

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-06-review-yield-b.md` and is queued in the epic `status.json`
> `plans[]` field. The orchestrator EMITS the command below; it never launches the
> plan inline. This spec is SELF-SUFFICIENT.

## Objective

Persist review quotas across sessions and finish refusal currency: quota-wait
deadlines surviving kills, ETA-seeded rate-window claims, zero-contribution
visibility, cross-repo refusal phrasings, and verdict helpers wired into emission.
G13 remainder + G03 + 1 singleton (9 lessons).

## Deliverables

1. Quota-wait deadline persisted across killed sleeps (2026-09-08-13-008).
2. Zero-contribution quorum visibility and action (2026-09-08-13-011).
3. Rate-window claim seeded from bot-stated ETA (2026-09-13-09-001).
4. Participation-site expectations on new CI read sites (2026-09-17-19-002).
5. Verdict helpers wired into production emission before landing (2026-09-17-19-003).
6. Inline signal kept as gate complement; deferred hardening banked (2026-09-18-11-002).
7. Sourcery third refusal phrasing in registry (2026-08-25-09-012).
8. CodeRabbit reset-notice phrasing without trailing phrase (2026-09-07-13-006).
9. Provider nitpicks routed when test-only scope excludes them (2026-09-08-21-001).

## Claim Labels

- OBSERVED: Sourcery budget refusal matched no detector and read as participation — read at `lessons-archive/2026-08-25-09-012.md` § Context.
- OBSERVED: a required bot met quorum every round with zero findings and nothing acted — read at `lessons-archive/2026-09-08-13-011.md` (title triage; body verified at outline).
- HYPOTHESIS: persisted deadlines plus ETA-seeded claims plus yield-gated quorum close the loop — confirm/refute at `marketplace/bundles/plan-marshall/skills/automatic-review/` § quota/rate-window (verify-at-outline).

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/` — quota, rate-window, yield.
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-providers/` — provider nitpick routing.

## Dependencies and Sequencing

- Depends on: PLAN-05 (pacing/evidence primitives).
- Overlaps with: PLAN-05 — strictly sequenced after it.
- Adjacent to: none.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/truthful-signals/plans/PLAN-209-review-yield-b.md"
```

## Write-Boundary

The plan touches only its own repository source and tests. It creates and edits NO
file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}`
message, and reports its outcome through its PR and its inbox message.
