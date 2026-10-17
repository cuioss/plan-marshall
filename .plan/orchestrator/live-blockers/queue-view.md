<!-- GENERATED FILE — never hand-edit. Rendered from this epic's ledger (status.json, resume_anchor.md, queue/*.json) by `orchestrator regenerate-view --slug live-blockers`. On a merge conflict in this file, do not merge it by hand: merge the source files, run `orchestrator regenerate-view --slug live-blockers`, and `git add` the result. -->

# Queue view: Live Blockers

## START HERE

**Resume anchor**: DRAIN MODE (operator 2026-10-16): no new emits. Remaining: PLAN-LB-54 (running, runbook lane). Analyze it when it lands. AFTER ANALYZING IT: give the operator the opencode.db approval-clearing instructions — (1) close OpenCode, 'opencode service stop', 'opencode service status'; (2) cp ~/.local/share/opencode/opencode.db ~/.local/share/opencode/opencode.db.bak-<date>; (3) plain terminal python3 sqlite3: DELETE FROM permission WHERE project_id='c33f8c265a91af24505bcd7a364a3c354739ada0' AND action='shell' (expect 8); (4) 'opencode service start'; (5) orchestrator verifies read-only; 'allow once' from then on. ALSO remind: rotate the OpenCode service credential (~/.config/opencode/service.json leaked by PLAN-LB-62). Then resume emits: PLAN-LB-65 + PLAN-LB-64 (critical), PLAN-LB-63, LB-52/55/53, LB-48/45/49, LB-51, LB-43/44/58/59/41/46/57. Operator also owes: harness sync from a plain terminal; #1777/#1787/#1790 kept unless told otherwise.
**Phase**: orchestrating
**Running**:
- PLAN-LB-54 (WS-01)
**Queue** (staged, in order):
1. PLAN-LB-41 (WS-05)
2. PLAN-LB-43 (WS-04)
3. PLAN-LB-44 (WS-01)
4. PLAN-LB-45 (WS-04)
5. PLAN-LB-46 (WS-05)
6. PLAN-LB-48 (WS-04)
7. PLAN-LB-49 (WS-04)
8. PLAN-LB-51 (WS-04)
9. PLAN-LB-52 (WS-01)
10. PLAN-LB-53 (WS-01)
11. PLAN-LB-55 (WS-01)
12. PLAN-LB-57 (WS-05)
13. PLAN-LB-58 (WS-01)
14. PLAN-LB-59 (WS-01)
15. PLAN-LB-63 (WS-04)
16. PLAN-LB-64 (WS-04)
17. PLAN-LB-65 (WS-04)
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
- PLAN-LB-56 (WS-04) — plan=implement-plan-lb-56-session-boundary-enforcement — PR 1781 — landing=landings/PLAN-LB-56.md — status: shipped
- PLAN-LB-60 (WS-04) — plan=implement-plan-lb-60-lb-40-regression-fixes — PR 1782 — landing=landings/PLAN-LB-60.md — status: shipped
- PLAN-LB-61 (WS-01) — plan=oc-lb-61-lb-47-hotfix — PR 1787 — landing=landings/PLAN-LB-61.md — status: shipped
- PLAN-LB-62 (WS-04) — plan=oc-lb-62-lb-56-completion — PR 1790 — landing=landings/PLAN-LB-62.md — status: shipped

## Ordered Queue

