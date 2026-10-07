# WS-05: Dispatch contract gaps

epic: process-compliance

> Charter document for one workstream — a coherent slice of the epic with its own goal
> and surface. Lives at `workstreams/WS-05-{slug}.md` and is tracked in the epic
> `status.json` `workstreams[]` field. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the tier contract.

## Charter

Own the five promoted dispatch-contract lessons: step-owned dispatch bodies,
fix-task loop-back shape, `loop_back_target` presence, producer-vocabulary
enforcement, and per-step prompt skills pinned by roster-closure tests. Closes when
improvisation-forced-by-missing-contract has a contract for each of the five.

## Scope

- In scope: dispatch registries, verification-feedback loop-back returns, producer vocabulary, dispatch roster + closure tests
- Out of scope: persona behavior prose (WS-04), generator/wrapper invocation paths (WS-03), runtime gaps (WS-06)

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-05-dispatch-envelopes | staged | Step-owned dispatch bodies, loop-back shape, loop_back_target |
| PLAN-06-dispatch-roster | staged | Producer vocab enforcement + roster prompt skills |

## Sequencing and Surface Notes

- PLAN-05 and PLAN-06 both live in dispatch surfaces: sequence them (PLAN-05 first, roster second) rather than parallelize.
