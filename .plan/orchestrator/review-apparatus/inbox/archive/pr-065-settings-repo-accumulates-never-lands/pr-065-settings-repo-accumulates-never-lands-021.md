envelope_version=1
sender_type=plan
sender_id=pr-065-settings-repo-accumulates-never-lands
epic=review-apparatus
kind=landing
created=2026-09-14T19:26:27Z

## What landed

pr-065-settings-repo-accumulates-never-lands shipped as #1491 (merged).

```landing-facts
schema=landing-facts/1
plan_id=pr-065-settings-repo-accumulates-never-lands
epic=review-apparatus
pr=#1491
merge_state=merged
cleanup_owed=false
deliverables_total=10
deliverables_done=10
total_tokens=6486159
total_wall_seconds=113741.0
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,pre-push-quality-gate:done,project:finalize-step-plugin-doctor:done,pre-submission-self-review:done,finalize-step-simplify:done,architecture-refresh:done,push:done,create-pr:done,project:finalize-step-era-stamp-fill:done,ci-verify:done,automatic-review:done,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:done,project:finalize-step-review-retrospective:done,plan-marshall:plan-retrospective:done,lessons-capture:done,finalize-step-preference-emitter:done,record-metrics:done,finalize-step-print-phase-breakdown:done,emit-landing:done,archive-plan:pending
```

## Residue

Automated bot review (CodeRabbit, Sourcery, cuioss-review-bot) was explicitly skipped for this PR (operator decision, `required_bots`/`optional_bots` set empty, `skip-bot-review` label applied) — most of this plan's real-world impact landed in the foreign repo `cuioss/pr-agent-settings` (PR #64, already merged), and this repo's own PR carried only the supporting tooling fix plus an opportunistic plugin-doctor bug fix. `project:finalize-step-review-retrospective` graded `indeterminate` because it reads bot roster defaults from `marshal.json` rather than this plan's local step-params override, so its "0 findings, roster of 3" reading is a false alarm against the actual (empty) roster this plan used — worth fixing in that retrospective step's config-source, not a gap in this plan's review coverage.

The GitLab half of the `pr list` `--limit`/`truncated` contract (`ci_base.py`, `gitlab_ops.py`, and their tests) was declared in scope but never touched — the derivation signal exists on the GitHub provider only.
