# History: Truthful Signals & Machinery Integrity

slug: truthful-signals
closed: 2026-10-07

> Frozen record of the epic at close. `epic.md`, the queue rows, the specs, the landings, the
> inbox and the logs stay in this tree untouched; this file is the summary a later reader
> starts from. Close freezes and never deletes.

## Closing rationale

Closed by operator instruction on 2026-10-07. plan-marshall's workflow machinery is being
rewritten as plan-marshall-mcp, which supersedes most of this epic's staged and parked work.
The work that still matters for plan-marshall itself — defects that block or mislead a normal
run today, and high-priority work on things the rewrite does not replace — was cut into the
successor epic `live-blockers` (`.plan/orchestrator/live-blockers/`). Everything else was
left where it stood.

## Vision as pursued

Close the recurring defect family in which a tool, gate, or hand-off reports a confident
clean/complete signal while silently suppressing the caveat that makes it wrong — plus the adjacent
family in which machinery silently loses information it was handed. Fix each instance at the tool
layer rather than papering over symptoms. Done at the epic level means: every staged plan shipped or
explicitly retired, no open instance of the flagship archetype, and the closing rename (PLAN-TRUTH-015)
landed.

2026-09-21: `quality-aspect` (the finalize-lane instance of this same defect archetype)
merged in. Its 15 live plans joined this queue, renumbered PLAN-205..221 as workstreams
`WS-QA-01` through `WS-QA-09`. Its terminal history (3 shipped rows, renumbered
PLAN-204/210/212) and quality-aspect's own `history.md` are in the
`truthful-signals-26-09-21` archive, alongside this epic's own 196 terminal rows split
out on the same date.

## Final state

The two blocks below are the generated view at close, verbatim.

### Queue view: Truthful Signals & Machinery Integrity

#### START HERE

**Resume anchor**: 2026-10-05: cui-http drain 014-020 (4 lessons 17-001..004, 3 discards). Live staged 8. Next: land ledger, then emit PLAN-TRUTH-187/172/186 when operator confirms launch.
**Phase**: orchestrating
**Parked**:
- PLAN-TRUTH-145 (WS-01)
- PLAN-TRUTH-146 (WS-01)
- PLAN-TRUTH-149 (WS-01)
- PLAN-TRUTH-150 (WS-01)
- PLAN-TRUTH-151 (WS-01)
- PLAN-TRUTH-153 (WS-01)
- PLAN-TRUTH-154 (WS-01)
- PLAN-TRUTH-155 (WS-01)
- PLAN-TRUTH-156 (WS-01)
- PLAN-TRUTH-158 (WS-01)
- PLAN-TRUTH-159 (WS-01)
- PLAN-TRUTH-160 (WS-01)
- PLAN-TRUTH-162 (WS-01)
- PLAN-TRUTH-163 (WS-01)
- PLAN-TRUTH-164 (WS-01)
- PLAN-TRUTH-165 (WS-01)
- PLAN-TRUTH-169 (WS-01)
- PLAN-TRUTH-170 (WS-01)
- PLAN-TRUTH-171 (WS-01)
- PLAN-TRUTH-173 (WS-01)
- PLAN-TRUTH-174 (WS-01)
- PLAN-TRUTH-175 (WS-01)
- PLAN-TRUTH-176 (WS-01)
- PLAN-TRUTH-177 (WS-01)
- PLAN-205 (WS-QA-01)
- PLAN-206 (WS-QA-02)
- PLAN-207 (WS-QA-02)
- PLAN-208 (WS-QA-03)
- PLAN-209 (WS-QA-03)
- PLAN-213 (WS-QA-06)
- PLAN-214 (WS-QA-06)
- PLAN-215 (WS-QA-06)
- PLAN-216 (WS-QA-07)
- PLAN-217 (WS-QA-07)
- PLAN-218 (WS-QA-09)
- PLAN-219 (WS-QA-08)
- PLAN-220 (WS-QA-08)
- PLAN-221 (WS-QA-02)
- PLAN-TRUTH-180 (WS-01)
**Queue** (staged, in order):
1. PLAN-TRUTH-181 (WS-01)
2. PLAN-TRUTH-182 (WS-01)
3. PLAN-TRUTH-183 (WS-01)
4. PLAN-TRUTH-184 (WS-01)
5. PLAN-TRUTH-185 (WS-01)
6. PLAN-TRUTH-187 (WS-01)
- PLAN-TRUTH-147 (WS-01) — plan=truth-147-lane-reports-green — PR 1599 — landing=landings/PLAN-TRUTH-147.md — status: shipped
- PLAN-TRUTH-161 (WS-01) — plan=truth-161-adr-number-allocation — PR 1586 — landing=landings/PLAN-TRUTH-161.md — status: shipped
- PLAN-TRUTH-167 (WS-01) — status: superseded
- PLAN-TRUTH-168 (WS-01) — plan=truth-168-sync-defaults-reverting-remove — PR 1674 — landing=landings/PLAN-TRUTH-168.md — status: shipped
- PLAN-TRUTH-172 (WS-01) — status: transferred
- PLAN-211 (WS-QA-04) — plan=implement-plan-211-baseline-reconcile — PR 1675 — landing=landings/PLAN-211.md — status: shipped
- PLAN-TRUTH-178 (WS-01) — status: transferred
- PLAN-TRUTH-179 (WS-01) — plan=truth-179-opencode-target-detection-landed — PR 1619 — landing=landings/PLAN-TRUTH-179.md — status: shipped
- PLAN-TRUTH-186 (WS-01) — status: transferred

