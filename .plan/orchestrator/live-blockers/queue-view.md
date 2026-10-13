<!-- GENERATED FILE — never hand-edit. Rendered from this epic's ledger (status.json, resume_anchor.md, queue/*.json) by `orchestrator regenerate-view --slug live-blockers`. On a merge conflict in this file, do not merge it by hand: merge the source files, run `orchestrator regenerate-view --slug live-blockers`, and `git add` the result. -->

# Queue view: Live Blockers

## START HERE

**Resume anchor**: 2026-10-13 - PLAN-LB-26 execute-loop-triage LAUNCHED on operator implement command (overlap with live antigravity-execution-fidelity accepted). NEXT: run plan lifecycle init from the staged spec, stamp queue plan_marshall_plan_id. PLAN-LB-39 and PLAN-LB-31 remain emitted awaiting launch; PLAN-LB-27 stays staged until LB-26 lands. At landing analyze adversarially per epic.md OpenCode watch.
**Phase**: orchestrating
**Queue** (staged, in order):
1. PLAN-LB-27 (WS-01)
2. PLAN-LB-31 (WS-05)
3. PLAN-LB-39 (WS-04)
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
- PLAN-LB-26 (WS-01) — status: launched
- PLAN-LB-28 (WS-02) — plan=lb-28-java-consumer-repos — PR 1750 — landing=landings/PLAN-LB-28.md — status: shipped
- PLAN-LB-29 (WS-04) — plan=plan-lb-29-harness-sync — PR 1724 — landing=landings/PLAN-LB-29.md — status: shipped
- PLAN-LB-30 (WS-04) — plan=plan-lb-30-org-ci-release — PR 1722 — landing=landings/PLAN-LB-30.md — status: shipped
- PLAN-LB-32 (WS-01) — plan=lb-32-head-dependent-step-refire — PR 1741 — landing=landings/PLAN-LB-32.md — status: shipped
- PLAN-LB-33 (WS-02) — plan=lb-33-leaf-test-scope-and-executor — PR 1745 — landing=landings/PLAN-LB-33.md — status: shipped
- PLAN-LB-34 (WS-01) — status: superseded
- PLAN-LB-35 (WS-01) — status: superseded
- PLAN-LB-36 (WS-01) — status: superseded
- PLAN-LB-37 (WS-01) — plan=lb-37-functional-review — PR 1759 — landing=landings/PLAN-LB-37.md — status: shipped
- PLAN-LB-38 (WS-05) — plan=plan-lb-38-review-gate-and-empty-scope — PR 1752 — landing=landings/PLAN-LB-38.md — status: shipped

## Ordered Queue

