# WS-06: Opencode abstraction repairs

epic: process-compliance

> Charter document for one workstream — a coherent slice of the epic with its own goal
> and surface. Lives at `workstreams/WS-06-{slug}.md` and is tracked in the epic
> `status.json` `workstreams[]` field. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the tier contract.

## Charter

Own what surrounds finalize-machinery PLAN-07 (session-identity resolver, never
re-staged here): the opencode runtime gaps that forced improvisation, the
NO_SESSION_IDENTITY sentinel convention, and unattended-order merge authorization.
Closes when a run on opencode degrades visibly instead of stranding silently.

## Scope

- In scope: opencode runtime gaps, sentinel convention, unattended merge authorization
- Out of scope: PLAN-07 session-identity resolver itself (finalize-machinery), phase gates (WS-01), dispatch contracts (WS-05)

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-07-opencode-repairs | shipped | Runtime gaps, sentinel convention, merge authorization |
| PLAN-15-opencode-enforcement-parity | staged | Two-tier deny/ask map + tool.execute.before guard, role × surface × path matrix |

## Sequencing and Surface Notes

- PLAN-07 touches `platform-runtime` opencode paths; references (never edits) finalize-machinery PLAN-07. Run after WS-01/WS-02 so gate work is settled first.