#### Ordered Queue

| # | Plan | Workstream | Status | Surface (expected) |
|---|------|------------|--------|--------------------|
| 1 | PLAN-TRUTH-145 | WS-01 | parked | marketplace/bundles/plan-marshall/skills/manage-execution-manifest/SKILL.md; marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/_manifest_core.py; marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/manage-execution-manifest.py; marketplace/bundles/plan-marshall/skills/manage-execution-manifest/standards/decision-rules.md; marketplace/bundles/plan-marshall/skills/manage-references/SKILL.md; marketplace/bundles/plan-marshall/skills/manage-references/scripts/; marketplace/bundles/plan-marshall/skills/manage-references/scripts/_references_core.py; marketplace/bundles/plan-marshall/skills/manage-references/scripts/manage_references.py; marketplace/bundles/plan-marshall/skills/phase-1-init/**; marketplace/bundles/plan-marshall/skills/phase-5-execute/SKILL.md; marketplace/bundles/plan-marshall/skills/phase-5-execute/scripts/scope_creep_check.py; marketplace/bundles/plan-marshall/skills/phase-5-execute/standards/canonical_verify.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/; test/plan-marshall/manage-execution-manifest/**; test/plan-marshall/manage-references/; test/plan-marshall/manage-references/**; test/plan-marshall/phase-5-execute/** |
| 2 | PLAN-TRUTH-146 | WS-01 | parked | marketplace/bundles/*/skills/ext-triage-*/; marketplace/bundles/plan-marshall/skills/automatic-review/scripts/; marketplace/bundles/plan-marshall/skills/manage-change-ledger/; marketplace/bundles/plan-marshall/skills/manage-findings/SKILL.md; marketplace/bundles/plan-marshall/skills/manage-findings/scripts/_findings_core.py; marketplace/bundles/plan-marshall/skills/manage-findings/standards/jsonl-format.md; marketplace/bundles/plan-marshall/skills/phase-5-execute/SKILL.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/review_commitments.py; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/pre-merge-barrier; marketplace/bundles/plan-marshall/skills/plan-orchestrator/SKILL.md; marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py; marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/landing-payload-spec.md; marketplace/bundles/plan-marshall/skills/plan-orchestrator/templates/landing-analysis.md; marketplace/bundles/plan-marshall/skills/plan-orchestrator/workflow/analyze.md; marketplace/bundles/plan-marshall/skills/ref-toon-format/scripts/toon_parser.py; marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/**; marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_gate_coverage.py; marketplace/bundles/plan-marshall/skills/tools-file-ops/scripts/constants.py; marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py; marketplace/bundles/plan-marshall/skills/workflow-integration-gitlab/scripts/gitlab_pr.py; marketplace/bundles/plan-marshall/skills/workflow-integration-sonar/scripts/sonar.py; marketplace/bundles/pm-requirements/skills/traceability/SKILL.md; test/plan-marshall/manage-findings/; test/plan-marshall/manage-findings/**; test/plan-marshall/plan-orchestrator/; test/plan-marshall/script-shared/**; test/plan-marshall/workflow-integration-sonar/ |
| 3 | PLAN-TRUTH-149 | WS-01 | parked | .claude/skills/audit-archived-plan-retrospectives/**; marketplace/bundles/plan-marshall/skills/manage-execution-manifest/**; marketplace/bundles/plan-marshall/skills/manage-findings/**; marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/emit-landing.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/output-template.md; marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/_orchestrator_inbox.py; marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/landing-payload-spec.md; marketplace/bundles/plan-marshall/skills/plan-retrospective/**; test/plan-marshall/**; test/plan-marshall/phase-6-finalize/; test/plan-marshall/plan-orchestrator/test_landing_completeness.py |
| 4 | PLAN-TRUTH-150 | WS-01 | parked | marketplace/bundles/plan-marshall/skills/build-gradle/scripts/_gradle_cmd_parse.py; marketplace/bundles/plan-marshall/skills/build-maven/SKILL.md; marketplace/bundles/plan-marshall/skills/build-maven/scripts/_maven_cmd_discover.py; marketplace/bundles/plan-marshall/skills/build-maven/scripts/_maven_cmd_parse.py; marketplace/bundles/plan-marshall/skills/build-maven/standards/maven-impl.md; marketplace/bundles/plan-marshall/skills/build-npm/scripts/_npm_parse_jest.py; marketplace/bundles/plan-marshall/skills/build-npm/scripts/_npm_parse_tap.py; marketplace/bundles/plan-marshall/skills/build-pyproject/scripts/_pyproject_cmd_parse.py; marketplace/bundles/plan-marshall/skills/manage-architecture/; marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_client_query.py; marketplace/bundles/plan-marshall/skills/manage-build-server/; marketplace/bundles/plan-marshall/skills/manage-build-server/scripts/**; marketplace/bundles/plan-marshall/skills/manage-change-ledger/**; marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_cmd_qgate_mechanical.py; marketplace/bundles/plan-marshall/skills/phase-4-plan/; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/pre-push-quality-gate.md; marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/_invariants.py; marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/; marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_jvm_patterns.py; marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_parse.py; marketplace/bundles/plan-marshall/skills/tools-integration-ci/scripts/**; marketplace/bundles/plan-marshall/skills/tools-integration-ci/standards/leaf-command-reference.md; marketplace/bundles/plan-marshall/skills/tools-integration-ci/standards/pr-operations.md; marketplace/bundles/plan-marshall/skills/tools-script-executor/templates/execute-script.py.template; marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_ops.py; test/plan-marshall/; test/plan-marshall/build-maven/test_maven_cmd_parse.py; test/plan-marshall/script-shared/test_build_parse.py |
| 5 | PLAN-TRUTH-151 | WS-01 | parked | marketplace/bundles/plan-marshall/skills/manage-config/scripts/; marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_domain_detect.py; marketplace/bundles/plan-marshall/skills/manage-lessons/**; marketplace/bundles/plan-marshall/skills/manage-plan-documents/**; marketplace/bundles/plan-marshall/skills/manage-solution-outline/; marketplace/bundles/plan-marshall/skills/manage-solution-outline/**; marketplace/bundles/plan-marshall/skills/manage-solution-outline/SKILL.md; marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/_plan_parsing.py; marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_change_type_heuristic.py; marketplace/bundles/plan-marshall/skills/persona-plan-orchestrator/standards/orchestration-model.md; marketplace/bundles/plan-marshall/skills/phase-1-init/**; marketplace/bundles/plan-marshall/skills/phase-2-refine/**; marketplace/bundles/plan-marshall/skills/phase-3-outline/; marketplace/bundles/plan-marshall/skills/phase-4-plan/**; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/finalize-step-security-audit.md; marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/planning-outline.md; marketplace/bundles/plan-marshall/skills/plan-retrospective/references/request-result-alignment.md; test/plan-marshall/manage-solution-outline/ |
| 6 | PLAN-TRUTH-153 | WS-01 | parked | marketplace/bundles/plan-marshall/skills/manage-architecture/; marketplace/bundles/plan-marshall/skills/manage-locks/scripts/merge_lock.py; marketplace/bundles/plan-marshall/skills/manage-tasks/SKILL.md; marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/**; marketplace/bundles/plan-marshall/skills/persona-plan-marshall-agent/standards/agent-behavior-rules.md; marketplace/bundles/plan-marshall/skills/phase-3-outline/; marketplace/bundles/plan-marshall/skills/phase-5-execute/standards/; marketplace/bundles/plan-marshall/skills/plan-retrospective/**; marketplace/bundles/plan-marshall/skills/ref-documentation/**; marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/**; marketplace/bundles/pm-plugin-development/skills/plugin-doctor/SKILL.md; marketplace/bundles/pm-plugin-development/skills/plugin-doctor/references/rule-provenance.md; marketplace/bundles/pm-plugin-development/skills/plugin-doctor/references/safe-fixes-guide.md; marketplace/bundles/pm-plugin-development/skills/plugin-doctor/references/verification-guide.md; marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_doctor_analysis.py; marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_doctor_shared.py; marketplace/bundles/pm-plugin-development/skills/plugin-doctor/standards/doctor-skills.md; test/_shared/_dispatch_roster.py; test/conftest.py; test/plan-marshall/**; test/plan-marshall/manage-locks/test_manage_locks_merge_lock_reentrant_acquire.py; test/plan-marshall/manage-tasks/** |
| 7 | PLAN-TRUTH-154 | WS-01 | parked | .claude/skills/finalize-step-sync-plugin-cache/SKILL.md; .claude/skills/sync-plugin-cache/SKILL.md; .claude/skills/sync-plugin-cache/scripts/sync.py; .plan/temp/repair-plugin-pin.py; AGENTS.md; CLAUDE.md; doc/developer/manual-sync-recovery.adoc; doc/developer/marketplace-build.adoc; marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py; marketplace/bundles/plan-marshall/skills/build-server-client/**; marketplace/bundles/plan-marshall/skills/manage-build-server/**; marketplace/bundles/plan-marshall/skills/manage-run-config/SKILL.md; marketplace/bundles/plan-marshall/skills/manage-run-config/scripts/run_config.py; marketplace/bundles/plan-marshall/skills/manage-run-config/standards/run-config-standard.md; marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/; marketplace/bundles/plan-marshall/skills/marshall-steward/references/menu-commit-trailer.md; marketplace/bundles/plan-marshall/skills/marshall-steward/references/menu-healthcheck.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/**; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/output-template.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/**; marketplace/bundles/plan-marshall/skills/plan-marshall-plugin/**; marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/q-gate-validation.md; marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py; marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/; marketplace/bundles/plan-marshall/skills/tools-integration-ci/scripts/ci.py; marketplace/bundles/plan-marshall/skills/tools-script-executor/**; marketplace/bundles/plan-marshall/skills/workflow-integration-git/; marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/git-workflow.py; marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py; test/plan-marshall/automatic-review/**; test/plan-marshall/manage-run-config/**; test/plan-marshall/tools-script-executor/**; test/plan-marshall/workflow-integration-git/** |
| 8 | PLAN-TRUTH-155 | WS-01 | parked | doc/plans/truthful-signals/170-graduate-deployment-diagram-type-from-api-sheriff/report-01.md; doc/user/configuration.adoc; doc/user/efforts.adoc; doc/user/enforcement-hook.adoc; doc/user/parallelism-and-locking.adoc; doc/user/recipes.adoc; marketplace//sync-plugin-cache; marketplace/bundles/; marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md; marketplace/bundles/plan-marshall/skills/automatic-review/automatic-review/scripts/review_completeness.py; marketplace/bundles/plan-marshall/skills/automatic-review/automatic-review/standards/bot-participation-contract.md; marketplace/bundles/plan-marshall/skills/extension-api/standards/build-systems-common.md; marketplace/bundles/plan-marshall/skills/extension-api/standards/persona-plan-marshall-agent/SKILL.md; marketplace/bundles/plan-marshall/skills/extension-api/standards/plan-marshall/workflow/await-long-running.md; marketplace/bundles/plan-marshall/skills/manage-findings/SKILL.md; marketplace/bundles/plan-marshall/skills/manage-lessons/SKILL.md; marketplace/bundles/plan-marshall/skills/manage-status/**; marketplace/bundles/plan-marshall/skills/persona-security-expert/standards/dependency-supply-chain.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/**; marketplace/bundles/plan-marshall/skills/plan-retrospective/**; marketplace/bundles/plan-marshall/skills/ref-workflow-architecture/standards/dispatch-logging.md; marketplace/bundles/plan-marshall/skills/tools-integration-ci/**; marketplace/bundles/plan-marshall/skills/tools-integration-ci/SKILL.md; marketplace/bundles/plan-marshall/skills/tools-permission-doctor/standards/permission-architecture.md; marketplace/bundles/pm-dev-java/skills/java-core/standards/java-17-features.md; marketplace/bundles/pm-dev-java/skills/java-core/standards/java-null-safety/SKILL.md; marketplace/bundles/pm-dev-java/skills/java-core/standards/java-null-safety/standards/null-safety-core.md; marketplace/bundles/pm-dev-java/skills/java-core/standards/java-null-safety/standards/null-safety-patterns.md; marketplace/bundles/pm-dev-java/skills/java-maintenance/standards/compliance-checklist.md; marketplace/bundles/pm-dev-java/skills/java-maintenance/standards/java-maintenance/standards/refactoring-triggers.md; marketplace/bundles/pm-documents/skills/ref-svg-diagrams/standards/diagram-type-deployment.md; marketplace/bundles/pm-documents/skills/ref-svg-diagrams/standards/ref-svg-diagrams/templates/deployment-diagram-skeleton.svg; marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/SKILL.md; test/plan-marshall/** |
| 9 | PLAN-TRUTH-156 | WS-01 | parked | marketplace/bundles/plan-marshall/skills/manage-status/SKILL.md; marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_mark_step.py; marketplace/bundles/plan-marshall/skills/manage-status/scripts/manage-status.py; test/plan-marshall/manage-status/_manage_status_transition_fixtures.py; test/plan-marshall/manage-status/_mark_step_done_fixtures.py; test/plan-marshall/manage-status/test_mark_step_done_completion_head_and_keys.py; test/plan-marshall/manage-status/test_mark_step_head_anchor.py |
| 10 | PLAN-TRUTH-158 | WS-01 | parked | marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/architecture-refresh.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/push.md; test/plan-marshall/phase-6-finalize/** |
| 11 | PLAN-TRUTH-159 | WS-01 | parked | .claude/skills/**; .claude/skills/finalize-step-deploy-target/SKILL.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md; test/plan-marshall/** |
| 12 | PLAN-TRUTH-160 | WS-01 | parked | doc/adr/022-Economy_rules_bind_the_persisted_artifact_never_the_reasoning_that_produced_it.adoc; marketplace/bundles/plan-marshall/skills/manage-metrics/scripts/**; marketplace/bundles/plan-marshall/skills/manage-metrics/standards/data-format.md; marketplace/bundles/plan-marshall/skills/phase-5-execute/**; marketplace/bundles/plan-marshall/skills/phase-6-finalize/**; test/plan-marshall/manage-metrics/** |
| 13 | PLAN-TRUTH-162 | WS-01 | parked | .claude/skills/**; .claude/skills/finalize-step-deploy-target/SKILL.md; marketplace/bundles/plan-marshall/skills/manage-solution-outline/SKILL.md; marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/manage-solution-outline.py; marketplace/bundles/plan-marshall/skills/persona-plan-marshall-agent/standards/agent-behavior-rules.md; marketplace/bundles/plan-marshall/skills/phase-4-plan/SKILL.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md; marketplace/bundles/plan-marshall/skills/platform-runtime/standards/pretooluse-enforcement.md; test/plan-marshall/** |
| 14 | PLAN-TRUTH-163 | WS-01 | parked | test/plan-marshall/plan-orchestrator/test_orchestrator_dispatch_workflow_pin.py |
| 15 | PLAN-TRUTH-164 | WS-01 | parked | marketplace/bundles/plan-marshall/skills/manage-status/**; marketplace/bundles/plan-marshall/skills/phase-6-finalize/**; marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/_cmd_prune_ref.py; marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/git-workflow.py; test/plan-marshall/workflow-integration-git/** |
| 16 | PLAN-TRUTH-165 | WS-01 | parked | marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/claude_runtime.py; marketplace/bundles/plan-marshall/skills/tools-permission-doctor/scripts/permission_doctor.py; marketplace/bundles/plan-marshall/skills/tools-permission-fix/**; marketplace/bundles/pm-plugin-development/skills/plugin-architecture/references/frontmatter-standards.md; marketplace/bundles/pm-plugin-development/skills/plugin-script-architecture/references/notation-spec.md; test/plan-marshall/tools-permission-doctor/**; test/plan-marshall/tools-permission-fix/** |
| 17 | PLAN-TRUTH-169 | WS-01 | parked | marketplace/bundles/plan-marshall/skills/build-maven/; marketplace/bundles/plan-marshall/skills/build-pyproject/; marketplace/bundles/plan-marshall/skills/build-server-client/; marketplace/bundles/plan-marshall/skills/manage-build-server/; marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/architecture-refresh.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/push.md; marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/; marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_gate_coverage.py; marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/build.py; test/conftest.py; test/plan-marshall/build-server-client/; test/plan-marshall/manage-build-server/; test/plan-marshall/phase-6-finalize/** |
| 18 | PLAN-TRUTH-170 | WS-01 | parked | marketplace/bundles/plan-marshall/skills/manage-status/scripts/; marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_lifecycle.py; marketplace/bundles/plan-marshall/skills/phase-5-execute/; marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/; marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/ci_verify.py; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/; marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/create-pr.md; marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/; test/plan-marshall/manage-status/; test/plan-marshall/workflow-integration-git/ |
| 19 | PLAN-TRUTH-171 | WS-01 | parked | marketplace/bundles/plan-marshall/skills/manage-change-ledger/; marketplace/bundles/plan-marshall/skills/manage-status/**; marketplace/bundles/plan-marshall/skills/manage-status/scripts/; marketplace/bundles/plan-marshall/skills/phase-2-refine/; marketplace/bundles/plan-marshall/skills/phase-4-plan/; marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/; marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/; marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/_cmd_prune_ref.py; marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/git-workflow.py; test/plan-marshall/manage-change-ledger/; test/plan-marshall/manage-status/; test/plan-marshall/workflow-integration-git/ |
| 20 | PLAN-TRUTH-173 | WS-01 | parked | marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-self-review-surfacing.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md; marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/_self_review_detectors.py; marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/_self_review_patterns.py; test/pm-plugin-development/ext-self-review-plan-marshall/ |
| 21 | PLAN-TRUTH-174 | WS-01 | parked | marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/; marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/extract-chat-signal.py; marketplace/bundles/plan-marshall/skills/ref-toon-format/scripts/toon_parser.py; test/plan-marshall/plan-retrospective/** |
| 22 | PLAN-TRUTH-175 | WS-01 | parked | marketplace/bundles/plan-marshall/skills/manage-change-ledger/**; marketplace/bundles/plan-marshall/skills/manage-metrics/**; marketplace/bundles/plan-marshall/skills/phase-6-finalize/**; marketplace/bundles/plan-marshall/skills/ref-workflow-architecture/standards/dispatch-logging.md; test/plan-marshall/manage-change-ledger/**; test/plan-marshall/manage-metrics/**; test/plan-marshall/phase-6-finalize/** |
| 23 | PLAN-TRUTH-176 | WS-01 | parked | marketplace/bundles/plan-marshall/skills/manage-findings/SKILL.md; marketplace/bundles/plan-marshall/skills/manage-solution-outline/SKILL.md; marketplace/bundles/plan-marshall/skills/tools-script-executor/**; marketplace/bundles/pm-plugin-development/skills/recipe-fix-argparse-rejection/**; test/plan-marshall/tools-script-executor/** |
| 24 | PLAN-TRUTH-177 | WS-01 | parked | marketplace/bundles/plan-marshall/skills/phase-1-init/**; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/emit-landing.md; marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/_orchestrator_inbox.py; test/plan-marshall/phase-1-init/** |
| 25 | PLAN-205 | WS-QA-01 | parked | marketplace/bundles/plan-marshall/skills/build-pyproject/; marketplace/bundles/plan-marshall/skills/manage-build-server/; marketplace/bundles/plan-marshall/skills/manage-change-ledger/; marketplace/bundles/plan-marshall/skills/manage-locks/; marketplace/bundles/plan-marshall/skills/manage-metrics/; marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/ |
| 26 | PLAN-206 | WS-QA-02 | parked | marketplace/bundles/plan-marshall/skills/manage-metrics/; marketplace/bundles/plan-marshall/skills/phase-6-finalize/ |
| 27 | PLAN-207 | WS-QA-02 | parked | marketplace/bundles/plan-marshall/skills/phase-5-execute/; marketplace/bundles/plan-marshall/skills/phase-6-finalize/ |
| 28 | PLAN-208 | WS-QA-03 | parked | marketplace/bundles/plan-marshall/skills/automatic-review/ |
| 29 | PLAN-209 | WS-QA-03 | parked | marketplace/bundles/plan-marshall/skills/automatic-review/; marketplace/bundles/plan-marshall/skills/manage-providers/ |
| 30 | PLAN-213 | WS-QA-06 | parked | marketplace/bundles/plan-marshall/skills/manage-tasks/; marketplace/bundles/plan-marshall/skills/phase-4-plan/; marketplace/bundles/plan-marshall/skills/phase-5-execute/ |
| 31 | PLAN-214 | WS-QA-06 | parked | marketplace/bundles/plan-marshall/skills/phase-2-refine/; marketplace/bundles/plan-marshall/skills/plan-marshall/; marketplace/bundles/plan-marshall/skills/workflow-integration-github/ |
| 32 | PLAN-215 | WS-QA-06 | parked | marketplace/bundles/plan-marshall/skills/manage-architecture/; marketplace/bundles/plan-marshall/skills/manage-lessons/; marketplace/bundles/plan-marshall/skills/tools-script-executor/ |
| 33 | PLAN-216 | WS-QA-07 | parked | marketplace/bundles/plan-marshall/skills/manage-findings/; marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/; marketplace/bundles/pm-plugin-development/skills/plugin-doctor/ |
| 34 | PLAN-217 | WS-QA-07 | parked | marketplace/bundles/plan-marshall/skills/manage-logging/; marketplace/bundles/plan-marshall/skills/plan-retrospective/ |
| 35 | PLAN-218 | WS-QA-09 | parked | marketplace/bundles/plan-marshall/skills/manage-config/ |
| 36 | PLAN-219 | WS-QA-08 | parked | marketplace/bundles/plan-marshall/skills/phase-6-finalize/ |
| 37 | PLAN-220 | WS-QA-08 | parked | marketplace/bundles/plan-marshall/skills/phase-6-finalize/; marketplace/bundles/plan-marshall/skills/tools-integration-ci/ |
| 38 | PLAN-221 | WS-QA-02 | parked | marketplace/bundles/plan-marshall/skills/marshall-steward/; marketplace/bundles/plan-marshall/skills/platform-runtime/; marketplace/bundles/plan-marshall/skills/tools-script-executor/; marketplace/bundles/pm-plugin-development/skills/finalize-step-deploy-target/ |
| 39 | PLAN-TRUTH-180 | WS-01 | parked | marketplace/bundles/plan-marshall/skills/manage-config/scripts/manage-config.py; marketplace/bundles/plan-marshall/skills/manage-status/scripts/; marketplace/bundles/plan-marshall/skills/phase-5-execute/scripts/scope_creep_check.py; test/plan-marshall/manage-config/; test/plan-marshall/manage-status/; test/plan-marshall/phase-5-execute/ |
| 40 | PLAN-TRUTH-181 | WS-01 | staged | marketplace/bundles/plan-marshall/skills/extension-api/scripts/extension_discovery.py; marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-self-review-surfacing.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md; marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/landing-payload-spec.md; marketplace/bundles/plan-marshall/skills/script-shared/scripts/; marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/SKILL.md; marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/; test/plan-marshall/phase-6-finalize/; test/pm-plugin-development/ext-self-review-plan-marshall/ |
| 41 | PLAN-TRUTH-182 | WS-01 | staged | marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-self-review-surfacing.md; marketplace/bundles/pm-dev-java/.claude-plugin/plugin.json; marketplace/bundles/pm-dev-java/README.md; marketplace/bundles/pm-dev-java/skills/ext-self-review-java/; test/pm-dev-java/ext-self-review-java/ |
| 42 | PLAN-TRUTH-183 | WS-01 | staged | marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-self-review-surfacing.md; marketplace/bundles/pm-dev-python/.claude-plugin/plugin.json; marketplace/bundles/pm-dev-python/README.md; marketplace/bundles/pm-dev-python/skills/ext-self-review-python/; test/pm-dev-python/ext-self-review-python/ |
| 43 | PLAN-TRUTH-184 | WS-01 | staged | marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-self-review-surfacing.md; marketplace/bundles/pm-dev-frontend/.claude-plugin/plugin.json; marketplace/bundles/pm-dev-frontend/README.md; marketplace/bundles/pm-dev-frontend/skills/ext-self-review-javascript/; test/pm-dev-frontend/ext-self-review-javascript/ |
| 44 | PLAN-TRUTH-185 | WS-01 | staged | marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-self-review-surfacing.md; marketplace/bundles/pm-documents/.claude-plugin/plugin.json; marketplace/bundles/pm-documents/README.md; marketplace/bundles/pm-documents/skills/ext-self-review-documents/; test/pm-documents/ext-self-review-documents/ |
| 45 | PLAN-TRUTH-187 | WS-01 | staged | marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/gitignore_setup.py; test/plan-marshall/marshall-steward/ |

## Queue outcome

54 plans: 5 shipped, 4 closed unshipped, 39 parked, 6 at another status.

### Shipped

| Plan | Slug | Status | PR |
|---|---|---|---|
| PLAN-TRUTH-147 | a-lane-reports-green-yields-or-transitions-without-the-artifact-its-own-gate-requires | shipped | 1599 |
| PLAN-TRUTH-161 | adr-number-allocation-reads-the-local-tree-so-two-branches-collide-invisibly | shipped | 1586 |
| PLAN-TRUTH-168 | sync-defaults-reports-added-while-silently-reverting-a-deliberate-remove-step | shipped | 1674 |
| PLAN-211 | baseline-reconcile | shipped | 1675 |
| PLAN-TRUTH-179 | opencode-target-detection-landed-three-gaps-it-exposed-still-stand | shipped | 1619 |

### Closed unshipped

| Plan | Slug | Status |
|---|---|---|
| PLAN-TRUTH-167 | self-review-on-a-diff-no-resolvable-surfacer-applies-to-loops-to-the-ceiling-instead-of-reporting-not-covered | superseded |
| PLAN-TRUTH-172 | the-lane-transition-lacks-the-arrival-path-and-the-artifacts-its-own-entry-gate-requires | transferred |
| PLAN-TRUTH-178 | scope-creep-guard-emits-a-finding-type-the-ledger-rejects | transferred |
| PLAN-TRUTH-186 | the-push-freshness-gate-refuses-the-pre-push-gates-own-green-builds | transferred |

### Parked at close

| Plan | Slug | Status |
|---|---|---|
| PLAN-TRUTH-145 | declarations-that-cannot-learn-and-cannot-go-stale | parked |
| PLAN-TRUTH-146 | the-findings-ledger-one-vocabulary-and-an-experiment-told-from-a-regression | parked |
| PLAN-TRUTH-149 | the-landing-payload-and-what-the-epic-learns-from-it | parked |
| PLAN-TRUTH-150 | build-and-ci-verdicts-that-mislead-specifically-on-the-healthy-path | parked |
| PLAN-TRUTH-151 | early-phase-gates-the-outline-parser-and-the-plan-tier-claim-write-back | parked |
| PLAN-TRUTH-153 | tests-fixtures-and-detectors-that-cannot-fail-and-underived-completeness-claims | parked |
| PLAN-TRUTH-154 | operator-facing-authority-surfaces-that-answer-confidently-and-wrongly | parked |
| PLAN-TRUTH-155 | agent-facing-documentation-surfaces-and-the-live-plan-defect-sweep | parked |
| PLAN-TRUTH-156 | mark-step-done-must-derive-head-at-completion-never-accept-it | parked |
| PLAN-TRUTH-158 | a-missing-freshness-reconciliation-record-is-reported-as-un-built-source-drift | parked |
| PLAN-TRUTH-159 | a-documented-finalize-step-command-this-repos-own-hook-denies | parked |
| PLAN-TRUTH-160 | the-billing-cost-column-undercounts-output-five-fold-in-a-report-of-ten-non-comparable-figures | parked |
| PLAN-TRUTH-162 | argparse-rejections-recur-despite-documented-signatures-the-canonical-hint-is-not-uniform | parked |
| PLAN-TRUTH-163 | two-deferred-dispatch-workflow-pin-test-defects-from-plan-truth-157 | parked |
| PLAN-TRUTH-164 | worktree-remove-leaves-use-worktree-and-worktree-path-stale | parked |
| PLAN-TRUTH-165 | detect-suspicious-reports-a-clean-allow-list-while-the-harness-warns-on-every-startup | parked |
| PLAN-TRUTH-169 | a-timeout-verdict-describes-the-wait-not-the-work-and-time-budgets-are-undeclared | parked |
| PLAN-TRUTH-170 | the-finalize-seam-records-less-than-it-does-and-enforces-less-than-it-documents | parked |
| PLAN-TRUTH-171 | state-writers-that-fabricate-collide-or-fail-silently | parked |
| PLAN-TRUTH-173 | the-in-run-self-review-instrument-detector-reach-a-bounded-terminus-and-six-vacuity-modes | parked |
| PLAN-TRUTH-174 | plan-retrospective-measurement-integrity | parked |
| PLAN-TRUTH-175 | dispatch-and-phase-boundary-measurement-integrity | parked |
| PLAN-TRUTH-176 | preflight-invocation-validator | parked |
| PLAN-TRUTH-177 | orchestration-detection-fails-open-without-source-id | parked |
| PLAN-205 | build-telemetry | parked |
| PLAN-206 | verify-first-a | parked |
| PLAN-207 | verify-first-b | parked |
| PLAN-208 | review-yield-a | parked |
| PLAN-209 | review-yield-b | parked |
| PLAN-213 | plan-execute-mechanics | parked |
| PLAN-214 | gates-anchors | parked |
| PLAN-215 | worktree-paths | parked |
| PLAN-216 | self-review-detectors | parked |
| PLAN-217 | chat-signal-halt | parked |
| PLAN-218 | testing-fidelity | parked |
| PLAN-219 | finalize-self-review | parked |
| PLAN-220 | cost-mergequeue | parked |
| PLAN-221 | executor-target-fidelity | parked |
| PLAN-TRUTH-180 | three-script-internal-error-recurrences-recovered-around-never-fixed | parked |

### Other status at close

| Plan | Slug | Status |
|---|---|---|
| PLAN-TRUTH-181 | self-review-surfacing-foundation-shared-envelope-and-per-content-class-dispatch | staged |
| PLAN-TRUTH-182 | ext-self-review-java-the-java-domain-self-review-surfacer | staged |
| PLAN-TRUTH-183 | ext-self-review-python-the-python-domain-self-review-surfacer | staged |
| PLAN-TRUTH-184 | ext-self-review-javascript-the-javascript-domain-self-review-surfacer | staged |
| PLAN-TRUTH-185 | ext-self-review-documents-the-asciidoc-and-markdown-self-review-surfacer | staged |
| PLAN-TRUTH-187 | gitignore-setup-never-un-ignores-the-tracked-orchestrator-ledger | staged |

A row still `staged` or `parked` here was live work that did not finish before the close. It
is a lead, not a queue entry: nothing emits it any more.

## Carried into `live-blockers`

- `PLAN-TRUTH-186` → `PLAN-LB-01` (row `transferred`).
- `PLAN-TRUTH-172` D2 → `PLAN-LB-04` (row `transferred`).
- `PLAN-TRUTH-178` → `PLAN-LB-07` (row `transferred`).
- `PLAN-TRUTH-181` D1–D3 → `PLAN-LB-03`; its D4–D7 and `PLAN-TRUTH-182` to `-185` (domain self-review surfacers) are not carried.
- `PLAN-TRUTH-150` Maven deliverables (with archived `PLAN-TRUTH-122`) → `PLAN-LB-13`.
- `PLAN-TRUTH-169` / `-162` wait procedures → `PLAN-LB-05`; `PLAN-TRUTH-170` `ci_verify` fold and D1 → `PLAN-LB-10`, D5 → `PLAN-LB-11`.
- `PLAN-TRUTH-154` plugin-registry pin → `PLAN-LB-15`.
- Inbox item `orchestrator-refactor-001.md` § 1 (launch gate) → `PLAN-LB-14`.

## Leads carried forward, not staged

- The medium- and low-priority items found in this epic are listed with evidence in
  `.plan/orchestrator/live-blockers/backlog.md`. They are unstaged.
- `epic.md` § Open Defects (58 entries) and § Watches (92 entries) are frozen as they
  stood. Entries not named above or in that backlog were judged to be design input for the
  rewrite, refactors or measurements of machinery the rewrite replaces, or already fixed.
- Design input for plan-marshall-mcp lives in that repository's requirements, specification
  and `doc/implementation-watch/` documents. Ledger pointers to
  `plan-marshall-mcp/doc/known-defects/…-carry-over.md` name a path that no longer exists.
- `PLAN-TRUTH-187` (steward `.gitignore` setup) and `PLAN-TRUTH-165` (permission checks) are ready and small but were ranked medium; they are in `backlog.md` §§ 3.2 and 2.4.
- The token-reduction roadmap (`roadmap-token-reduction.md`) concerns machinery the rewrite replaces and is not carried.

### Inbox messages undrained at close

- `inbox/orchestrator-refactor-001.md`

## Decision record

`epic.md` § Decisions is the curated view; `logs/decision.log` is the append-only record. Both
are frozen in this tree.
