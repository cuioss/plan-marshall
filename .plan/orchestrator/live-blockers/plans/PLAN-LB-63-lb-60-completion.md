# PLAN-LB-63: Dead-step cleanup never deletes on a partial scan; the upgrade recovers from an executor that fails to import

epic: live-blockers
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for hand-off.
> Lives at `plans/PLAN-LB-63-lb-60-completion.md` and is queued as one row file,
> `queue/PLAN-LB-63.json`, in the epic ledger. This spec is SELF-SUFFICIENT.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the hand-off contract.

> Staged 2026-10-16 from the landing analysis of PLAN-LB-60 (#1782, `9d4207dcc`),
> `landings/PLAN-LB-60.md`: 1 met / 4 partial. High-severity remainder only (operator rule: high
> and critical). Runs in the OpenCode runbook lane. **Each deliverable is its own deliverable;
> each Done-when below is a test you write, see fail at `9d4207dcc`, then see pass.**

## Objective

PLAN-LB-60 made dead-step cleanup refuse to delete when discovery fails outright, but a
*partial* scan still reads as complete: a phase-6 skill directory that exists but lacks its
`workflow/` or `standards/` subdirectory makes live default steps look dead, and sync-defaults
deletes them and records them as operator removals. Separately, the upgrade still cannot recover
from an executor that exists but fails to import — the original PLAN-LB-40 failure.

## Deliverables

1. **A partial scan is `unknown`, and an unknown sweep says so.**
   - `_implementor_scan_surfaces_resolve` (`extension-api/scripts/extension_discovery.py:1447-1496`)
     resolves only when every directory the scan reads exists and is readable — for phase 6 the
     `workflow/` and `standards/` subdirectories the scan walks (`:1226-1233`), not only the skill
     directory (`:1466`). An unreadable step document is `unknown` for that step.
   - sync-defaults reports an unresolved sweep explicitly (`dead_sweep: unknown` with the reason),
     never as `dead_removed: []`.
   - A step deleted as dead is recorded with its params, distinguishable from an operator removal,
     so a later re-add does not read as crossing an operator decision.

   *Done when:* tests, each failing at `9d4207dcc`: a fixture phase-6 skill directory without
   `workflow/` yields `unknown` for `default:push` and deletes nothing; an unresolved sweep reports
   `dead_sweep: unknown`; a genuinely dead id's removal record carries its params and a
   `dead_step` origin.

2. **The upgrade recovers from an executor that fails to import.**
   - The in-script recovery condition (`marshall-steward/scripts/upgrade.py:991`,
     `needs_recovery = executor_version is None`) also covers an executor whose import fails
     (`ModuleNotFoundError` or any import error when probed), regenerating it from the newest cache
     as for a missing one.
   - The documented recovery entry (`upgrade-flow.md:65-81`) is one PLAN-LB-62's R5 allow-list
     admits; if PLAN-LB-62 has not landed, state the dependency in the PR and leave the doc form
     unchanged.

   *Done when:* a test with an executor fixture whose import raises `ModuleNotFoundError` reaches
   the stage plan after regeneration; it fails at `9d4207dcc`.

Split guard: two deliverables.

## Claim Labels

- OBSERVED: `_implementor_scan_surfaces_resolve` checks `_phase_6_skill_dir().is_dir()` only (`extension_discovery.py:1466`) — orchestrator-read at `9d4207dcc`.
- OBSERVED: with a phase-6 directory lacking `workflow/` and `standards/`, `_find_dead_step_ids(['default:push','default:create-pr'], 'phase-6-finalize')` returned both `dead` (delegated agent, in-process, read-only).
- OBSERVED: removed ids are written to the operator `removed_steps` list without params (`_cmd_sync_defaults.py:707-708`, `_cmd_quality_phases.py:76-82`) (delegated agent).
- OBSERVED: `upgrade.py:991` `needs_recovery = executor_version is None` (delegated agent).
- HYPOTHESIS: the import failure can be probed without executing the executor's code path that fails (e.g. a subprocess `--help` probe) — confirm before choosing the probe (verify before D2).

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/extension-api/scripts/extension_discovery.py` (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_sync_defaults.py` (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_quality_phases.py` (D1)
- OBSERVED: `test/plan-marshall/extension-api/test_extension_discovery_behavior.py` (D1)
- OBSERVED: `test/plan-marshall/manage-config/test_sync_defaults.py` (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/upgrade.py` (D2)
- OBSERVED: `test/plan-marshall/marshall-steward/test_upgrade.py` (D2)

## Dependencies and Sequencing

- Depends on: none. D2's doc form follows PLAN-LB-62 (running) if it has landed.
- Overlaps with: PLAN-LB-62 (running) only through `upgrade-flow.md` if D2 touches it.

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message.
