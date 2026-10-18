<!-- GENERATED FILE — never hand-edit. Rendered from this epic's ledger (status.json, resume_anchor.md, queue/*.json) by `orchestrator regenerate-view --slug live-blockers`. On a merge conflict in this file, do not merge it by hand: merge the source files, run `orchestrator regenerate-view --slug live-blockers`, and `git add` the result. -->

# Queue view: Live Blockers

## START HERE

**Resume anchor**: DRAINING (operator): only PLAN-LB-45 still running. Precondition for next emit (operator): /sync-harnesses + regenerate main executor for the Claude target (currently opencode-target, 163 foreign notations); then verify /plan-marshall-runbook-lane exists and runbook_lane resolve works. All emits use the new skill (operator). After LB-45 lands: set lane=runbook on rows, hand-fill Skills:/Persona: lines, emit PLAN-LB-67 and PLAN-LB-69 first, then PLAN-LB-68 and PLAN-LB-70 (high), PLAN-LB-43 (after LB-68), PLAN-LB-55 (after LB-70), LB-53 after LB-55, PLAN-LB-59, PLAN-LB-51, LB-48/49, LB-44, -58, -41, -46, -57. Open: park LB-48/49/51?
**Phase**: orchestrating
**Running**:
- PLAN-LB-45 (WS-04)
**Queue** (staged, in order):
1. PLAN-LB-41 (WS-05)
2. PLAN-LB-43 (WS-04)
3. PLAN-LB-44 (WS-01)
4. PLAN-LB-46 (WS-05)
5. PLAN-LB-48 (WS-04)
6. PLAN-LB-49 (WS-04)
7. PLAN-LB-51 (WS-04)
8. PLAN-LB-53 (WS-01)
9. PLAN-LB-55 (WS-01)
10. PLAN-LB-57 (WS-05)
11. PLAN-LB-58 (WS-01)
12. PLAN-LB-59 (WS-01)
13. PLAN-LB-67 (WS-04)
14. PLAN-LB-68 (WS-04)
15. PLAN-LB-69 (WS-04)
16. PLAN-LB-70 (WS-03)
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
- PLAN-LB-26 (WS-01) — plan=lb-26-execute-loop-triage — PR 1769 — landing=landings/PLAN-LB-26.md — status: shipped
- PLAN-LB-27 (WS-01) — status: retired
- PLAN-LB-28 (WS-02) — plan=lb-28-java-consumer-repos — PR 1750 — landing=landings/PLAN-LB-28.md — status: shipped
- PLAN-LB-29 (WS-04) — plan=plan-lb-29-harness-sync — PR 1724 — landing=landings/PLAN-LB-29.md — status: shipped
- PLAN-LB-30 (WS-04) — plan=plan-lb-30-org-ci-release — PR 1722 — landing=landings/PLAN-LB-30.md — status: shipped
- PLAN-LB-31 (WS-05) — plan=plan-lb-31-in-house-reviewer — PR 1771 — landing=landings/PLAN-LB-31.md — status: shipped
- PLAN-LB-32 (WS-01) — plan=lb-32-head-dependent-step-refire — PR 1741 — landing=landings/PLAN-LB-32.md — status: shipped
- PLAN-LB-33 (WS-02) — plan=lb-33-leaf-test-scope-and-executor — PR 1745 — landing=landings/PLAN-LB-33.md — status: shipped
- PLAN-LB-34 (WS-01) — status: superseded
- PLAN-LB-35 (WS-01) — status: superseded
- PLAN-LB-36 (WS-01) — status: superseded
- PLAN-LB-37 (WS-01) — plan=lb-37-functional-review — PR 1759 — landing=landings/PLAN-LB-37.md — status: shipped
- PLAN-LB-38 (WS-05) — plan=plan-lb-38-review-gate-and-empty-scope — PR 1752 — landing=landings/PLAN-LB-38.md — status: shipped
- PLAN-LB-39 (WS-04) — plan=antigravity-execution-fidelity — PR 1768 — landing=landings/PLAN-LB-39.md — status: shipped
- PLAN-LB-40 (WS-04) — plan=steward-upgrade-integrity — PR 1774 — landing=landings/PLAN-LB-40.md — status: shipped
- PLAN-LB-42 (WS-01) — plan=plan-lb-42-outline-qgate-integrity — PR 1773 — landing=landings/PLAN-LB-42.md — status: shipped
- PLAN-LB-47 (WS-01) — plan=lb-26-regression-fixes — PR 1778 — landing=landings/PLAN-LB-47.md — status: shipped
- PLAN-LB-50 (WS-04) — plan=implement-plan-lb-50-lb-39-regression-fixes — PR 1777 — landing=landings/PLAN-LB-50.md — status: shipped
- PLAN-LB-52 (WS-01) — plan=oc-lb-52-criteria-and-gate-integrity — PR 1806 — landing=landings/PLAN-LB-52.md — status: shipped
- PLAN-LB-54 (WS-01) — plan=oc-lb-54-lb-42-completion — PR 1788 — landing=landings/PLAN-LB-54.md — status: shipped
- PLAN-LB-56 (WS-04) — plan=implement-plan-lb-56-session-boundary-enforcement — PR 1781 — landing=landings/PLAN-LB-56.md — status: shipped
- PLAN-LB-60 (WS-04) — plan=implement-plan-lb-60-lb-40-regression-fixes — PR 1782 — landing=landings/PLAN-LB-60.md — status: shipped
- PLAN-LB-61 (WS-01) — plan=oc-lb-61-lb-47-hotfix — PR 1787 — landing=landings/PLAN-LB-61.md — status: shipped
- PLAN-LB-62 (WS-04) — plan=oc-lb-62-lb-56-completion — PR 1790 — landing=landings/PLAN-LB-62.md — status: shipped
- PLAN-LB-63 (WS-04) — plan=oc-lb-63-lb-60-completion — PR 1795 — landing=landings/PLAN-LB-63.md — status: shipped
- PLAN-LB-64 (WS-04) — plan=oc-lb-64-lb-50-completion — PR 1794 — landing=landings/PLAN-LB-64.md — status: shipped
- PLAN-LB-65 (WS-04) — plan=oc-lb-65-lb-62-completion — PR 1800 — landing=landings/PLAN-LB-65.md — status: shipped
- PLAN-LB-66 (WS-04) — plan=oc-lb-66-runbook-lane-skill — PR 1808 — landing=landings/PLAN-LB-66.md — status: shipped

