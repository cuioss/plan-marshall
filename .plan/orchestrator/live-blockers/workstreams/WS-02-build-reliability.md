# WS-02: Build Reliability

epic: live-blockers

> Charter document for one workstream — a coherent slice of the epic with its own goal
> and surface. Lives at `workstreams/WS-02-build-reliability.md` and is tracked in the
> `workstreams[]` field of the epic header, `status.json`. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the tier contract.

## Charter

Build execution and build-result parsing that produce false failures or wrong numbers. The workstream closes when a timeout leaves no orphan processes, a whole-tree verify can finish under concurrent plans, and Maven results are correct in consumer repositories.

## Scope

- In scope: the build server supervisor, the build wrapper and its temp handling, the Maven command discovery and output parsers
- Out of scope: the freshness gate that consumes build records (WS-01, PLAN-LB-01)

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-LB-23-verify-builds | staged | A timed-out build stops completely and names its bound; the freshness gate credits the gate's own green builds |
| PLAN-LB-28-java-consumer-repos | staged | Maven build results are right; self-review ends on a diff no surfacer covers (weak merge) |
| PLAN-LB-12-build-timeout-and-verify-budget | superseded | PLAN-LB-23 (all deliverables) |
| PLAN-LB-13-maven-build-results | superseded | PLAN-LB-28 (all deliverables) |

## Sequencing and Surface Notes

- PLAN-LB-23 and PLAN-LB-28 meet only at `script-shared/scripts/build/_build_shared.py`, which PLAN-LB-28 touches conditionally. Sequence them unless that plan's outline leaves the file alone.
- PLAN-LB-23 may run beside PLAN-LB-24 (WS-05); PLAN-LB-28 beside PLAN-LB-27 (WS-01).
