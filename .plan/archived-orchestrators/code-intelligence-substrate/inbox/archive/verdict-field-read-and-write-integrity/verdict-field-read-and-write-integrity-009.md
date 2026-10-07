envelope_version=1
sender_type=plan
sender_id=verdict-field-read-and-write-integrity
epic=code-intelligence-substrate
kind=landing
created=2026-08-26T19:41:16Z

## What landed

verdict-field-read-and-write-integrity shipped as #1355 (merged). An unreadable `## Claim Labels` section is now a distinguishable parse state that contributes a blocking row instead of passing the prep-ready gate vacuously, `corpus set-verdict --section-scope` gives it a write address, and `corpus epics` enumerates the epic corpus so a blast-radius measurement can be derived rather than sampled.

```landing-facts
schema=landing-facts/1
plan_id=verdict-field-read-and-write-integrity
epic=code-intelligence-substrate
pr=#1355
merge_state=merged
deliverables_total=3
deliverables_done=3
total_tokens=5132687
total_wall_seconds=50448.0
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,pre-push-quality-gate:done,project:finalize-step-plugin-doctor:done,pre-submission-self-review:done,finalize-step-simplify:done,architecture-refresh:done,push:done,create-pr:done,project:finalize-step-era-stamp-fill:done,ci-verify:done,automatic-review:done,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:done,project:finalize-step-review-retrospective:done,plan-marshall:plan-retrospective:done,lessons-capture:done,finalize-step-preference-emitter:done,record-metrics:done,finalize-step-print-phase-breakdown:done,emit-landing:done,archive-plan:pending
step.branch-cleanup.merge_mechanism=merge_queue
step.branch-cleanup.merge_state=merged
step.record-metrics.total_tokens=5132687
step.record-metrics.total_wall_seconds=50448.0
step.record-metrics.any_phase_missing_end_time=false
step.create-pr.pr_number=1355
step.finalize-step-sync-baseline.action=noop
step.finalize-step-sync-baseline.upstream_commit_count=0
landing_commit=91a07aaa4ffe5007a39963aee4031e83d497155c
```

## Residue

**A stated denominator in a sibling epic's spec is wrong, and this run measured it.** TASK-4's blast-radius sweep over all 9 epic slugs returned 331 specs scanned, 26 unreadable, 26 blocking, partition `absent 104 / empty 0 / unreadable 26 / parsed 201` summing exactly to 331. `code-intelligence-substrate`'s stated expectation of 7 is CONFIRMED (7 of 64). `truthful-signals`' numerator of 19 is confirmed, but its denominator is REFUTED: 161 specs, not the 124 its spec states. Twice observed. Authoring form of the 26: table-form 7, prose-only 19, template-placeholder 0, fenced-only-body 0 — both zeros derived from a content sweep over 5,246 files, not merely unobserved. All 26 carry `section_verdict: absent`, so they are blocked rather than admitted; none was repaired, deliberately.

**Two live review-pipeline defects this run reproduced, both already filed as lessons routed here.** Lesson `2026-08-26-16-001`: a sourcery rate-limit refusal is credited as PARTICIPATION — a third, undocumented budget phrasing matches neither declared `refusal_pattern` nor the structural fallback, so `refused_bots[]`, `unrecognised_refusal[]` and `count_skipped_refusal` all came back empty and the summary read "2 reviewed" when one bot reviewed. It surfaced in three instruments (the FIND producer, the pre-merge barrier re-fetch, and the review-retrospective's per-reviewer scoring, where the refusal scored 0%-resolved as though the reviewer had failed rather than never run). Lesson `2026-08-26-17-001`: pr-agent is reported ABSENT because its ~22-minute response outruns `review_bot_buffer_seconds: 180`, and it publishes no check-run so `bot_completion` returns `no_check_name` and the buffer IS the whole wait. Two consecutive FINDs recorded it absent and consumed a loop-back iteration each; it had in fact reviewed. These are the false-green and false-red halves of one gap.

**The finalize dispatch ledger cannot see re-dispatch inside an already-entered step.** Seven `pre-submission-self-review` rounds produced 2 `[DISPATCH]` lines, 2 `effort resolve-target` records, and 2 boundary rows — all three channels hang off step ENTRY, so they share one blind spot. `6-finalize` records 2,883,328 accumulated tokens against a dispatch-boundary total of 1,555,736: roughly 36% of the phase carried by no boundary row, in the phase that is the majority of the plan's spend. `check-dispatch-audit.py::cmd_run` grades that gap `nominal` because it hands the correctly-scoped finalize count to one check and the UNSCOPED phases-2-6 count to `evaluate_channel_completeness`, so its `ratio: 1.0` is a coincidence of two unrelated populations; the finalize-scoped ratio is 12/22 = 0.545.

**An open question this run could not settle.** The cross-plan merge mutex was acquired at the widened-hold point and released at the terminal site as `action: noop, lock not held (already free)`, with no intervening explicit release. `work.log` shows the title token set 17:05:40Z and cleared 17:57:03Z — 51m10s, inside the 3600s hold budget — and no release payload in either log. A mutex that self-releases mid-hold would not be serializing what it claims to serialize, but this run cannot evidence the mechanism, so it is recorded as a question rather than asserted as a defect.

**Two tooling defects located in source.** `git_provider.py` carries `_DEFAULT_TIMEOUT_SECONDS = 60`; `git-workflow.py::cmd_worktree_remove` calls `run_git` with no override and branches on `rc != 0` once, attaching the same "pass `--force` only after verifying the worktree is clean" hint to rc 124 (timeout), rc 127, and a genuine dirty-tree refusal — and a timeout leaves the worktree PARTIALLY removed, so the retry then reads as dirty for a reason the first attempt caused. This fired twice on this plan. Separately, `pre-submission-self-review`'s `cohort_size` is round-scoped: `contract_drift` fired across four consecutive rounds for a cumulative 7 findings while the largest figure any record publishes is 2, which is exactly the closed-cohort illusion the field exists to prevent.

**The in-house gate found the substance; the bots found lint.** Seven full-surface self-review rounds found 10 real defects pre-push — every one a doc claiming something the code does not provide, the same class this plan was written to fix, including a recovery path that was unreachable from BOTH write-side callers. The three review bots contributed one markdownlint MD038 nit between them. The comparison carries a confound worth keeping: the self-review runs at orders 5-7, so the bots reviewed a tree those 10 defects had already been removed from, and this run therefore does not measure whether they would have caught them.
