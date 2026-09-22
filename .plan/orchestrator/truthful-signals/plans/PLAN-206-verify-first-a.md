# PLAN-03: Verify-first rules and convergent fixes

epic: truthful-signals
workstream: WS-02

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-03-verify-first-a.md` and is queued in the epic `status.json`
> `plans[]` field. The orchestrator EMITS the command below; it never launches the
> plan inline. This spec is SELF-SUFFICIENT.

## Objective

Enforce the verify-first contract at the fix site: delete-to-one-home verified by
re-search, convergent resolutions applied as stated, rounds clean only on enumerated
propositions, unmeasured channels rendered as unmeasured. G02 first half (11 lessons).

## Deliverables

1. Delete-to-one-home verification by literal re-search, not enumeration (2026-09-02-14-001).
2. Four context-load columns populated with enrich at metrics close (2026-08-25-09-004).
3. Billing-cost measurement before bounding self-review re-fire (2026-08-25-09-007).
4. Regex-note on search --content metacharacter false zeros (2026-08-25-09-011).
5. Convergent resolutions applied as stated, not narrowed (2026-09-02-13-001).
6. Unmeasured channel rendered unmeasured, never clean zero (2026-09-02-13-004).
7. Round-cleanliness bound to enumerated propositions (2026-09-02-14-002).
8. Independent verification across self-review rounds (2026-09-03-01-001).
9. should_emit fragments declaring could-not-look (2026-09-03-06-003).
10. Mirrored-site admission with scope (2026-09-03-06-006).
11. Session-id capture at finalize entry (2026-09-04-14-006).

## Claim Labels

- OBSERVED: seven self-review rounds filed 25 findings while fixes were deletions the prescriptions already converged on — read at `lessons-archive/2026-09-02-14-001.md` § Context.
- OBSERVED: three rounds re-derived one misreading before an external reviewer overturned it — read at `lessons-archive/2026-09-03-01-001.md` (title triage; body verified at outline).
- HYPOTHESIS: proposition-enumeration obligation on each round breaks re-derivation loops — confirm/refute at `marketplace/bundles/plan-marshall/skills/phase-6-finalize/` § pre-submission-self-review (verify-at-outline).

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/` — self-review rounds, signal gates.
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-metrics/` — context-load columns, enrich.

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: PLAN-04 and PLAN-17 (same finalize surfaces) — PLAN-03 runs first alone.
- Adjacent to: none.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/truthful-signals/plans/PLAN-206-verify-first-a.md"
```

## Write-Boundary

The plan touches only its own repository source and tests. It creates and edits NO
file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}`
message, and reports its outcome through its PR and its inbox message.
