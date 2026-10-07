envelope_version=1
sender_type=plan
sender_id=charter-assembled-at-run-time
epic=review-apparatus
kind=landing
created=2026-09-24T11:14:22Z

# Landing — PLAN-PR-066 charter-assembled-at-run-time

PR #1611 merged via the merge queue (6df659569). The reviewer now assembles the review charter at run time from each repository's `.github/project.yml` `cuioss-review-bot:` declaration: absent or `enabled` not true means the central charter; `enabled: true` means the spine plus the selected packs plus `additional_rules`. The reviewer surfaces are renamed to `cuioss-review-bot`, and the settings repository is renamed to `cuioss/cuioss-review-bot`.

```landing-facts
schema=landing-facts/1
plan_id=charter-assembled-at-run-time
epic=review-apparatus
pr=#1611
merge_state=merged
cleanup_owed=false
deliverables_total=13
deliverables_done=13
total_tokens=8161027
total_wall_seconds=77934
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,finalize-step-simplify:done,project:finalize-step-plugin-doctor:done,pre-submission-self-review:done,architecture-refresh:done,pre-push-quality-gate:done,push:done,create-pr:done,project:finalize-step-era-stamp-fill:done,ci-verify:done,automatic-review:done,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:done,project:finalize-step-review-retrospective:done,plan-marshall:plan-retrospective:done,finalize-step-preference-emitter:done,record-metrics:done,finalize-step-print-phase-breakdown:done,emit-landing:done,archive-plan:pending
step.branch-cleanup.merge_mechanism=merge_queue
step.branch-cleanup.merge_state=merged
step.record-metrics.any_phase_missing_end_time=false
step.pre-submission-self-review.may_close=operator_override
```

## Foreign landings (part of this plan)

- cuioss/cuioss-organization#288 (D1–D7, D11 org side), #290 (release prep); release **v0.30.0**, workflow SHA `2fa5476de3435e7fc3705646c3f1f3c99be95e71`.
- cuioss/cuioss-review-bot#66 (D12 docs rewrite + D10 consumer guide). The repository was renamed from `pr-agent-settings`.
- cuioss/plan-marshall#1601 (project.yml key rename) and #1605 (D8 pilot opt-in, `enabled: true`, packs python + plugin).

## Evidence

- (p6) live: the reviewer followed the redirect `/repos/cuioss/pr-agent-settings` → the renamed repo and logged `Generating prediction with vertex_ai/gemini-3.7-flash` (#1605 job 107381690506).
- D8: the #1611 review log shows `##[group]Assembled review charter (spine; packs: python, plugin; additional rules: 0)`.
- (p4) live probe (#1600): the GitHub App token mint does NOT follow a repository rename. The v0.29.0 reviewers broke until the 0.30.0 re-pin was fixed forward.

## Residue

- **Fleet:** API-Sheriff's re-pin PR (API-Sheriff#351) was not yet merged at landing, so its reviews fail at the token mint until it lands. 17 consumer re-pin PRs from the 0.30.0 release were open at release time. Only plan-marshall is opted in (D9 record: 30 repos).
- **Self-review closed on an operator ruling:** it exhausted the loop-back ceiling (5 rounds, 15 findings fixed). The operator ruled it closed on a clean round 6, over the verifier's `may_close=no` (the objection was that github-impl.md/gitlab-impl.md were unchecked; those docs are selective).
- **Fix commit not re-reviewed:** the operator admitted one inline fix commit (cf7885e84) for 3 CodeRabbit findings with no re-review. The merge authorization `barrier-ask-override` was recorded at cf7885e84.
- **Local main commit for CI-accepted ruff layout:** the local ruff import-grouping churn was resolved by committing the local layout (lesson 2026-09-23-23-001); upstream main carries the same layout.
- **Lessons filed:** 2026-09-23-16-001 (scope_creep finding type rejected), 2026-09-23-23-001 (local vs CI ruff), 2026-09-24-05-001 (worktree-rebase-to rebases a behind=0 merged branch). The plan retrospective routed 7 candidate lessons (charter-assembled-at-run-time-001..007).
