envelope_version=1
sender_type=plan
sender_id=retrospective-aspects-publish-verdict
epic=post-run-quality
kind=landing
created=2026-09-21T09:31:18Z

## What landed

retrospective-aspects-publish-verdict shipped as #1550 (merged).

```landing-facts
schema=landing-facts/1
plan_id=retrospective-aspects-publish-verdict
epic=post-run-quality
pr=#1550
merge_state=merged
cleanup_owed=false
deliverables_total=5
deliverables_done=5
total_tokens=18653683
total_wall_seconds=128684.0
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,finalize-step-simplify:done,project:finalize-step-plugin-doctor:done,pre-submission-self-review:done,architecture-refresh:done,pre-push-quality-gate:done,push:done,create-pr:done,project:finalize-step-era-stamp-fill:done,ci-verify:done,automatic-review:done,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:done,project:finalize-step-review-retrospective:done,plan-marshall:plan-retrospective:done,finalize-step-preference-emitter:done,record-metrics:done,finalize-step-print-phase-breakdown:done
```

## Residue

- `pre-submission-self-review` fired 21 times (17 loop_back, 4 done across re-firings), `finalize-step-simplify` fired 27 times, `project:finalize-step-plugin-doctor` fired 20 times — this plan's finalize phase alone consumed ~13.5M of the run's 18.65M total tokens (a 14x overrun against the plan's single_module+bug_fix error anchor). A critical finding covering this was already filed to this epic's inbox as `retrospective-aspects-publish-verdict-001.md` before this landing.
- `plan-retrospective` (this run's opt-in retrospective aspect) filed 8 candidate-lessons to this epic's inbox, 4 of which are defects in `plan-retrospective` itself (found by the aspect running against its own plan) — see `retrospective-aspects-publish-verdict-002.md` through `-009.md` (exact numbering per the orchestrator's own allocation).
- `project:finalize-step-review-retrospective`'s review-vs-gate delta was `excluded` (`gate_tree_unsubstantiated`): the pre-submission-self-review loop-back churn left three different `reviewed_commit_sha` values across the PR's findings, so no single reviewed-head could be substantiated against the gate's certified tree.
