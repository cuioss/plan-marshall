envelope_version=1
sender_type=plan
sender_id=lb-28-java-consumer-repos
epic=live-blockers
kind=landing
created=2026-10-10T23:30:25Z

## What landed

lb-28-java-consumer-repos shipped as #1750 (merged).

```landing-facts
schema=landing-facts/1
plan_id=lb-28-java-consumer-repos
epic=live-blockers
pr=#1750
merge_state=merged
cleanup_owed=false
deliverables_total=4
deliverables_done=4
total_tokens=6931627
total_wall_seconds=28055.0
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,project:finalize-step-plugin-doctor:done,finalize-step-security-audit:done,pre-submission-self-review:done,architecture-refresh:done,pre-push-quality-gate:done,push:done,create-pr:done,ci-verify:done,automatic-review:done,sonar-roundtrip:done,adr-propose:done,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:done,project:finalize-step-review-retrospective:done,lessons-capture:done,finalize-step-preference-emitter:done,plan-marshall:plan-retrospective:done,record-metrics:done,finalize-step-print-phase-breakdown:done
step.branch-cleanup.merge_mechanism=merge_queue
step.sonar-roundtrip.work_performed=false
step.pre-submission-self-review.advisory_count=3
step.finalize-step-sync-baseline.action=rebased
```

## Residue

- The PLAN-LB-28 request excluded `extension-api` edits, but the self-review contract-drift fix (TOON `by_runner` / `population` projection) edited `extension-api/standards/build-execution.md`; the retrospective flagged the crossed exclusion and no operator decision was recorded.
- Deliverables D5–D8 of PLAN-LB-28 were moved to PLAN-LB-34 and were not implemented here.
- Run exceeded its token budget (6.09M accounted vs 2.0M limit per the retrospective).
- Sonar is not configured in this checkout; the sonar verb returned `internal_error` rather than `unconfigured` (lesson 2026-10-10-21-001).
- sourcery (optional bot) refused on quota; required bots participated.
