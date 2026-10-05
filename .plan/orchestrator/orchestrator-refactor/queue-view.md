<!-- GENERATED FILE — never hand-edit. Rendered from this epic's ledger (status.json, resume_anchor.md, queue/*.json) by `orchestrator regenerate-view --slug orchestrator-refactor`. On a merge conflict in this file, do not merge it by hand: merge the source files, run `orchestrator regenerate-view --slug orchestrator-refactor`, and `git add` the result. -->

# Queue view: Orchestrator Substrate Refactor

## START HERE

**Resume anchor**: 2026-10-03 — CLEANUP DONE after the PLAN-10 landing (restart verdict ready); ledger landed through the first live run of orchestrator land (outcome in that run's report; check with orchestrator land status). Shipped: PLAN-01/02/04/08/09/10/11; WS-05 complete. Nothing is staged: the only remaining rows are PLAN-03/05/06/07, parked under the PM-MCP supersession (do NOT emit; verdicts stale). Inbox empty.

Next action: OPERATOR DECISION — close and archive this epic (only parked rows remain), or keep it open. If land did not report landed, re-run /plan-orchestrator land: it resumes an in-flight land from its pushed marker. Still open for the operator: confirm /sync-harnesses ran after 7a0af07c5 (watch in epic.md); the gate's scope (per-candidate instead of whole-population fail-closed); the 24-epic legacy-layout sweep; routing of the git-config-injection hardening; settled-narrative relocation out of epic.md (deferred, candidates listed in Decisions); retiring lesson 2026-09-27-07-001 (the mailbox-probe defect #1685 fixed). PLAN-09 lesson rows stay at findings/2026-09-28-plan-09-lesson-carry-over.md until the operator names a target.

LEDGER LIVES IN THE SHARED WORKTREE since 2026-10-01: orchestrator.use_worktree is ON (repository-wide, #1666). Every ledger read/write resolves to .plan/local/worktrees/_orchestrator (branch chore/orchestrator-ledger) — always take epic_dir and store_checkout from resolve-path, never a cwd-relative .plan/orchestrator path. Ledger changes reach main through /plan-orchestrator land (#1690), not by hand.

2026-09-28 — PLAN-09 SHIPPED (#1652, 438a0a71f). #1641's revert of this tree restored from 88fcfc9ef and landed (#1656); record relocated to settled.md.

2026-09-26 — QUEUE PARKED, PM-MCP SUPERSEDES IT (review-apparatus-001 drained); PLAN-09/10/11 later re-staged by operator decision.
**Phase**: orchestrating
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
- PLAN-10 (WS-05) — plan=orchestrator-land-verbs — PR #1690 — landing=landings/PLAN-10.md — status: shipped
- PLAN-11 (WS-04) — plan=cross-check-dated-archive-self-collision — PR #1676 — landing=landings/PLAN-11.md — status: shipped

## Ordered Queue

| # | Plan | Workstream | Status | Surface (expected) |
|---|------|------------|--------|--------------------|
| 1 | PLAN-03 | WS-02 | parked | doc/adr/; marketplace/bundles/plan-marshall/skills/manage-config/SKILL.md; marketplace/bundles/plan-marshall/skills/manage-config/scripts/_config_defaults.py; marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/cache_retention.py; marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/_orchestrator_inbox.py; marketplace/bundles/plan-marshall/skills/script-shared/scripts/marketplace_paths.py; marketplace/bundles/pm-plugin-development/skills/plugin-doctor/references/rule-catalog.md; marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_shim_marker.py; marketplace/bundles/pm-plugin-development/skills/plugin-script-architecture/standards/shim-marker-convention.md; test/plan-marshall/marshall-steward/test_cache_retention.py; test/plan-marshall/plan-orchestrator/**; test/pm-plugin-development/plugin-doctor/test_analyze_shim_marker.py |
| 2 | PLAN-05 | WS-03 | parked | marketplace/bundles/plan-marshall/skills/manage-architecture/**; marketplace/bundles/plan-marshall/skills/manage-logging/**; marketplace/bundles/plan-marshall/skills/manage-status/**; marketplace/bundles/plan-marshall/skills/persona-plan-marshall-agent/standards/argument-naming.md; marketplace/bundles/plan-marshall/skills/persona-plan-orchestrator/**; marketplace/bundles/plan-marshall/skills/plan-orchestrator/**; marketplace/bundles/plan-marshall/skills/platform-runtime/**; marketplace/bundles/plan-marshall/skills/script-shared/scripts/query/query-architecture.py; marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/doctor-marketplace.py; marketplace/bundles/pm-plugin-development/skills/tools-epic-surface-partition/**; test/plan-marshall/manage-logging/**; test/plan-marshall/manage-status/**; test/plan-marshall/plan-orchestrator/**; test/pm-plugin-development/plugin-doctor/test_doctor_marketplace.py; test/pm-plugin-development/tools-epic-surface-partition/** |
| 3 | PLAN-06 | WS-04 | parked | marketplace/bundles/plan-marshall/skills/phase-1-init/**; marketplace/bundles/plan-marshall/skills/phase-6-finalize/**; marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/_orchestrator_inbox.py; marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py; marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/inbox-envelope.md; marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/landing-payload-spec.md; marketplace/bundles/pm-plugin-development/skills/tools-epic-surface-partition/scripts/_epic_partition.py; marketplace/bundles/pm-plugin-development/skills/tools-epic-surface-partition/scripts/epic-surface-partition.py; test/plan-marshall/phase-1-init/**; test/plan-marshall/phase-6-finalize/**; test/plan-marshall/plan-orchestrator/**; test/pm-plugin-development/tools-epic-surface-partition/** |
| 4 | PLAN-07 | WS-04 | parked | marketplace/bundles/plan-marshall/skills/plan-orchestrator/SKILL.md; marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/; marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/_orchestrator_inbox.py; marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py; test/plan-marshall/plan-orchestrator/** |