| # | Plan | Workstream | Status | Surface (expected) |
|---|------|------------|--------|--------------------|
| 1 | PLAN-LB-26 | WS-01 | launched | marketplace/bundles/plan-marshall/skills/build-server-client/SKILL.md; marketplace/bundles/plan-marshall/skills/manage-findings/SKILL.md; marketplace/bundles/plan-marshall/skills/manage-findings/scripts/_findings_core.py; marketplace/bundles/plan-marshall/skills/manage-findings/scripts/manage-findings.py; marketplace/bundles/plan-marshall/skills/manage-findings/standards/jsonl-format.md; marketplace/bundles/plan-marshall/skills/manage-tasks/SKILL.md; marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_cmd_qgate_mechanical.py; marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_cmd_step.py; marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_tasks_core.py; marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_tasks_crud.py; marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_tasks_envelope.py; marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_tasks_query.py; marketplace/bundles/plan-marshall/skills/manage-tasks/standards/task-contract.md; marketplace/bundles/plan-marshall/skills/phase-5-execute/SKILL.md; marketplace/bundles/plan-marshall/skills/phase-5-execute/scripts/scope_creep_check.py; marketplace/bundles/plan-marshall/skills/phase-5-execute/standards/canonical_verify.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md; marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/await-long-running.md; marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/execution.md; marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/q-gate-validation.md; marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/triage.md; marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/verification-feedback.md; marketplace/bundles/plan-marshall/skills/ref-workflow-architecture/standards/agents.md; marketplace/bundles/plan-marshall/skills/ref-workflow-architecture/standards/phase-lifecycle.md; marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_execute_factory.py; test/plan-marshall/manage-findings/_findings_store_fixtures.py; test/plan-marshall/manage-findings/test_findings_store_add.py; test/plan-marshall/manage-findings/test_findings_store_resolve.py; test/plan-marshall/manage-findings/test_manage_findings_qgate.py; test/plan-marshall/manage-findings/test_qgate_resolution_survives_reemission.py; test/plan-marshall/manage-tasks/test_manage_tasks_add.py; test/plan-marshall/manage-tasks/test_manage_tasks_batch_add_batch.py; test/plan-marshall/manage-tasks/test_manage_tasks_finalize_step.py; test/plan-marshall/manage-tasks/test_manage_tasks_get.py; test/plan-marshall/manage-tasks/test_manage_tasks_next.py; test/plan-marshall/manage-tasks/test_manage_tasks_qgate_mechanical.py; test/plan-marshall/phase-5-execute/test_dispatch_envelope_contracts.py; test/plan-marshall/phase-5-execute/test_scope_creep_check.py; test/plan-marshall/script-shared/test_build_execute_factory.py |
| 2 | PLAN-LB-27 | WS-01 | staged | marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-finalize-step.md; marketplace/bundles/plan-marshall/skills/manage-findings/SKILL.md; marketplace/bundles/plan-marshall/skills/manage-findings/standards/jsonl-format.md; marketplace/bundles/plan-marshall/skills/manage-references/scripts/_references_core.py; marketplace/bundles/plan-marshall/skills/manage-references/scripts/_references_crud.py; marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_task_artifacts.py; marketplace/bundles/plan-marshall/skills/persona-security-expert/standards/secrets-handling.md; marketplace/bundles/plan-marshall/skills/phase-5-execute/SKILL.md; marketplace/bundles/plan-marshall/skills/phase-5-execute/scripts/scope_creep_check.py; marketplace/bundles/plan-marshall/skills/phase-5-execute/standards/operations.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md; marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/execution.md; marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/triage.md; marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/verification-feedback.md; marketplace/bundles/plan-marshall/skills/tools-file-ops/scripts/constants.py; marketplace/bundles/plan-marshall/skills/workflow-integration-git/SKILL.md; marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/git-workflow.py; marketplace/bundles/plan-marshall/skills/workflow-integration-git/standards/artifact-patterns.json; marketplace/bundles/plan-marshall/skills/workflow-integration-git/standards/git-commit-standards.md; test/plan-marshall/manage-findings/test_finding_type_literal_population.py; test/plan-marshall/phase-5-execute/test_qgate_persist_contract.py; test/plan-marshall/phase-5-execute/test_scope_creep_check.py; test/plan-marshall/phase-5-execute/test_scope_creep_could_not_look.py; test/plan-marshall/phase-5-execute/test_scope_creep_merge_base.py; test/plan-marshall/workflow-integration-git/test_commit_staging_doc_contract.py; test/plan-marshall/workflow-integration-git/test_git_workflow_artifacts.py; test/plan-marshall/workflow-integration-git/test_git_workflow_stage.py |
| 3 | PLAN-LB-31 | WS-05 | staged | .plan/marshal.json; doc/analysis/in-house-reviewer-efficacy.md; marketplace/bundles/plan-marshall/skills/automatic-review/standards/cuioss-review-bot.md; test/plan-marshall/automatic-review/test_bot_participation_contract_config.py |
| 4 | PLAN-LB-39 | WS-04 | staged | marketplace/bundles/plan-marshall-antigravity/skills/target-rules/standards/antigravity-rules.md; marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/; marketplace/bundles/plan-marshall/skills/manage-metrics/scripts/manage-metrics.py; marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_lifecycle.py; marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_freshness_crosscheck.py; marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/upgrade.py; marketplace/bundles/plan-marshall/skills/persona-plan-marshall-agent/SKILL.md; marketplace/bundles/plan-marshall/skills/phase-1-init/SKILL.md; marketplace/bundles/plan-marshall/skills/phase-4-plan/SKILL.md; marketplace/bundles/plan-marshall/skills/phase-5-execute/SKILL.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/emit-landing.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/pre-push-quality-gate.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/record-metrics.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/functional-review.md; marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/execution.md; marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/triage.md; marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/landing-payload-spec.md; marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/antigravity_runtime.py; marketplace/bundles/plan-marshall/skills/platform-runtime/standards/contract.md; marketplace/targets/antigravity/emitter.py; marketplace/targets/antigravity/mapping.json; marketplace/targets/opencode/; test/marketplace/targets/; test/plan-marshall/manage-execution-manifest/; test/plan-marshall/manage-metrics/; test/plan-marshall/manage-status/; test/plan-marshall/phase-6-finalize/; test/plan-marshall/platform-runtime/ |
