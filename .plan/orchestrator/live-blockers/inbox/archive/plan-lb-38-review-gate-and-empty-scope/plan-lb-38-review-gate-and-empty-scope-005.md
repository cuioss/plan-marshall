envelope_version=1
sender_type=plan
sender_id=plan-lb-38-review-gate-and-empty-scope
epic=live-blockers
kind=landing
created=2026-10-11T23:07:34Z

## What landed

plan-lb-38-review-gate-and-empty-scope shipped as #1752 (merged).

```landing-facts
schema=landing-facts/1
plan_id=plan-lb-38-review-gate-and-empty-scope
epic=live-blockers
pr=#1752
merge_state=merged
cleanup_owed=false
deliverables_total=9
deliverables_done=9
total_tokens=9525584
total_wall_seconds=55586.0
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,project:finalize-step-plugin-doctor:done,pre-submission-self-review:done,architecture-refresh:done,pre-push-quality-gate:done,push:done,create-pr:done,ci-verify:done,automatic-review:done,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:done,project:finalize-step-review-retrospective:done,finalize-step-preference-emitter:done,plan-marshall:plan-retrospective:done,record-metrics:done,finalize-step-print-phase-breakdown:done,emit-landing:done,archive-plan:pending
step.branch-cleanup.merge_mechanism=merge_queue
step.create-pr.pr_number=1752
step.finalize-step-sync-baseline.action=rebased
```

## Residue

- D10 (review-bot size cap) was dropped at outline under its own drop clause: no review bot declares a size cap.
- D7 resolution changed during finalize from keep-resolved to reopen-on-change (operator decision), adding `_findings_core.update_finding_text` outside the declared read-only scope.
- The uv.lock re-lock (main's lock was stale after dependabot #1743/#1744) was committed in this PR by operator choice.
- CodeRabbit participation was credited from an edited pre-existing issue comment rather than a fresh review after the trigger. This was sent to the inbox as a candidate lesson.
- review-retrospective found 0 `pr-comment` findings in the store, so the reviewer comparison is indeterminate.
- Advisory items left open: (1) on a repository with no CI where only bot statuses report, `github_pr.py` holds "fixed" replies indefinitely; (2) in the workflow-integration-github SKILL.md, the "both are subtracted" wording is unclear; (3) the self-response trailing-run guard in `github_pr.py` ignores in-place edits; (4) in the automatic-review SKILL.md, the description of `review_rate_window_timeout_seconds` is out of date; (5) the marshal.json config is out of date and `/marshall-steward` is recommended.
