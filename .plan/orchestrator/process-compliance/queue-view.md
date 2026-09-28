<!-- GENERATED FILE — never hand-edit. Rendered from this epic's ledger (status.json, resume_anchor.md, queue/*.json) by `orchestrator regenerate-view --slug process-compliance`. On a merge conflict in this file, do not merge it by hand: merge the source files, run `orchestrator regenerate-view --slug process-compliance`, and `git add` the result. -->

# Queue view: Process compliance: make rule-following structural, especially on opencode

## START HERE

**Resume anchor**: 2026-09-28 LANDING: branch chore/process-compliance-drain-and-restore carries (a) restore of this epic from 88fcfc9ef after #1641 reverted it (PLAN-08/09/11/14 parked again, decisions + banners back, archive re-consumed) and (b) the 2026-09-28 drain (PLAN-17 fold, PLAN-18 staged) plus #1641 findings to 8 epics. Next: merge that PR, pull main; then /plan-orchestrator next slug=process-compliance (planning-lane cluster PLAN-10/16/17/18 overlaps — one at a time, PLAN-17 before PLAN-18); PLAN-12 + PLAN-13 RUNNING — analyze on landing. | PRIOR: 2026-09-28 drain (4 findings): folded 2 into PLAN-17, staged PLAN-18. | PRIOR: 2026-09-27 drain under operator directive 'current problems are FIXED, not relayed to PM-MCP': PLAN-10 un-parked; PLAN-16 + PLAN-17 staged. | PRIOR: 2026-09-26 PM-MCP supersession: rest of queue parked, carry-over filed. | PRIOR: Cleanup done at e995df45 (44 re-grounded, compacted); restart not_ready.
**Phase**: orchestrating
**Running**:
- PLAN-12 (WS-05)
- PLAN-13 (WS-07)
**Parked**:
- PLAN-08 (WS-03)
- PLAN-09 (WS-03)
- PLAN-11 (WS-06)
- PLAN-14 (WS-04)
**Queue** (staged, in order):
1. PLAN-10 (WS-01)
2. PLAN-16 (WS-01)
3. PLAN-17 (WS-01)
4. PLAN-18 (WS-01)
- PLAN-01 (WS-01) — plan=phase-gates — PR 1540 — landing=landings/PLAN-01.md — status: shipped
- PLAN-02 (WS-02) — plan=plan-02-worktree-discipline — PR 1547 — landing=landings/PLAN-02.md — status: shipped
- PLAN-03 (WS-03) — plan=compliant-paths — PR 1542 — landing=landings/PLAN-03.md — status: shipped
- PLAN-04 (WS-04) — plan=plan-04-persona-behavior — PR 1556 — landing=landings/PLAN-04.md — status: shipped
- PLAN-05 (WS-05) — plan=implement-dispatch-envelopes-process-compliance — PR 1583 — landing=landings/PLAN-05.md — status: shipped
- PLAN-06 (WS-05) — plan=plan-06-dispatch-roster — PR 1606 — landing=landings/PLAN-06.md — status: shipped
- PLAN-07 (WS-06) — plan=plan-07-opencode-repairs — PR 1554 — landing=landings/PLAN-07.md — status: shipped
- PLAN-15 (WS-06) — plan=implement-opencode-enforcement-parity — PR 1618 — landing=landings/PLAN-15.md — status: shipped

## Ordered Queue

| # | Plan | Workstream | Status | Surface (expected) |
|---|------|------------|--------|--------------------|
| 1 | PLAN-08 | WS-03 | parked | marketplace/bundles/plan-marshall/skills/tools-integration-ci/; marketplace/bundles/plan-marshall/skills/workflow-integration-github/ |
| 2 | PLAN-09 | WS-03 | parked | AGENTS.md; marketplace/bundles/plan-marshall/skills/plan-orchestrator/SKILL.md; marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py; test/plan-marshall/plan-orchestrator/ |
| 3 | PLAN-10 | WS-01 | staged | marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_lifecycle.py; marketplace/bundles/plan-marshall/skills/phase-1-init/; marketplace/bundles/plan-marshall/skills/plan-marshall/; marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/planning.md; marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/_orchestrator_inbox.py; test/plan-marshall/plan-marshall/; test/plan-marshall/plan-orchestrator/ |
| 4 | PLAN-11 | WS-06 | parked | marketplace/bundles/plan-marshall/skills/phase-6-finalize/; marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py; test/plan-marshall/phase-5-execute/; test/plan-marshall/plan-orchestrator/ |
| 5 | PLAN-12 | WS-05 | running | marketplace/bundles/plan-marshall/skills/manage-locks/scripts/merge_lock.py; marketplace/bundles/plan-marshall/skills/manage-status/scripts/manage-status.py; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md; marketplace/bundles/plan-marshall/skills/plan-retrospective/; marketplace/bundles/plan-marshall/skills/tools-integration-ci/scripts/ci.py; marketplace/bundles/plan-marshall/skills/tools-integration-ci/standards/pr-review-operations.md; test/plan-marshall/manage-status/ |
| 6 | PLAN-13 | WS-07 | running | marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/archive-plan.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/dispatch-inline-split.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/emit-landing.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/create-pr.md; marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/session_binding.py; test/plan-marshall/phase-6-finalize/ |
| 7 | PLAN-14 | WS-04 | parked | marketplace/bundles/plan-marshall/skills/persona-plan-marshall-agent/; test/plan-marshall/persona-plan-marshall-agent/ |
| 8 | PLAN-16 | WS-01 | staged | CLAUDE.md; marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_domain_detect.py; marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/manage-execution-manifest.py; marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_planning_lane.py; marketplace/bundles/plan-marshall/skills/persona-plan-marshall-agent/; marketplace/bundles/plan-marshall/skills/phase-1-init/; marketplace/bundles/plan-marshall/skills/plan-marshall/SKILL.md; test/plan-marshall/manage-config/; test/plan-marshall/manage-execution-manifest/; test/plan-marshall/manage-status/ |
| 9 | PLAN-17 | WS-01 | staged | marketplace/bundles/plan-marshall/skills/phase-2-refine/; marketplace/bundles/plan-marshall/skills/phase-3-outline/SKILL.md; marketplace/bundles/plan-marshall/skills/plan-marshall/references/phase-handshake.md; marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/_git_helpers.py; marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/_invariants.py; marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/planning-outline.md; marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/planning.md; test/plan-marshall/plan-marshall/ |
| 10 | PLAN-18 | WS-01 | staged | marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/; marketplace/bundles/plan-marshall/skills/phase-2-refine/; marketplace/bundles/plan-marshall/skills/phase-3-outline/; marketplace/bundles/plan-marshall/skills/phase-4-plan/; marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/planning-outline.md; marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/planning.md; marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/q-gate-validation.md; marketplace/bundles/pm-plugin-development/skills/ext-outline-workflow/standards/change-types.md; test/plan-marshall/manage-solution-outline/; test/plan-marshall/plan-marshall/ |
