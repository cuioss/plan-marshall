<!-- GENERATED FILE — never hand-edit. Rendered from this epic's ledger (status.json, resume_anchor.md, queue/*.json) by `orchestrator regenerate-view --slug orchestrator-refactor`. On a merge conflict in this file, do not merge it by hand: merge the source files, run `orchestrator regenerate-view --slug orchestrator-refactor`, and `git add` the result. -->

# Queue view: Orchestrator Substrate Refactor

## START HERE

**Resume anchor**: 2026-10-03 — PLAN-10 RUNNING as plan orchestrator-land-verbs (5-execute at last cross-read). Emitted on operator override. Nothing else is staged: the queue is empty of emittable work. Parked, do NOT emit: PLAN-03/05/06/07 (PM-MCP supersession; verdicts stale, deliberately not refreshed). Shipped: PLAN-01/02/04/08/09/11.

At emit the gate refused PLAN-10 on two counts, both overridden by the operator: (1) candidate comparison indeterminate — sibling_epic_spec indeterminate: 95 of 611; (2) a checked overlap with live plan unified-sync-all-harnesses on manage-locks/standards/machine-global-config-scope-audit.md. (2) is discharged: #1684 merged (4962d398b), so expect at most a rebase on that file.

SYNC OWED: the ad-hoc fix #1685 (8aa33cfe1, recorded in epic.md Decisions) corrected the phase-transition mailbox probe, which misreported every orchestrated plan as not_orchestrated. The running PLAN-10 uses the synced plugin copy, so it keeps the old behaviour until the operator runs /sync-harnesses (which replaced /sync-plugin-cache in #1684). Do not deliver a mailbox message to PLAN-10 before that sync. A sync is outside the orchestrator's carve-out.

Next action: wait for PLAN-10 to land, then analyze (inbox drain: landing message plus its retrospective candidate-lessons), transition the row to shipped and stamp pr and landing. On resume before that: cross-read manage-status list for orchestrator-land-verbs and its PR state. Still open for the operator: the gate's scope (per-candidate instead of whole-population fail-closed — a new WS-04 spec); the 24-epic legacy-layout sweep; routing of the git-config-injection hardening; settled-narrative relocation out of epic.md (deferred); whether to close the epic once PLAN-10 ships (only parked rows would remain). PLAN-09 lesson rows stay at findings/2026-09-28-plan-09-lesson-carry-over.md until the operator names a target.

