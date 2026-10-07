# WS-09: Testing, Config & Process Contracts

epic: quality-aspect

> Charter document for one workstream — a coherent slice of the epic with its own goal
> and surface. Lives at `workstreams/WS-09-quality-aspect.md` and is tracked in the epic
> `status.json` `workstreams[]` field.

## Charter

Owns test fidelity and cross-cutting contracts: argv constants the CLI accepts,
mirrors pinned to published seams, config roots rejected before field access, and
the nine process-contract lessons (CI abstraction, intent rendering, re-review
budgets, manifest snapshots, finding persistence, footprint pruning). Closed when a
green suite means the mirrored behavior and every stated default matches the code.

## Scope

- In scope: persona-module-tester fidelity, pytest-testing mirrors and splits,
  manage-config guards, tools-integration-ci merge-queue and derivation comments,
  the nine empty-component process lessons.
- Out of scope: lifecycle phase mechanics (WS-06), reviewer signals (WS-03).

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-15-config-guards | staged | Config root guards and mode lists (reshaped 2026-09-19: tester/mirror lessons moved to test-quality PLAN-180; renamed 2026-09-19, no testing content remains) |

*Transferred out 2026-09-19 (operator direction): PLAN-16-process-contracts →
process-compliance PLAN-08 (8 lessons; basetemp single-owned by test-quality
PLAN-180). Spec file removed from this tree; queue row retired; lesson evidence
remains at `lessons-archive/`.*

## Sequencing and Surface Notes

- PLAN-15 (tester/python/config) and PLAN-16 (ci/github contracts) are
  surface-disjoint and may run concurrently.
