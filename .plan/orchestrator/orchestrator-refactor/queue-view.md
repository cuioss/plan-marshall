<!-- GENERATED FILE — never hand-edit. Rendered from this epic's ledger (status.json, resume_anchor.md, queue/*.json) by `orchestrator regenerate-view --slug orchestrator-refactor`. On a merge conflict in this file, do not merge it by hand: merge the source files, run `orchestrator regenerate-view --slug orchestrator-refactor`, and `git add` the result. -->

# Queue view: Orchestrator Substrate Refactor

## START HERE

**Resume anchor**: 2026-09-27 — PLAN-09 RUNNING as plan orchestrator-worktree-substrate (one shared worktree for ALL epic changes; overlap warning waived by operator). Next: await its landing message in inbox (analyze). PLAN-10 strictly after PLAN-09; PLAN-11 staged but shares orchestrator.py — do not emit while PLAN-09 runs unless the operator waives again. Parked, do NOT emit: PLAN-03/05/06/07. PM-MCP carry-over file still awaits operator commit in plan-marshall-mcp.

2026-09-26 — QUEUE PARKED, PM-MCP SUPERSEDES IT (review-apparatus-001 drained); PLAN-09/10/11 later re-staged by operator decision.

PREVIOUS ANCHOR (kept): Cleanup pass shipped (PR #1621, merge 54b4bb525): 30 A1 verdicts re-grounded, PLAN-10/PLAN-11 re-scoped. restart-check: ready.
**Phase**: orchestrating
**Running**:
- PLAN-09 (WS-05) — plan=orchestrator-worktree-substrate
**Parked**:
- PLAN-03 (WS-02)
- PLAN-05 (WS-03)
- PLAN-06 (WS-04)
- PLAN-07 (WS-04)
**Queue** (staged, in order):
1. PLAN-10 (WS-05)
2. PLAN-11 (WS-04)
- PLAN-01 (WS-01) — plan=tracked-orchestrator-store-resolver — PR #1557, #1558, #1561 — landing=landings/PLAN-01.md — status: shipped
- PLAN-02 (WS-01) — plan=ledger-decomposition-and-row-vocabulary — PR #1609 — landing=landings/PLAN-02.md — status: shipped
- PLAN-04 (WS-03) — plan=identifier-vocabulary-decision — PR #1543 — landing=landings/PLAN-04.md — status: shipped
- PLAN-08 (WS-04) — plan=verdict-staleness-scoping — PR #1585 — landing=landings/PLAN-08.md — status: shipped

## Ordered Queue

| # | Plan | Workstream | Status | Surface (expected) |
|---|------|------------|--------|--------------------|
| 1 | PLAN-03 | WS-02 | parked | doc/adr/; marketplace/bundles/plan-marshall/skills/manage-config/SKILL.md; marketplace/bundles/plan-marshall/skills/manage-config/scripts/_config_defaults.py; marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/cache_retention.py; marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/_orchestrator_inbox.py; marketplace/bundles/plan-marshall/skills/script-shared/scripts/marketplace_paths.py; marketplace/bundles/pm-plugin-development/skills/plugin-doctor/references/rule-catalog.md; marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_shim_marker.py; marketplace/bundles/pm-plugin-development/skills/plugin-script-architecture/standards/shim-marker-convention.md; test/plan-marshall/marshall-steward/test_cache_retention.py; test/plan-marshall/plan-orchestrator/**; test/pm-plugin-development/plugin-doctor/test_analyze_shim_marker.py |
| 2 | PLAN-05 | WS-03 | parked | marketplace/bundles/plan-marshall/skills/manage-architecture/**; marketplace/bundles/plan-marshall/skills/manage-logging/**; marketplace/bundles/plan-marshall/skills/manage-status/**; marketplace/bundles/plan-marshall/skills/persona-plan-marshall-agent/standards/argument-naming.md; marketplace/bundles/plan-marshall/skills/persona-plan-orchestrator/**; marketplace/bundles/plan-marshall/skills/plan-orchestrator/**; marketplace/bundles/plan-marshall/skills/platform-runtime/**; marketplace/bundles/plan-marshall/skills/script-shared/scripts/query/query-architecture.py; marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/doctor-marketplace.py; marketplace/bundles/pm-plugin-development/skills/tools-epic-surface-partition/**; test/plan-marshall/manage-logging/**; test/plan-marshall/manage-status/**; test/plan-marshall/plan-orchestrator/**; test/pm-plugin-development/plugin-doctor/test_doctor_marketplace.py; test/pm-plugin-development/tools-epic-surface-partition/** |
| 3 | PLAN-06 | WS-04 | parked | marketplace/bundles/plan-marshall/skills/phase-1-init/**; marketplace/bundles/plan-marshall/skills/phase-6-finalize/**; marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/_orchestrator_inbox.py; marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py; marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/inbox-envelope.md; marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/landing-payload-spec.md; marketplace/bundles/pm-plugin-development/skills/tools-epic-surface-partition/scripts/_epic_partition.py; marketplace/bundles/pm-plugin-development/skills/tools-epic-surface-partition/scripts/epic-surface-partition.py; test/plan-marshall/phase-1-init/**; test/plan-marshall/phase-6-finalize/**; test/plan-marshall/plan-orchestrator/**; test/pm-plugin-development/tools-epic-surface-partition/** |
| 4 | PLAN-07 | WS-04 | parked | marketplace/bundles/plan-marshall/skills/plan-orchestrator/SKILL.md; marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/; marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/_orchestrator_inbox.py; marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py; test/plan-marshall/plan-orchestrator/** |
| 5 | PLAN-09 | WS-05 | running | marketplace/bundles/plan-marshall/skills/manage-config/scripts/_config_defaults.py; marketplace/bundles/plan-marshall/skills/manage-config/standards/data-model.md; marketplace/bundles/plan-marshall/skills/persona-plan-orchestrator/standards/orchestration-model.md; marketplace/bundles/plan-marshall/skills/phase-1-init/**; marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/_orchestrator_inbox.py; marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py; marketplace/bundles/plan-marshall/skills/platform-runtime/**; marketplace/bundles/plan-marshall/skills/tools-file-ops/**; marketplace/bundles/plan-marshall/skills/workflow-integration-git/SKILL.md; marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/git-workflow.py; test/plan-marshall/manage-config/**; test/plan-marshall/phase-1-init/**; test/plan-marshall/plan-orchestrator/**; test/plan-marshall/workflow-integration-git/** |
| 6 | PLAN-10 | WS-05 | staged | marketplace/bundles/plan-marshall/skills/manage-locks/**; marketplace/bundles/plan-marshall/skills/plan-orchestrator/SKILL.md; marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py; marketplace/bundles/plan-marshall/skills/tools-integration-ci/**; marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/git-workflow.py; test/plan-marshall/plan-orchestrator/**; test/plan-marshall/tools-integration-ci/** |
| 7 | PLAN-11 | WS-04 | staged | marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py; test/plan-marshall/plan-orchestrator/test_orchestrator_corpus.py |
