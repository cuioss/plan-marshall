# WS-03: Compliant paths for forced violations

epic: process-compliance

> Charter document for one workstream — a coherent slice of the epic with its own goal
> and surface. Lives at `workstreams/WS-03-{slug}.md` and is tracked in the epic
> `status.json` `workstreams[]` field. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the tier contract.

## Charter

Own the three forced-violation gaps where the compliant path did not cover the use
case: a sanctioned orchestrator-spec read path, a generator-bootstrap exception with
template staleness detection, and a wrapper filter passthrough for targeted signal.
Closes when each deviation class has a sanctioned path or a recorded AGENTS.md carve-out.

## Scope

- In scope: `plan-orchestrator corpus read` (or AGENTS.md carve-out), generator bootstrap contract, wrapper passthrough form
- Out of scope: phase gates (WS-01), worktree flags (WS-02), dispatch rosters (WS-05)

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-03-compliant-paths | staged | Sanctioned read path, generator exception, wrapper passthrough |
| PLAN-08-process-contracts | staged | Nine→eight plan-lane contract gaps: bypass visibility, PR-body edits, intent idempotence, leaf budgets, snapshots, persistence, counts, prune gating (transferred from quality-aspect 2026-09-19; basetemp stayed with test-quality PLAN-180) |

## Sequencing and Surface Notes

- PLAN-03 touches orchestrator/generator/wrapper surfaces; adjacent to WS-05 dispatch work but non-overlapping (contracts vs. invocation paths).