LEDGER LIVES IN THE SHARED WORKTREE since 2026-10-01: orchestrator.use_worktree is ON (repository-wide, #1666). Every ledger read/write resolves to .plan/local/worktrees/_orchestrator (branch chore/orchestrator-ledger) — always take epic_dir and store_checkout from resolve-path, never a cwd-relative .plan/orchestrator path. Ledger commits do not reach main by themselves: until PLAN-10 ships land, the ledger branch is landed by hand. The remote branch origin/chore/orchestrator-ledger is gone after the #1680 landing, so the next hand-landing needs a fresh push. To see what is unlanded, run git -C {store_checkout} log origin/main..HEAD and git -C {store_checkout} status.

2026-09-28 — PLAN-09 SHIPPED (#1652, 438a0a71f). #1641's revert of this tree restored from 88fcfc9ef and landed (#1656); record relocated to settled.md.

2026-09-26 — QUEUE PARKED, PM-MCP SUPERSEDES IT (review-apparatus-001 drained); PLAN-09/10/11 later re-staged by operator decision.
**Phase**: orchestrating
**Running**:
- PLAN-10 (WS-05) — plan=orchestrator-land-verbs
**Parked**:
- PLAN-03 (WS-02)
- PLAN-05 (WS-03)
- PLAN-06 (WS-04)
- PLAN-07 (WS-04)
**Queue** (staged, in order):
- (empty)
- PLAN-01 (WS-01) — plan=tracked-orchestrator-store-resolver — PR #1557, #1558, #1561 — landing=landings/PLAN-01.md — status: shipped
- PLAN-02 (WS-01) — plan=ledger-decomposition-and-row-vocabulary — PR #1609 — landing=landings/PLAN-02.md — status: shipped
- PLAN-04 (WS-03) — plan=identifier-vocabulary-decision — PR #1543 — landing=landings/PLAN-04.md — status: shipped
- PLAN-08 (WS-04) — plan=verdict-staleness-scoping — PR #1585 — landing=landings/PLAN-08.md — status: shipped
- PLAN-09 (WS-05) — plan=orchestrator-worktree-substrate — PR #1652 — landing=landings/PLAN-09.md — status: shipped
- PLAN-11 (WS-04) — plan=cross-check-dated-archive-self-collision — PR #1676 — landing=landings/PLAN-11.md — status: shipped

## Ordered Queue

| # | Plan | Workstream | Status | Surface (expected) |
|---|------|------------|--------|--------------------|
| 1 | PLAN-03 | WS-02 | parked | doc/adr/; marketplace/bundles/plan-marshall/skills/manage-config/SKILL.md; marketplace/bundles/plan-marshall/skills/manage-config/scripts/_config_defaults.py; marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/cache_retention.py; marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/_orchestrator_inbox.py; marketplace/bundles/plan-marshall/skills/script-shared/scripts/marketplace_paths.py; marketplace/bundles/pm-plugin-development/skills/plugin-doctor/references/rule-catalog.md; marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_shim_marker.py; marketplace/bundles/pm-plugin-development/skills/plugin-script-architecture/standards/shim-marker-convention.md; test/plan-marshall/marshall-steward/test_cache_retention.py; test/plan-marshall/plan-orchestrator/**; test/pm-plugin-development/plugin-doctor/test_analyze_shim_marker.py |
| 2 | PLAN-05 | WS-03 | parked | marketplace/bundles/plan-marshall/skills/manage-architecture/**; marketplace/bundles/plan-marshall/skills/manage-logging/**; marketplace/bundles/plan-marshall/skills/manage-status/**; marketplace/bundles/plan-marshall/skills/persona-plan-marshall-agent/standards/argument-naming.md; marketplace/bundles/plan-marshall/skills/persona-plan-orchestrator/**; marketplace/bundles/plan-marshall/skills/plan-orchestrator/**; marketplace/bundles/plan-marshall/skills/platform-runtime/**; marketplace/bundles/plan-marshall/skills/script-shared/scripts/query/query-architecture.py; marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/doctor-marketplace.py; marketplace/bundles/pm-plugin-development/skills/tools-epic-surface-partition/**; test/plan-marshall/manage-logging/**; test/plan-marshall/manage-status/**; test/plan-marshall/plan-orchestrator/**; test/pm-plugin-development/plugin-doctor/test_doctor_marketplace.py; test/pm-plugin-development/tools-epic-surface-partition/** |
| 3 | PLAN-06 | WS-04 | parked | marketplace/bundles/plan-marshall/skills/phase-1-init/**; marketplace/bundles/plan-marshall/skills/phase-6-finalize/**; marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/_orchestrator_inbox.py; marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py; marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/inbox-envelope.md; marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/landing-payload-spec.md; marketplace/bundles/pm-plugin-development/skills/tools-epic-surface-partition/scripts/_epic_partition.py; marketplace/bundles/pm-plugin-development/skills/tools-epic-surface-partition/scripts/epic-surface-partition.py; test/plan-marshall/phase-1-init/**; test/plan-marshall/phase-6-finalize/**; test/plan-marshall/plan-orchestrator/**; test/pm-plugin-development/tools-epic-surface-partition/** |
| 4 | PLAN-07 | WS-04 | parked | marketplace/bundles/plan-marshall/skills/plan-orchestrator/SKILL.md; marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/; marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/_orchestrator_inbox.py; marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py; test/plan-marshall/plan-orchestrator/** |
| 5 | PLAN-10 | WS-05 | running | marketplace/bundles/plan-marshall/skills/manage-locks/**; marketplace/bundles/plan-marshall/skills/persona-plan-orchestrator/standards/orchestration-model.md; marketplace/bundles/plan-marshall/skills/plan-orchestrator/SKILL.md; marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py; marketplace/bundles/plan-marshall/skills/plan-orchestrator/workflow/**; marketplace/bundles/plan-marshall/skills/tools-file-ops/scripts/orchestrator_worktree.py; marketplace/bundles/plan-marshall/skills/tools-integration-ci/**; marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/git-workflow.py; marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py; test/plan-marshall/manage-locks/**; test/plan-marshall/plan-orchestrator/**; test/plan-marshall/tools-file-ops/**; test/plan-marshall/tools-integration-ci/**; test/plan-marshall/workflow-integration-git/** |