| # | Plan | Workstream | Status | Surface (expected) |
|---|------|------------|--------|--------------------|
| 1 | PLAN-LB-41 | WS-05 | staged | marketplace/bundles/plan-marshall/skills/automatic-review/standards/cuioss-review-bot.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/code-review.md; marketplace/targets/README.md; test/plan-marshall/phase-6-finalize/_review_contract_scanners.py; test/plan-marshall/phase-6-finalize/test_code_review_contract.py; test/plan-marshall/phase-6-finalize/test_functional_review_contract.py |
| 2 | PLAN-LB-43 | WS-04 | staged | marketplace/bundles/plan-marshall/agents/execution-context.md; marketplace/bundles/plan-marshall/skills/extension-api/SKILL.md; marketplace/bundles/plan-marshall/skills/extension-api/scripts/extension_api.py; marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-execution-context-workflow.md; test/marketplace/targets/opencode/test_variant_emitter.py; test/plan-marshall/extension-api/ |
| 3 | PLAN-LB-44 | WS-01 | staged | marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/ci_verify.py; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/ci-verify.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/dispatch-inline-split.md; marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/verification-feedback.md; test/plan-marshall/phase-6-finalize/test_ci_verify_cli.py; test/plan-marshall/phase-6-finalize/test_ci_verify_core.py; test/plan-marshall/phase-6-finalize/test_ci_verify_reporting.py; test/plan-marshall/plan-marshall/test_verification_feedback_producer_vocab.py |
| 4 | PLAN-LB-45 | WS-04 | staged | marketplace/bundles/plan-marshall/skills/phase-1-init/SKILL.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/emit-landing.md; marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/_orchestrator_inbox.py; marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py; marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/landing-payload-spec.md; marketplace/bundles/plan-marshall/skills/plan-orchestrator/workflow/preflight.md; marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/_claude_runtime_impl.py; marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/platform_runtime.py; marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/runtime_info.py; marketplace/bundles/plan-marshall/skills/platform-runtime/standards/contract.md; marketplace/bundles/plan-marshall/skills/platform-runtime/standards/runtime-info.md; test/plan-marshall/plan-orchestrator/test_landing_completeness.py; test/plan-marshall/plan-orchestrator/test_preflight_client_toon.py; test/plan-marshall/platform-runtime/test_runtime_info.py; test/plan-marshall/script-shared/test_target_context.py |
| 5 | PLAN-LB-46 | WS-05 | staged | marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md; marketplace/bundles/plan-marshall/skills/automatic-review/scripts/bot_registry.py; marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py; marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md; marketplace/bundles/plan-marshall/skills/automatic-review/standards/coderabbit.md; marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py; marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py; test/plan-marshall/automatic-review/; test/plan-marshall/automatic-review/test_bot_registry_patterns.py; test/plan-marshall/automatic-review/test_review_completeness_cli.py; test/plan-marshall/automatic-review/test_trigger_b_stale_set_from_participation.py; test/plan-marshall/workflow-integration-github/test_comments_stage_filters.py; test/plan-marshall/workflow-integration-github/test_comments_stage_refusals.py |
| 6 | PLAN-LB-48 | WS-04 | staged | doc/developer/opencode.adoc; marketplace/bundles/plan-marshall-opencode/skills/target-rules/standards/opencode-rules.md; marketplace/bundles/plan-marshall/skills/persona-plan-marshall-agent/standards/agent-behavior-rules.md; marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/opencode_runtime.py; marketplace/bundles/plan-marshall/skills/script-shared/scripts/target_context.py; marketplace/bundles/plan-marshall/skills/tools-permission-fix/scripts/permission_fix.py; marketplace/targets/opencode/emitter.py; marketplace/targets/opencode/mapping.json; marketplace/targets/opencode/variant_emitter.py; test/marketplace/targets/opencode/test_body_transforms.py; test/marketplace/targets/opencode/test_emitter.py; test/marketplace/targets/opencode/test_frontmatter.py; test/marketplace/targets/opencode/test_variant_emitter.py; test/plan-marshall/platform-runtime/test_opencode_runtime.py; test/plan-marshall/platform-runtime/test_permission_ops.py; test/plan-marshall/script-shared/test_target_context.py; test/plan-marshall/tools-permission-fix/test_runtime_dsl.py |
| 7 | PLAN-LB-49 | WS-04 | staged | marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/_opencode_sessions.py; marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/claude_runtime.py; marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/opencode_runtime.py; marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/session_binding.py; marketplace/bundles/plan-marshall/skills/platform-runtime/standards/contract.md; marketplace/bundles/plan-marshall/skills/platform-runtime/standards/no-op-policy.md; test/plan-marshall/manage-metrics/test_manage_metrics_enrich.py; test/plan-marshall/platform-runtime/test_opencode_degrade_paths.py; test/plan-marshall/platform-runtime/test_opencode_runtime.py; test/plan-marshall/platform-runtime/test_opencode_sessions.py |
| 8 | PLAN-LB-51 | WS-04 | staged | marketplace/bundles/plan-marshall-antigravity/skills/target-rules/standards/antigravity-rules.md; marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/; marketplace/bundles/plan-marshall/skills/persona-plan-marshall-agent/standards/agent-behavior-rules.md; marketplace/bundles/plan-marshall/skills/phase-4-plan/SKILL.md; marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/antigravity_runtime.py; marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/runtime_base.py; marketplace/targets/antigravity/emitter.py; marketplace/targets/antigravity/mapping.json; test/marketplace/targets/antigravity/; test/plan-marshall/phase-4-plan/; test/plan-marshall/platform-runtime/test_antigravity_runtime.py |
| 9 | PLAN-LB-52 | WS-01 | staged | marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/; marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/review-rubric.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/functional-review.md; marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/triage.md; test/plan-marshall/phase-6-finalize/ |
| 10 | PLAN-LB-53 | WS-01 | staged | marketplace/bundles/plan-marshall/skills/manage-status/scripts/; marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md; test/plan-marshall/phase-6-finalize/ |
| 11 | PLAN-LB-54 | WS-01 | running | marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_domain_narrow.py; marketplace/bundles/plan-marshall/skills/manage-solution-outline/SKILL.md; marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/manage-solution-outline.py; marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/planning-outline.md; marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/q-gate-validation.md; test/plan-marshall/manage-config/test_cmd_domain_narrow.py; test/plan-marshall/manage-solution-outline/test_manage_solution_outline_cli.py; test/plan-marshall/q-gate-validation-agent/test_qgate_outline_integrity_regression.py |
| 12 | PLAN-LB-55 | WS-01 | staged | marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md; marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py; marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md; marketplace/bundles/plan-marshall/skills/automatic-review/standards/coderabbit.md; marketplace/bundles/plan-marshall/skills/manage-locks/scripts/merge_lock.py; marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_lifecycle.py; marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/pre-push-quality-gate.md; marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/; marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py; test/plan-marshall/automatic-review/; test/plan-marshall/manage-status/test_transition_boundary_guards.py; test/plan-marshall/phase-6-finalize/ |
| 13 | PLAN-LB-57 | WS-05 | staged | doc/analysis/; marketplace/bundles/plan-marshall/skills/automatic-review/scripts/; marketplace/bundles/plan-marshall/skills/tools-integration-ci/SKILL.md; marketplace/bundles/plan-marshall/skills/tools-integration-ci/scripts/ci_base.py; marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_ops.py; test/plan-marshall/automatic-review/; test/plan-marshall/tools-integration-ci/ |
| 14 | PLAN-LB-58 | WS-01 | staged | marketplace/bundles/plan-marshall/skills/build-maven/scripts/; marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/derive_gate_bundles.py; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/pre-push-quality-gate.md; marketplace/bundles/plan-marshall/skills/workflow-integration-sonar/SKILL.md; marketplace/bundles/plan-marshall/skills/workflow-integration-sonar/scripts/sonar.py; marketplace/bundles/pm-documents/skills/ref-asciidoc/scripts/_cmd_verify_links.py; test/plan-marshall/build-maven/; test/plan-marshall/phase-6-finalize/test_derive_gate_bundles.py; test/plan-marshall/workflow-integration-sonar/; test/pm-documents/ref-asciidoc/ |
| 15 | PLAN-LB-59 | WS-01 | staged | marketplace/bundles/plan-marshall/skills/extension-api/; marketplace/bundles/plan-marshall/skills/manage-adr/SKILL.md; marketplace/bundles/plan-marshall/skills/manage-adr/scripts/manage-adr.py; marketplace/bundles/plan-marshall/skills/manage-personas/scripts/manage_personas.py; marketplace/bundles/plan-marshall/skills/phase-4-plan/SKILL.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/adr-propose.md; marketplace/bundles/pm-dev-java/skills/plan-marshall-plugin/extension.py; test/plan-marshall/manage-adr/; test/plan-marshall/manage-personas/ |
| 16 | PLAN-LB-63 | WS-04 | staged | marketplace/bundles/plan-marshall/skills/extension-api/scripts/extension_discovery.py; marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_quality_phases.py; marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_sync_defaults.py; marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/upgrade.py; test/plan-marshall/extension-api/test_extension_discovery_behavior.py; test/plan-marshall/manage-config/test_sync_defaults.py; test/plan-marshall/marshall-steward/test_upgrade.py |
| 17 | PLAN-LB-64 | WS-04 | staged | marketplace/bundles/plan-marshall-antigravity/skills/target-rules/standards/antigravity-rules.md; marketplace/bundles/plan-marshall-opencode/skills/target-rules/standards/opencode-rules.md; marketplace/bundles/plan-marshall/skills/marshall-steward/references/upgrade-flow.md; marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/configure_harness.py; marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/antigravity_runtime.py; marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/opencode_runtime.py; test/plan-marshall/marshall-steward/test_harness_config.py; test/plan-marshall/platform-runtime/test_antigravity_runtime.py; test/plan-marshall/platform-runtime/test_opencode_runtime.py |
| 18 | PLAN-LB-65 | WS-04 | staged | .opencode/plugin/guard.js; marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/claude_pretooluse_hook.py; marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/opencode_runtime.py; marketplace/bundles/plan-marshall/skills/platform-runtime/standards/r5-allowlist.json; marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/git-workflow.py; test/plan-marshall/platform-runtime/_guard_node_harness.py; test/plan-marshall/platform-runtime/test_claude_pretooluse_hook.py; test/plan-marshall/platform-runtime/test_guard_hook_parity.py; test/plan-marshall/platform-runtime/test_opencode_runtime.py; test/plan-marshall/workflow-integration-git/test_source_commit_gate_commit_path.py |
