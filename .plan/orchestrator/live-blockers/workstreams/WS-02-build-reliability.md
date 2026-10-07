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
| PLAN-LB-12-build-timeout-and-verify-budget | staged | Timeouts kill the whole build and say which budget fired |
| PLAN-LB-13-maven-build-results | staged | Maven module-tests, test counts and warning classification are correct |

## Sequencing and Surface Notes

- LB-12 and LB-13 both touch `script-shared/scripts/build/`; LB-13 owns the parsers, LB-12 the execution and timeout path.
- LB-01 reads build records LB-12 writes; LB-12 must not change the record shape LB-01 relies on without saying so.
