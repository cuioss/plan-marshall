<!-- GENERATED FILE — never hand-edit. Rendered from this epic's ledger (status.json, resume_anchor.md, queue/*.json) by `orchestrator regenerate-view --slug live-blockers`. On a merge conflict in this file, do not merge it by hand: merge the source files, run `orchestrator regenerate-view --slug live-blockers`, and `git add` the result. -->

# Queue view: Live Blockers

## START HERE

**Resume anchor**: 2026-10-13 — DRAINED: inbox empty (19 messages: four PLAN-LB-37 follow-ups, fifteen lessons-routing findings from the pm-mcp-core epic). RUNNING: PLAN-LB-37 functional review + code review — four part-PRs on main (#1754, #1755, #1757, #1758); landing message, consumer rollout (D9/D10) and bot settings (D15) still to come. STAGED, all overlapping PLAN-LB-37: PLAN-LB-31, PLAN-LB-27; PLAN-LB-26 waits for 37. TOP OF THE DECISION LIST: the six CRITICAL Antigravity Open Defects (operator ruling 2026-10-12: Antigravity is the highest priority) — no sub-agent dispatch in phase 5, CLAUDE.md never loaded, zero tokens and no harness stamp (Watch trigger met), maven run executes any plugin goal, incomplete package reported complete with tests weakened, pushed head without mandated gates — none owned; staging them is the operator's call. Also unowned and high: sibling-repository deliverable lifecycle, red CI has no triage route, consumer-repo workflow resolution, deep-lane assessments, 4-plan Q-Gate hash skip, review-bot stale after fix commits. OPERATOR DECISION: ceremony selection versus no-push. SHIPPED: PLAN-LB-14 (#1715), 22 (#1718), 30 (#1722), 23 (#1729), 29 (#1724), 32 (#1741), 24 (#1742), 33 (#1745), 28 (#1750), 25 (#1751), 38 (#1752), plus the standalone self-review plan. SUPERSEDED: 34, 35, 36. OPERATOR ACTIONS: re-run architecture discovery in the Maven consumers; regenerate executors on each machine. OPEN: PLAN-LB-32 re-fire design; root opencode.json; registry repin. See epic.md.
**Phase**: orchestrating
**Running**:
- PLAN-LB-37 (WS-01)
**Queue** (staged, in order):
1. PLAN-LB-26 (WS-01)
2. PLAN-LB-27 (WS-01)
3. PLAN-LB-31 (WS-05)
- PLAN-LB-14 (WS-03) — plan=lb-14-launch-gate-scope — PR 1715 — landing=landings/PLAN-LB-14.md — status: shipped
- PLAN-LB-01 (WS-01) — status: superseded
- PLAN-LB-04 (WS-01) — status: superseded
- PLAN-LB-07 (WS-01) — status: superseded
- PLAN-LB-03 (WS-01) — status: superseded
- PLAN-LB-02 (WS-01) — status: superseded
- PLAN-LB-08 (WS-01) — status: superseded
- PLAN-LB-06 (WS-01) — status: superseded
- PLAN-LB-05 (WS-01) — status: superseded
- PLAN-LB-09 (WS-01) — status: superseded
- PLAN-LB-10 (WS-01) — status: superseded
- PLAN-LB-11 (WS-01) — status: superseded
- PLAN-LB-12 (WS-02) — status: superseded
- PLAN-LB-13 (WS-02) — status: superseded
- PLAN-LB-15 (WS-04) — status: superseded
- PLAN-LB-17 (WS-04) — status: superseded
- PLAN-LB-16 (WS-04) — status: superseded
- PLAN-LB-18 (WS-05) — status: superseded
- PLAN-LB-19 (WS-05) — status: superseded
- PLAN-LB-21 (WS-05) — status: superseded
- PLAN-LB-20 (WS-05) — status: superseded
- PLAN-LB-22 (WS-01) — plan=lb-22-finalize-loop-control — PR 1718 — landing=landings/PLAN-LB-22.md — status: shipped
- PLAN-LB-23 (WS-02) — plan=lb-23-verify-builds — PR 1729 — landing=landings/PLAN-LB-23.md — status: shipped
- PLAN-LB-24 (WS-05) — plan=lb-24-review-step — PR 1742 — landing=landings/PLAN-LB-24.md — status: shipped
- PLAN-LB-25 (WS-01) — plan=lb-25-phase-and-merge-gates — PR 1751 — landing=landings/PLAN-LB-25.md — status: shipped
- PLAN-LB-28 (WS-02) — plan=lb-28-java-consumer-repos — PR 1750 — landing=landings/PLAN-LB-28.md — status: shipped
- PLAN-LB-29 (WS-04) — plan=plan-lb-29-harness-sync — PR 1724 — landing=landings/PLAN-LB-29.md — status: shipped
- PLAN-LB-30 (WS-04) — plan=plan-lb-30-org-ci-release — PR 1722 — landing=landings/PLAN-LB-30.md — status: shipped
- PLAN-LB-32 (WS-01) — plan=lb-32-head-dependent-step-refire — PR 1741 — landing=landings/PLAN-LB-32.md — status: shipped
- PLAN-LB-33 (WS-02) — plan=lb-33-leaf-test-scope-and-executor — PR 1745 — landing=landings/PLAN-LB-33.md — status: shipped
- PLAN-LB-34 (WS-01) — status: superseded
- PLAN-LB-35 (WS-01) — status: superseded
- PLAN-LB-36 (WS-01) — status: superseded
- PLAN-LB-38 (WS-05) — plan=plan-lb-38-review-gate-and-empty-scope — PR 1752 — landing=landings/PLAN-LB-38.md — status: shipped

## Ordered Queue

| # | Plan | Workstream | Status | Surface (expected) |
|---|------|------------|--------|--------------------|
| 1 | PLAN-LB-26 | WS-01 | staged | marketplace/bundles/plan-marshall/skills/build-server-client/SKILL.md; marketplace/bundles/plan-marshall/skills/manage-findings/SKILL.md; marketplace/bundles/plan-marshall/skills/manage-findings/scripts/_findings_core.py; marketplace/bundles/plan-marshall/skills/manage-findings/scripts/manage-findings.py; marketplace/bundles/plan-marshall/skills/manage-findings/standards/jsonl-format.md; marketplace/bundles/plan-marshall/skills/manage-tasks/SKILL.md; marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_cmd_qgate_mechanical.py; marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_cmd_step.py; marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_tasks_core.py; marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_tasks_crud.py; marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_tasks_envelope.py; marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_tasks_query.py; marketplace/bundles/plan-marshall/skills/manage-tasks/standards/task-contract.md; marketplace/bundles/plan-marshall/skills/phase-5-execute/SKILL.md; marketplace/bundles/plan-marshall/skills/phase-5-execute/scripts/scope_creep_check.py; marketplace/bundles/plan-marshall/skills/phase-5-execute/standards/canonical_verify.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md; marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/await-long-running.md; marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/execution.md; marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/q-gate-validation.md; marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/triage.md; marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/verification-feedback.md; marketplace/bundles/plan-marshall/skills/ref-workflow-architecture/standards/agents.md; marketplace/bundles/plan-marshall/skills/ref-workflow-architecture/standards/phase-lifecycle.md; marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_execute_factory.py; test/plan-marshall/manage-findings/_findings_store_fixtures.py; test/plan-marshall/manage-findings/test_findings_store_add.py; test/plan-marshall/manage-findings/test_findings_store_resolve.py; test/plan-marshall/manage-findings/test_manage_findings_qgate.py; test/plan-marshall/manage-findings/test_qgate_resolution_survives_reemission.py; test/plan-marshall/manage-tasks/test_manage_tasks_add.py; test/plan-marshall/manage-tasks/test_manage_tasks_batch_add_batch.py; test/plan-marshall/manage-tasks/test_manage_tasks_finalize_step.py; test/plan-marshall/manage-tasks/test_manage_tasks_get.py; test/plan-marshall/manage-tasks/test_manage_tasks_next.py; test/plan-marshall/manage-tasks/test_manage_tasks_qgate_mechanical.py; test/plan-marshall/phase-5-execute/test_dispatch_envelope_contracts.py; test/plan-marshall/phase-5-execute/test_scope_creep_check.py; test/plan-marshall/script-shared/test_build_execute_factory.py |
| 2 | PLAN-LB-27 | WS-01 | staged | marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-finalize-step.md; marketplace/bundles/plan-marshall/skills/manage-findings/SKILL.md; marketplace/bundles/plan-marshall/skills/manage-findings/standards/jsonl-format.md; marketplace/bundles/plan-marshall/skills/manage-references/scripts/_references_core.py; marketplace/bundles/plan-marshall/skills/manage-references/scripts/_references_crud.py; marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_task_artifacts.py; marketplace/bundles/plan-marshall/skills/persona-security-expert/standards/secrets-handling.md; marketplace/bundles/plan-marshall/skills/phase-5-execute/SKILL.md; marketplace/bundles/plan-marshall/skills/phase-5-execute/scripts/scope_creep_check.py; marketplace/bundles/plan-marshall/skills/phase-5-execute/standards/operations.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md; marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/execution.md; marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/triage.md; marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/verification-feedback.md; marketplace/bundles/plan-marshall/skills/tools-file-ops/scripts/constants.py; marketplace/bundles/plan-marshall/skills/workflow-integration-git/SKILL.md; marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/git-workflow.py; marketplace/bundles/plan-marshall/skills/workflow-integration-git/standards/artifact-patterns.json; marketplace/bundles/plan-marshall/skills/workflow-integration-git/standards/git-commit-standards.md; test/plan-marshall/manage-findings/test_finding_type_literal_population.py; test/plan-marshall/phase-5-execute/test_qgate_persist_contract.py; test/plan-marshall/phase-5-execute/test_scope_creep_check.py; test/plan-marshall/phase-5-execute/test_scope_creep_could_not_look.py; test/plan-marshall/phase-5-execute/test_scope_creep_merge_base.py; test/plan-marshall/workflow-integration-git/test_commit_staging_doc_contract.py; test/plan-marshall/workflow-integration-git/test_git_workflow_artifacts.py; test/plan-marshall/workflow-integration-git/test_git_workflow_stage.py |
| 3 | PLAN-LB-31 | WS-05 | staged | .plan/marshal.json; doc/analysis/in-house-reviewer-efficacy.md; marketplace/bundles/plan-marshall/skills/automatic-review/standards/cuioss-review-bot.md; test/plan-marshall/automatic-review/test_bot_participation_contract_config.py |
| 4 | PLAN-LB-37 | WS-01 | running | .plan/marshal.json; CLAUDE.md; README.md; marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-self-review-surfacing.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/functional-review-rubric.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/functional-review.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md; marketplace/bundles/pm-plugin-development/.claude-plugin/plugin.json; marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/**; test/plan-marshall/manage-execution-manifest/; test/plan-marshall/marshall-steward/; test/plan-marshall/phase-6-finalize/; test/pm-plugin-development/ext-self-review-plan-marshall/** |
