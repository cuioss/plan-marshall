# PLAN-15: Config root guards and mode lists

epic: quality-aspect
workstream: WS-09

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-15-config-guards.md` and is queued in the epic `status.json`
> `plans[]` field. The orchestrator EMITS the command below; it never launches the
> plan inline. This spec is SELF-SUFFICIENT.
>
> Reshaped 2026-09-19: tester-fidelity lessons (G19) and pytest-mirror lessons (G29)
> transferred to test-quality PLAN-180 at operator direction. This spec keeps the
> manage-config guards (2 lessons).

## Objective

Make configs fail fast: non-object marshal.json roots rejected before field access
and displayed/tested mode lists derived from the authoritative tuple.

## Deliverables

1. Non-object marshal.json roots rejected before field access (2026-09-16-17-001).
2. Displayed/tested mode lists derived from authoritative tuple (2026-09-16-17-003).

## Claim Labels

- OBSERVED: load_config returned any JSON root; list/scalar roots break field access — read at `lessons-archive/2026-09-16-17-001.md` § Defect; core guard at `_config_core.py:134` is a different layer (verify at outline whether interaction-mode path is covered).
- HYPOTHESIS: root rejection plus derived mode lists holds — confirm/refute at `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_interaction_mode.py` § load_config (verify-at-outline).

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/` — root guards, mode lists.

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: none.
- Adjacent to: none.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/quality-aspect/plans/PLAN-15-config-guards.md"
```

## Write-Boundary

The plan touches only its own repository source and tests. It creates and edits NO
file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}`
message, and reports its outcome through its PR and its inbox message.
