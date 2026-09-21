envelope_version=1
sender_type=plan
sender_id=plan-130-sweep-the-prose-the-widened-rules
epic=test-quality
kind=landing
created=2026-09-07T15:26:03Z

## What landed

plan-130-sweep-the-prose-the-widened-rules shipped as #1436 + #1435 (merged), after #1432 was closed unmerged without ever being reviewed.

```landing-facts
schema=landing-facts/1
plan_id=plan-130-sweep-the-prose-the-widened-rules
epic=test-quality
pr=#1436,#1435
merge_state=merged
deliverables_total=8
deliverables_done=8
total_tokens=4300635
total_wall_seconds=81060
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,pre-push-quality-gate:done,project:finalize-step-plugin-doctor:done,pre-submission-self-review:done,finalize-step-simplify:done,architecture-refresh:done,push:done,create-pr:done,project:finalize-step-era-stamp-fill:done,ci-verify:done,automatic-review:done,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:done,project:finalize-step-review-retrospective:done,plan-marshall:plan-retrospective:done,lessons-capture:done,finalize-step-preference-emitter:done,record-metrics:done,finalize-step-print-phase-breakdown:done,emit-landing:done,archive-plan:done
step.branch-cleanup.merge_state=merged
step.branch-cleanup.merge_mechanism=merge_queue
step.branch-cleanup.shipped_prs=1436,1435
step.branch-cleanup.abandoned_prs=1432
step.finalize-step-sync-baseline.action=rebased
step.finalize-step-sync-baseline.upstream_commit_count=2
```

## Residue

**The `pr` fact above does not match `create-pr`'s recorded `pr_number`, deliberately.** That step recorded `1432`, because only the FIRST `create-pr` invocation writes the fact. #1432 was closed unmerged and shipped nothing; the plan shipped as #1436 and #1435. Transcribing the step's stale fact would have told this epic the plan landed as a PR that landed nothing, so the observed end state is reported here instead and the discrepancy named rather than hidden. The underlying gap — `facts.pr_number` is write-once across re-created PRs — is a producer defect worth an epic-level fix; it also caused the retrospective's footprint resolver to return 36 of 112 files and emit a spurious `Recall 32% below threshold` error naming 76 correctly-shipped files as missing.

**The rule population re-opened during the run that closed it.** The sweep drove `test-docstring-historical-prose` from 232 findings / 111 files to 0 over its own population, verified by the shipped rule and an independent per-segment enumerator. At merged `main` the whole-tree count is **3**, all in `test/plan-marshall/manage-tasks/test_freshness_exempt_vs_verified_discrimination.py`, added by upstream PR #1425 which landed mid-run and was folded in by the finalize rebase. This is the Standing-Enforcement Note's predicted recurrence, now observed twice (PLAN-080's "211 of 211" was falsified within two days). Recorded as finding `f9f476`. It is direct evidence for the WS-03 severity-flip decision: at `error`, PR #1425 would have been blocked — precisely what the flip buys and precisely its cost.

**The 100-file review cap is a structural constraint on this epic's remaining sweeps.** CodeRabbit refuses any PR over 100 files, so a tree-wide sweep of this size cannot be reviewed as one PR. This plan split along its own deliverable boundaries into 76 + 36. A follow-on: after a SQUASH merge of a stacked base branch, retargeting the child PR does NOT recompute its merge base — #1435 kept reporting 112 files and kept being refused, and two 90-minute quota waits were spent before the file count was re-read. The remedy is rebasing the child's own commits onto the new base.

**Six prose/identifier incoherences are left for a follow-up pass**, recorded by the simplify sweep: a de-referenced comment sitting next to an identifier that still carries the old number (e.g. `test_maven_rewrite_log.py` prose no longer says "deliverable 1" while the constant is still `D1_CORPUS`; `test_comments_stage.py` dropped `1014` while `_SOURCERY_1014_REFUSAL` keeps it). Renaming identifiers is behaviour-adjacent and was outside a prose-only sweep.

**A measurement gap the plan reported rather than filled**: no whole-tree collected-test baseline was captured before the first fix commit. The zero-delta claim rests on an A/B at the same base — 24714 tests with and without the sweep's edits — not on a pre/post comparison of the original tree.
