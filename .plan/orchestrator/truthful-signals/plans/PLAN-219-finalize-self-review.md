# PLAN-17: Finalize self-review round semantics

> ⛔⛔ **SUPERSEDED BY PM-MCP (2026-09-26, operator decision; row status `parked`).** `plan-marshall-mcp` replaces both the
> process prose and the Python scripts this plan edits, so implementing it here is legacy work. Its
> implementation-independent content (rules, invariants, classifications, data, fixtures) was extracted to
> `plan-marshall-mcp/doc/known-defects/truthful-signals-carry-over.md` as PM-MCP input.
> **Do NOT emit; un-park only by explicit operator decision.** The spec body below stays intact as the evidence chain.

epic: truthful-signals
workstream: WS-08

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-17-finalize-self-review.md` and is queued in the epic
> `status.json` `plans[]` field. The orchestrator EMITS the command below; it never
> launches the plan inline. This spec is SELF-SUFFICIENT.

## Objective

Give every self-review round honest semantics: VERIFY emission present,
whole-passage re-review after fixes, archive-plan completion never silently lost.
G24 first part (10 lessons).

## Deliverables

1. [VERIFY] emission restored across the finalize lane (2026-09-02-13-005).
2. Whole-round zero as the only benign zero (2026-09-02-14-004).
3. Simplify reconciling outline-prose decisions (2026-09-03-11-001).
4. Prompt-field validation before dispatch (2026-09-07-15-001).
5. Stacked-child rebase before refusal re-read (2026-09-07-15-004).
6. Emitting-notation bucketing in lessons-capture gate (2026-09-07-15-011).
7. archive-plan completion receipt (2026-09-08-13-001).
8. mutates_source reconciled with edit behaviour (2026-09-08-13-002).
9. Whole-passage re-review after self-review fixes (2026-09-08-13-005).
10. Infrastructure-noise classification for CI timeouts (2026-09-12-08-001).

(Retired 2026-09-19, both verified in-tree before retiring:
returned_with_findings stamping — documented by construction at
phase-6-finalize/SKILL.md (mark-step-done outcome loop_back triggers the
stamp); metrics re-close on loop-back — end-phase accumulates with close_count,
re_entered_phases and value_scope at manage-metrics/SKILL.md and data-format.md.)

## Claim Labels

- OBSERVED: archive-plan is the one step whose completion record can vanish with no downstream catch — read at `lessons-archive/2026-09-08-13-001.md` (title triage; body verified at outline).
- HYPOTHESIS: VERIFY emission plus completion receipts retires the class — confirm/refute at `marketplace/bundles/plan-marshall/skills/phase-6-finalize/` § round outcomes (verify-at-outline).

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/` — VERIFY, archive-plan.

## Dependencies and Sequencing

- Depends on: PLAN-01 (reads its ledger joins) and PLAN-03 (round rules).
- Overlaps with: PLAN-03, PLAN-04, PLAN-18 — sequenced after PLAN-03.
- Adjacent to: none.
- Landing follow-ups (PLAN-01, #1545; folded from ledger-joins-003/006, no new
  surface): when a verifier is unavailable, record exactly what substitute
  evidence the resolution rested on so a later pass can re-check without
  re-deriving context; treat CI deadline_exceeded as a re-poll signal rather
  than a failure verdict, resolving premature timeout findings as
  taken_into_account once the re-poll lands green.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/truthful-signals/plans/PLAN-219-finalize-self-review.md"
```

## Write-Boundary

The plan touches only its own repository source and tests. It creates and edits NO
file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}`
message, and reports its outcome through its PR and its inbox message.
