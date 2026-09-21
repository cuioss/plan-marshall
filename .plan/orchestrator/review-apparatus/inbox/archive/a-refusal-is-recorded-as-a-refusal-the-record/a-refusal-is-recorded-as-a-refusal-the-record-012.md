envelope_version=1
sender_type=plan
sender_id=a-refusal-is-recorded-as-a-refusal-the-record
epic=review-apparatus
kind=landing
created=2026-08-31T08:24:04Z

## What landed

`a-refusal-is-recorded-as-a-refusal-the-record` shipped as #1368 (merge_state not recorded as a typed fact — see Residue).

```landing-facts
schema=landing-facts/1
plan_id=a-refusal-is-recorded-as-a-refusal-the-record
epic=review-apparatus
pr=#1368
merge_state=unknown
deliverables_total=7
deliverables_done=7
total_tokens=9883675
total_wall_seconds=131194.0
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,pre-push-quality-gate:done,project:finalize-step-plugin-doctor:done,pre-submission-self-review:done,finalize-step-simplify:done,architecture-refresh:done,push:done,create-pr:done,project:finalize-step-era-stamp-fill:done,ci-verify:done,automatic-review:done,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:done,project:finalize-step-review-retrospective:done,plan-marshall:plan-retrospective:done,lessons-capture:done,finalize-step-preference-emitter:done,record-metrics:done,finalize-step-print-phase-breakdown:done,emit-landing:unknown,archive-plan:unknown
step.create-pr.pr_number=1368
step.record-metrics.total_tokens=9883675
step.record-metrics.total_wall_seconds=131194.0
step.record-metrics.any_phase_missing_end_time=false
```

## Residue

**`merge_state` is `unknown`, and the PR did in fact merge.** `branch-cleanup` recorded
`outcome: done` with `display_detail: "merged via queue as 31d42db87 (squash); PR state read
from PR itself"` but wrote **no `facts` sub-dict at all** — no `merge_state`, no
`merge_mechanism`, no `action`, no `work_performed`, despite declaring all four in its
`records_facts` frontmatter. `emit-landing` reads the typed fact and is forbidden from
re-parsing `display_detail`, so the only honest value is `unknown`. The landing is therefore
INCOMPLETE at `merge_state` for a producer-side reason, not because the merge state was
genuinely unobservable: the squash landed as `31d42db871eb1ed6095868b42af85e8162ef4a8e`
(`fix(automatic-review): thread refusal cause and account declines (#1368)`), confirmed on
`main`. **This is a `records_facts` both-direction contract violation in
`default:branch-cleanup` — it declares four facts and records none.**

**`steps` reports `emit-landing` and `archive-plan` as `unknown`, and that is a spec gap, not a
run defect.** The `steps` key is specified as "every finalize step in composed order", but
`emit-landing` sits at `order: 1000` and `archive-plan` at `1100`, so the producer structurally
cannot know its own outcome or archive's when it writes. No producer of this key can ever
satisfy the spec as written. Recorded here rather than papered over with a fabricated `done`.

**The finalize run was resumed across sessions after a merge-FIFO deadlock.** The post-merge
tail (`integrate_into_main` move-back, worktree removal, remote-ref prune, the four
post-`branch-cleanup` steps) did not run in the merging session. On resume,
`merge_lock acquire` returned `admission: blocked` with `waiting_count: 2` while
`merge_lock check` reported the lock **free** — a parked front waiter
(`detector-and-auditor-integrity`) held the FIFO head with no session polling it. Two
observations for the epic: (a) a plan-dir-alive waiter is never pruned, so a parked plan blocks
every later plan's move-back indefinitely; (b) the blocked payload reported
`blocking_plan_id: null` even though a blocking waiter existed, so the diagnostic named nobody.
Cleared by `merge_lock release --plan-id detector-and-auditor-integrity`.

**`merge_commit_sha` could not be taken from `switch-and-pull` HEAD on a delayed re-entry.**
`branch-cleanup.md` § "Record the landing commit SHA" says to record `git rev-parse HEAD` after
the pull. On this resume `main` had already advanced to `8bc4a68f6` (a sibling plan's landing)
and `commits_pulled: 0`, so following the step literally would have recorded another plan's
commit as this plan's landing — silently corrupting the footprint resolver's merge-commit
fallback tier. Recorded `31d42db871eb1ed6095868b42af85e8162ef4a8e` instead.

**`uv` is not on PATH in the finalize shell.** `project:finalize-step-deploy-target` prescribes
`uv run python marketplace/targets/generate.py`; that failed with exit 127. Ran via
`.venv/bin/python3` instead. The step doc assumes a `uv` on PATH that this machine's finalize
shell does not have.

**Review coverage on the merged PR was 1 of 3 reviewers.** `project:finalize-step-review-retrospective`
found only `coderabbitai` measurable; `sourcery-ai` and `cuioss-review-bot` (pr-agent — the
*required* bot) both `unmeasurable` (enabled, zero records). No human review record exists on
#1368. The merge proceeded under the operator-granted `barrier-ask-override` recorded in
`status.metadata.merge_authorizations`. The delta verdict was excluded
(`gate_tree_unsubstantiated`): the `pr-comment` findings carry three distinct
`reviewed_commit_sha` values from the loop-backs, all predating the gate head, so
`structural_share` is withheld rather than zero.

**Prior inbox traffic from this plan:** `-001` (finding) and `-002`…`-011`
(candidate-lesson) are already filed; this landing does not restate them.
