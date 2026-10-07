envelope_version=1
sender_type=plan
sender_id=architecture-store-query-truthfulness
epic=code-intelligence-substrate
kind=landing
created=2026-09-15T08:04:37Z

## What landed

architecture-store-query-truthfulness shipped as #1489 (merged).

```landing-facts
schema=landing-facts/1
plan_id=architecture-store-query-truthfulness
epic=code-intelligence-substrate
pr=#1489
merge_state=merged
cleanup_owed=false
deliverables_total=12
deliverables_done=12
total_tokens=5299565
total_wall_seconds=209619.0
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,pre-push-quality-gate:done,project:finalize-step-plugin-doctor:done,pre-submission-self-review:done,finalize-step-simplify:done,architecture-refresh:done,push:done,create-pr:done,project:finalize-step-era-stamp-fill:done,ci-verify:done,automatic-review:done,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:done,project:finalize-step-review-retrospective:done,plan-marshall:plan-retrospective:done,lessons-capture:done,finalize-step-preference-emitter:done,record-metrics:done,finalize-step-print-phase-breakdown:done
```

## Residue

- Round 3 of `automatic-review` hit a CodeRabbit hourly-quota refusal twice; recovered after two ~90-minute waits under the standing operator recovery protocol (no escalation, no PR reopen — CodeRabbit was actively refusing, not silent).
- Six out-of-footprint self-review findings (a vacuous test-presence assertion, and five documentation sites restating a superseded `module_edges`/`content_search` status-vocabulary rule) were carried forward as lessons `2026-09-14-21-001`, `-002`, `-003` rather than fixed in-plan (outside declared `affected_files`).
- `plan-retrospective` flagged this run's cost as 5.2× over its `multi_module + bug_fix` anchor (10.5M tokens against a 2.0M anchor for the finalize+execute stretch alone), driven by 4 loop-back iterations in finalize and the CodeRabbit rate-limit recovery cycle.
