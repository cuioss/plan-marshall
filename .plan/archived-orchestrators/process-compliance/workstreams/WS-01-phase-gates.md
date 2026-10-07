# WS-01: Phase-completion artifact gates

epic: process-compliance

> Charter document for one workstream — a coherent slice of the epic with its own goal
> and surface. Lives at `workstreams/WS-01-{slug}.md` and is tracked in the epic
> `status.json` `workstreams[]` field. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the tier contract.

## Charter

Own the earliest decidable enforcement point for phase transitions: refuse bare
2-refine/3-outline/4-plan completions inside `manage-status transition` unless the
phase's artifact exists, with an explicit logged exemption for legitimately
artifact-free phases. Closes when a run cannot skip phases silently.

## Scope

- In scope: `manage-status` transition gate, phase artifact validators (solution_outline, task files, clarify record), exemption metadata schema
- Out of scope: worktree machinery (WS-02), dispatch contracts (WS-05), persona behavior rules (WS-04)

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-01-phase-gates | staged | Phase artifact gates in manage-status transition |

## Sequencing and Surface Notes

- PLAN-01 touches only `manage-status` + phase artifact readers; disjoint from worktree (WS-02) and runtime (WS-06) surfaces. Sequential slot anyway (scope=1).
