# WS-03: Consumer-Surfaced Config Integrity

epic: plan-optimization

> Charter document for one workstream. Lives at
> `workstreams/WS-03-consumer-surfaced-config-integrity.md` and is tracked in the epic
> `status.json` `workstreams[]` field. See
> `persona-marshall-orchestrator/standards/orchestration-model.md` for the tier contract.

## Charter

Fix manage-config / marshall-steward / executor-provisioning correctness defects surfaced by real
consumer-project onboarding (not by the wave-1 roadmap landings — a distinct source, hence its own
workstream). Found during first-run `/marshall-steward` wizard + upgrade runs on a fresh consumer
(cui-open-rewrite); all bugs INDEPENDENTLY VERIFIED against upstream source 2026-07-18. A recurring
meta-theme runs through them: **steward provisioning fails silently / fails open** (green
`status: success` on a wrong write; staleness vacuously `fresh`; a queue enabled without its CI).
Closes when fresh-project onboarding + upgrade is silent-corruption-free, staleness fails CLOSED, and
merge-queue enablement can't brick `main`.

## Scope

- In scope: manage-config `project set` field-name validation (`_cmd_system_plan.py`); the first-run
  wizard's finalize-lane materialization (`_cmd_sync_defaults.py` `_materialize_finalize_lanes` +
  `marshall-steward/references/wizard-flow.md` + steward SKILL.md).
- Out of scope: the merge-queue mechanism itself (that is PLAN-06's `default:branch-cleanup` knob
  surface — Bug 1 here is about *rejecting the wrong knob*, not the knob's behavior); the wave-2
  landings-cleanup plans (WS-01); parked items (WS-02).

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-07-steward-wizard-config-integrity | ✅ shipped (PR #932) | D1 `unknown_field` guard + D2 wizard sync-defaults lanes; bonus error-contract doc self-review catch |
| PLAN-08-executor-manifest-resolution | ✅ shipped (PR #934) | D1 clone-root resolver +traversal guard, D2 non-destructive stamp, D3 fail-closed `marshal_status: unknown`; ADR-009. Lesson 22-001 (scoped-gate blind spot) |
| PLAN-09-merge-queue-merge-group-guard | ✅ shipped (PR #935) | D1 refuse-at-API `_repo_has_merge_group_trigger` (direct-child-indent anchored) + D2 doc reconcile; resolved (a) refuse |
| PLAN-13-steward-provisioning-fail-closed | staged (REOPENED 07-18) | Systemic follow-up: fail-closed invariant + audit sweep over the provisioning surface (ADR-009), not just the 3 point-fixes above |

## Sequencing and Surface Notes

- **Startable now.** Surface (`_cmd_system_plan.py` + `_cmd_sync_defaults.py` + `wizard-flow.md` +
  steward SKILL.md) is distinct from in-flight PLAN-05 (terminal-title) — fully disjoint.
- **Adjacency with in-flight PLAN-06 (ci-pr-safe-merge):** both touch the manage-config / steward
  config surface, but different files (PLAN-06 = `_config_defaults.py` new knob + `configuration.adoc`;
  PLAN-07 = `_cmd_system_plan.py` validation + `_cmd_sync_defaults.py`/`wizard-flow.md`). Mostly
  disjoint — watch for a rebase if both touch `configuration.adoc` / config-defaults docs.
- No ordering dependency between the two deliverables; ships as one unit (2 deliverables, well under
  the split guard).
