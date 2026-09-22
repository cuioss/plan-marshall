# PLAN-01: Ledger joins and retrospective honesty

epic: quality-aspect
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-01-ledger-joins.md` and is queued in the epic `status.json`
> `plans[]` field. The orchestrator EMITS the command below; it never launches the
> plan inline. This spec is SELF-SUFFICIENT.

## Objective

Make finalize-lane cost numbers join and honest: ledger rows pair on a shared key,
per-task artifact emission is measurable, and retrospective aspects report the
population each figure was computed over. Lessons: G17, G10, G27 (10 lessons,
archived at `lessons-archive/`).

## Deliverables

1. Step-id join key across execution-log and dispatch-boundary ledgers (2026-09-02-13-002).
2. Per-task changed_files persistence for artifact-emission measurement (2026-09-04-17-004).
3. [OUTCOME] emission for every completed task including late dispatch (2026-09-04-17-007).
4. analyze-logs build_count reconciled with pyproject_build calls (2026-08-25-09-009).
5. RE_ENTRY_COVERAGE precondition decoupled from its policed signal (2026-09-02-13-003).
6. Batched fragment registration (2026-09-03-19-007).
7. Per-firing [DISPATCH] comparison in check-dispatch-audit (2026-09-04-14-001).
8. Manifest-consistency caveat on post-merge base-ref (2026-09-04-17-006).
9. Split-plan footprint union over every shipped merge commit (2026-09-07-15-003).
10. Single-plan-root fragment path resolution (2026-09-16-17-004).

(Retired 2026-09-19: transcript-less target policy — the transcript-gated
resolver with gap flag and hard block is documented at
phase-6-finalize/SKILL.md § session_id and plan-marshall/workflow/execution.md;
verified in-tree before retiring.)

## Claim Labels

- OBSERVED: execution-log vs dispatch-boundary rows pair at ~40% with no shared key — read at `lessons-archive/2026-09-02-13-002.md` § Context.
- OBSERVED: analyze-logs reports build_count 0 against 84 recorded pyproject_build calls — read at `lessons-archive/2026-08-25-09-009.md` § Context.
- HYPOTHESIS: a step_id join key plus union_rows rendering pairs the ledgers without breaking existing consumers — confirm/refute at `marketplace/bundles/plan-marshall/skills/manage-metrics/scripts/_cmd_reconcile_ledgers.py` § `reconcile-ledgers` (verify-at-outline).

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-metrics/` — ledger pairing, reconcile-ledgers.
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-retrospective/` — analyze-logs, chat-signal aspects.
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-change-ledger/` — per-build rows.

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: PLAN-04 (manage-metrics context-load flags) — sequence PLAN-01 first.
- Adjacent to: WS-08 re-fire accounting reads these joins without touching them.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/quality-aspect/plans/PLAN-01-ledger-joins.md"
```

## Write-Boundary

The plan touches only its own repository source and tests. It creates and edits NO
file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}`
message, and reports its outcome through its PR and its inbox message.
