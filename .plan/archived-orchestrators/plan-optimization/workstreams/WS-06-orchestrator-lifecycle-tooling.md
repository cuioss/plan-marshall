# WS-06: Orchestrator Lifecycle Tooling

epic: plan-optimization

> Charter document for one workstream. Lives at `workstreams/WS-06-orchestrator-lifecycle-tooling.md`
> and tracked in the epic `status.json` `workstreams[]` field.

## Charter

Extend the orchestrator's own lifecycle tooling. First item: add an `archive` capability that
physically relocates a CLOSED epic tree out of the active orchestrator store root to
`.plan/local/archived-orchestrators/{slug}/`, analogous to `.plan/local/archived-plans/`. Today
`close` freezes in place (the tree stays under `.plan/local/orchestrator/` as the audit record); the
operator wants an optional move-out step for store-root tidiness. Closes when a closed epic can be
archived to `archived-orchestrators/` via a first-class verb, with discovery/status/resume still
resolving it from the archived location.

## Scope

- In scope: the `archive` verb on `marshall-orchestrator` (router + `workflow/archive.md`), a
  `orchestrator.py archive` subcommand (main-anchored relocation), the orchestration-model standard
  update (lifecycle: close → optional archive), and status/resume/scan fallback to the archived tree.
- Out of scope: changing `close` semantics (close still freezes; archive is a separate, optional
  post-close step); plan archiving (already exists); the epic's substantive plans (WS-01…WS-05).

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-12-orchestrator-archive-verb | staged | `archive` verb + `orchestrator.py archive` → `.plan/local/archived-orchestrators/{slug}/` |

## Sequencing and Surface Notes

- Operator-requested (2026-07-18). Fully disjoint from in-flight PLAN-10 (github) and staged PLAN-11
  (manifest/aspect) — orchestrator-skill surface is its own. Startable anytime.
- Meta note: this modifies the orchestrator skill this epic is being run under; a normal plan-marshall
  meta-dev task (orchestrator stages, the plan lifecycle implements).
