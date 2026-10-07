envelope_version=1
sender_type=plan
sender_id=plan-pr-078-review-bot-fleet-opt-in
epic=review-apparatus
kind=landing
created=2026-10-06T22:24:44Z

## What landed

plan-pr-078-review-bot-fleet-opt-in shipped its host change as #1704 (merged); the fleet rollout landed only partway — 7 of 20 in-scope repositories carry the opt-in, 13 are deferred.

```landing-facts
schema=landing-facts/1
plan_id=plan-pr-078-review-bot-fleet-opt-in
epic=review-apparatus
pr=#1704
merge_state=merged
cleanup_owed=false
deliverables_total=10
deliverables_done=10
total_tokens=8442614
total_wall_seconds=114951.0
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,finalize-step-simplify:done,project:finalize-step-plugin-doctor:done,pre-submission-self-review:done,architecture-refresh:done,pre-push-quality-gate:done,push:done,create-pr:done,ci-verify:done,automatic-review:done,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:done,project:finalize-step-review-retrospective:done,plan-marshall:plan-retrospective:done,finalize-step-preference-emitter:done,record-metrics:done,finalize-step-print-phase-breakdown:done
step.create-pr.pr_number=1704
step.branch-cleanup.merge_mechanism=merge_queue
step.branch-cleanup.merge_state=merged
step.branch-cleanup.cleanup_owed=false
step.pre-submission-self-review.acceptance=accepted
step.pre-submission-self-review.may_close=no
step.record-metrics.any_phase_missing_end_time=false
step.finalize-step-sync-baseline.action=rebased
```

## Residue

- **Two landings exist for this run.** Message `plan-pr-078-review-bot-fleet-opt-in-001` (kind=landing) was written earlier by the plan's own task 11 as the fleet report; its landing-facts were unknown at that time. This message carries the settled facts; `-001` carries the per-repository fleet table. Read them together; the facts here win.
- **`deliverables_done=10` counts closed tasks, not full outcomes.** Deliverables 5 and 6 (enrolment batches A and B) landed only partway: 13 repositories fail the org `project.yml` schema on keys that pre-date this plan, and the operator chose to fix the schema first. Deferred — batch A: cui-core-ui-model, cui-jsf-components, cui-portal-ui, cui-java-tools, cui-jsf-test-basic, cui-portal-core; batch B: cui-reference-documentation, cui-test-keycloak-integration, nifi-extensions, cui-test-generator, cui-test-juli-logger, cui-test-mockwebserver-junit5, cui-test-value-objects. Follow-up lesson 2026-10-06-15-001 tracks the schema fix.
- **Landed in foreign repositories:** API-Sheriff #399, TokenSheriff #782, cui-http #273 (migrated; merged on a block-only schema check, whole-file re-validation still owed), cui-java-module-template #156, cui-open-rewrite #190, plan-marshall-mcp #33, playwright-test-artifacts #185 (enrolled), coderabbit #6, cuioss-organization #307 (npm release guard, released as v0.36.0). plan-marshall-telemetry was excluded by the operator.
- **Live verification covers 1 of 7 enrolled repositories** (plan-marshall-mcp, PR #34). The other six are unverified until their next real pull request; no probe pull requests were opened, by operator decision.
- **Self-review did not converge.** The operator closed it after 3 rounds (12 doc findings fixed); CodeRabbit then found 3 further real defects, all fixed in f80ed122b before merge.
- **Reviewer coverage on #1704:** only CodeRabbit left records that could be judged. cuioss-review-bot and Sourcery left none; the store shows neither that they reviewed nor that they did not.
- **Open items not fixed by this plan:** the `job_not_found` edge case in `_github_ci.py`; a wrong plan-marshall-mcp cell in the persisted pack table; leftover local `feature/plan-pr-078-review-bot-fleet-opt-in` branches in the foreign checkouts; `post_run_source_guard check` is documented with a `--plan-id` flag it does not accept.
- **Cost:** 8.44M tokens against a 2.5M anchor; finalize (3.50M) cost more than execute (2.86M), driven by four loop-back passes. Nine candidate-lesson messages (`-002` to `-010`) from the plan retrospective are in this inbox.