## Ordered Queue

| # | Plan | Workstream | Status | Surface (expected) | Lane |
|---|------|------------|--------|--------------------|------|
| 1 | PLAN-LB-41 | WS-05 | staged | marketplace/bundles/plan-marshall/skills/automatic-review/standards/cuioss-review-bot.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/code-review.md; marketplace/targets/README.md; test/plan-marshall/phase-6-finalize/_review_contract_scanners.py; test/plan-marshall/phase-6-finalize/test_code_review_contract.py; test/plan-marshall/phase-6-finalize/test_functional_review_contract.py | plan-marshall |
| 2 | PLAN-LB-43 | WS-04 | staged | marketplace/bundles/plan-marshall/agents/execution-context.md; marketplace/bundles/plan-marshall/skills/extension-api/SKILL.md; marketplace/bundles/plan-marshall/skills/extension-api/scripts/extension_api.py; marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-execution-context-workflow.md; marketplace/bundles/plan-marshall/skills/marshall-steward/SKILL.md; marketplace/bundles/plan-marshall/skills/marshall-steward/references/upgrade-flow.md; marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/upgrade.py; marketplace/bundles/plan-marshall/skills/tools-script-executor/scripts/generate_executor.py; marketplace/bundles/plan-marshall/skills/tools-script-executor/templates/execute-script.py.template; test/marketplace/targets/opencode/test_variant_emitter.py; test/plan-marshall/extension-api/; test/plan-marshall/marshall-steward/; test/plan-marshall/tools-script-executor/ | plan-marshall |
| 3 | PLAN-LB-44 | WS-01 | staged | marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/ci_verify.py; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/ci-verify.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/dispatch-inline-split.md; marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/verification-feedback.md; test/plan-marshall/phase-6-finalize/test_ci_verify_cli.py; test/plan-marshall/phase-6-finalize/test_ci_verify_core.py; test/plan-marshall/phase-6-finalize/test_ci_verify_reporting.py; test/plan-marshall/plan-marshall/test_verification_feedback_producer_vocab.py | plan-marshall |
| 4 | PLAN-LB-45 | WS-04 | running | marketplace/bundles/plan-marshall/skills/phase-1-init/SKILL.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/emit-landing.md; marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/_orchestrator_inbox.py; marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py; marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/landing-payload-spec.md; marketplace/bundles/plan-marshall/skills/plan-orchestrator/workflow/preflight.md; marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/_claude_runtime_impl.py; marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/platform_runtime.py; marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/runtime_info.py; marketplace/bundles/plan-marshall/skills/platform-runtime/standards/contract.md; marketplace/bundles/plan-marshall/skills/platform-runtime/standards/runtime-info.md; test/plan-marshall/plan-orchestrator/test_landing_completeness.py; test/plan-marshall/plan-orchestrator/test_preflight_client_toon.py; test/plan-marshall/platform-runtime/test_runtime_info.py; test/plan-marshall/script-shared/test_target_context.py | plan-marshall |
| 5 | PLAN-LB-46 | WS-05 | staged | marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md; marketplace/bundles/plan-marshall/skills/automatic-review/scripts/bot_registry.py; marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py; marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md; marketplace/bundles/plan-marshall/skills/automatic-review/standards/coderabbit.md; marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py; marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py; test/plan-marshall/automatic-review/; test/plan-marshall/automatic-review/test_bot_registry_patterns.py; test/plan-marshall/automatic-review/test_review_completeness_cli.py; test/plan-marshall/automatic-review/test_trigger_b_stale_set_from_participation.py; test/plan-marshall/workflow-integration-github/test_comments_stage_filters.py; test/plan-marshall/workflow-integration-github/test_comments_stage_refusals.py | plan-marshall |
| 6 | PLAN-LB-48 | WS-04 | staged | doc/developer/opencode.adoc; marketplace/bundles/plan-marshall-opencode/skills/target-rules/standards/opencode-rules.md; marketplace/bundles/plan-marshall/skills/persona-plan-marshall-agent/standards/agent-behavior-rules.md; marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/opencode_runtime.py; marketplace/bundles/plan-marshall/skills/script-shared/scripts/target_context.py; marketplace/bundles/plan-marshall/skills/tools-permission-fix/scripts/permission_fix.py; marketplace/targets/opencode/emitter.py; marketplace/targets/opencode/mapping.json; marketplace/targets/opencode/variant_emitter.py; test/marketplace/targets/opencode/test_body_transforms.py; test/marketplace/targets/opencode/test_emitter.py; test/marketplace/targets/opencode/test_frontmatter.py; test/marketplace/targets/opencode/test_variant_emitter.py; test/plan-marshall/platform-runtime/test_opencode_runtime.py; test/plan-marshall/platform-runtime/test_permission_ops.py; test/plan-marshall/script-shared/test_target_context.py; test/plan-marshall/tools-permission-fix/test_runtime_dsl.py | plan-marshall |
| 7 | PLAN-LB-49 | WS-04 | staged | marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/_opencode_sessions.py; marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/claude_runtime.py; marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/opencode_runtime.py; marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/session_binding.py; marketplace/bundles/plan-marshall/skills/platform-runtime/standards/contract.md; marketplace/bundles/plan-marshall/skills/platform-runtime/standards/no-op-policy.md; test/plan-marshall/manage-metrics/test_manage_metrics_enrich.py; test/plan-marshall/platform-runtime/test_opencode_degrade_paths.py; test/plan-marshall/platform-runtime/test_opencode_runtime.py; test/plan-marshall/platform-runtime/test_opencode_sessions.py | plan-marshall |
| 8 | PLAN-LB-51 | WS-04 | staged | marketplace/bundles/plan-marshall-antigravity/skills/target-rules/standards/antigravity-rules.md; marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/; marketplace/bundles/plan-marshall/skills/persona-plan-marshall-agent/standards/agent-behavior-rules.md; marketplace/bundles/plan-marshall/skills/phase-4-plan/SKILL.md; marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/antigravity_runtime.py; marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/runtime_base.py; marketplace/targets/antigravity/emitter.py; marketplace/targets/antigravity/mapping.json; test/marketplace/targets/antigravity/; test/plan-marshall/phase-4-plan/; test/plan-marshall/platform-runtime/test_antigravity_runtime.py | plan-marshall |
| 9 | PLAN-LB-53 | WS-01 | staged | marketplace/bundles/plan-marshall/skills/manage-status/scripts/; marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md; test/plan-marshall/phase-6-finalize/ | plan-marshall |
| 10 | PLAN-LB-55 | WS-01 | staged | marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md; marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py; marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md; marketplace/bundles/plan-marshall/skills/automatic-review/standards/coderabbit.md; marketplace/bundles/plan-marshall/skills/manage-locks/scripts/merge_lock.py; marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_lifecycle.py; marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/pre-push-quality-gate.md; marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/; marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py; test/plan-marshall/automatic-review/; test/plan-marshall/manage-status/test_transition_boundary_guards.py; test/plan-marshall/phase-6-finalize/ | plan-marshall |
| 11 | PLAN-LB-57 | WS-05 | staged | doc/analysis/; marketplace/bundles/plan-marshall/skills/automatic-review/scripts/; marketplace/bundles/plan-marshall/skills/tools-integration-ci/SKILL.md; marketplace/bundles/plan-marshall/skills/tools-integration-ci/scripts/ci_base.py; marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_ops.py; test/plan-marshall/automatic-review/; test/plan-marshall/tools-integration-ci/ | plan-marshall |
| 12 | PLAN-LB-58 | WS-01 | staged | marketplace/bundles/plan-marshall/skills/build-maven/scripts/; marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/derive_gate_bundles.py; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/pre-push-quality-gate.md; marketplace/bundles/plan-marshall/skills/workflow-integration-sonar/SKILL.md; marketplace/bundles/plan-marshall/skills/workflow-integration-sonar/scripts/sonar.py; marketplace/bundles/pm-documents/skills/ref-asciidoc/scripts/_cmd_verify_links.py; test/plan-marshall/build-maven/; test/plan-marshall/phase-6-finalize/test_derive_gate_bundles.py; test/plan-marshall/workflow-integration-sonar/; test/pm-documents/ref-asciidoc/ | plan-marshall |
| 13 | PLAN-LB-59 | WS-01 | staged | marketplace/bundles/plan-marshall/skills/extension-api/; marketplace/bundles/plan-marshall/skills/manage-adr/SKILL.md; marketplace/bundles/plan-marshall/skills/manage-adr/scripts/manage-adr.py; marketplace/bundles/plan-marshall/skills/manage-personas/scripts/manage_personas.py; marketplace/bundles/plan-marshall/skills/phase-4-plan/SKILL.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/adr-propose.md; marketplace/bundles/pm-dev-java/skills/plan-marshall-plugin/extension.py; test/plan-marshall/manage-adr/; test/plan-marshall/manage-personas/ | plan-marshall |
| 14 | PLAN-LB-67 | WS-04 | staged | .github/workflows/python-verify.yml; doc/developer/opencode.adoc; marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md; marketplace/bundles/plan-marshall/skills/automatic-review/standards/coderabbit.md; marketplace/bundles/plan-marshall/skills/runbook-lane/SKILL.md; marketplace/bundles/plan-marshall/skills/runbook-lane/scripts/runbook_lane.py; test/plan-marshall/runbook-lane/test_runbook_lane.py | plan-marshall |
| 15 | PLAN-LB-68 | WS-04 | staged | .opencode/plugin/guard.js; doc/developer/opencode.adoc; doc/developer/platform-runtime/SKILL.md; doc/developer/platform-runtime/standards/pretooluse-enforcement.md; marketplace/bundles/plan-marshall/skills/marshall-steward/references/marshall-steward/SKILL.md; marketplace/bundles/plan-marshall/skills/marshall-steward/references/upgrade-flow.md; marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/claude_pretooluse_hook.py; marketplace/bundles/plan-marshall/skills/platform-runtime/standards/r5-allowlist.json; marketplace/bundles/plan-marshall/skills/tools-script-executor/SKILL.md; test/plan-marshall/platform-runtime/; test/plan-marshall/workflow-integration-git/test_source_commit_gate_commit_path.py | plan-marshall |
| 16 | PLAN-LB-69 | WS-04 | staged | marketplace/bundles/plan-marshall/skills/persona-plan-orchestrator/standards/orchestration-model.md; marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py; marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/landing-payload-spec.md; marketplace/bundles/plan-marshall/skills/plan-orchestrator/templates/landing-analysis.md; marketplace/bundles/plan-marshall/skills/plan-orchestrator/templates/plan-spec.md; marketplace/bundles/plan-marshall/skills/plan-orchestrator/templates/workflow/cleanup.md; marketplace/bundles/plan-marshall/skills/plan-orchestrator/templates/workflow/decompose.md; marketplace/bundles/plan-marshall/skills/plan-orchestrator/templates/workflow/orchestrate.md; marketplace/bundles/plan-marshall/skills/plan-orchestrator/workflow/analyze.md; marketplace/bundles/plan-marshall/skills/platform-runtime/plan-orchestrator/scripts/; marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/; test/plan-marshall/plan-orchestrator/ | plan-marshall |
| 17 | PLAN-LB-70 | WS-03 | staged | marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/_criteria_snapshot.py; marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_lifecycle.py; marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/review_support.py; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/plan-marshall/workflow/triage.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/review-rubric.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/workflow/functional-review.md; test/plan-marshall/phase-6-finalize/test_criteria_integrity_d1.py | plan-marshall |
