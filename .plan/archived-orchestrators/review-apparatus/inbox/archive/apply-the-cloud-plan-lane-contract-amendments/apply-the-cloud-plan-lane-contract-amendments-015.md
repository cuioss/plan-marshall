envelope_version=1
sender_type=plan
sender_id=apply-the-cloud-plan-lane-contract-amendments
epic=review-apparatus
kind=landing
created=2026-09-05T06:34:42Z

## What landed

apply-the-cloud-plan-lane-contract-amendments shipped as #1416 (merged) — three long-deferred cloud-plan-lane contract amendments applied from outside the lane, plus surface attribution and a narrowed `.plan/` carve-out.

```landing-facts
schema=landing-facts/1
plan_id=apply-the-cloud-plan-lane-contract-amendments
epic=review-apparatus
pr=#1416
merge_state=merged
deliverables_total=6
deliverables_done=6
total_tokens=4790971
total_wall_seconds=66631.0
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,pre-push-quality-gate:done,project:finalize-step-plugin-doctor:done,pre-submission-self-review:done,architecture-refresh:done,push:done,create-pr:done,project:finalize-step-era-stamp-fill:done,ci-verify:done,automatic-review:done,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:done,project:finalize-step-review-retrospective:done,plan-marshall:plan-retrospective:done,lessons-capture:done,finalize-step-preference-emitter:done,record-metrics:done,finalize-step-print-phase-breakdown:done,emit-landing:in_progress,archive-plan:pending
step.branch-cleanup.merge_mechanism=merge_queue
step.branch-cleanup.action=merged
step.create-pr.pr_number=1411
step.record-metrics.any_phase_missing_end_time=false
step.finalize-step-sync-baseline.upstream_commit_count=2
step.pre-submission-self-review.firing_count=5
step.automatic-review.firing_count=3
step.ci-verify.firing_count=3
step.push.firing_count=2
```

## Residue

**1. The `pr` fact and `create-pr`'s recorded fact disagree, and the landing carries the later one.**
`create-pr` recorded `pr_number=1411`. That PR was **closed without merging** during the CodeRabbit
acquisition; #1416 is the PR that merged (`branch-cleanup` recorded `merge_state=merged` and named
#1416). `create-pr` never re-fired, so its fact is stale rather than wrong-at-write-time. The landing
carries `pr=#1416` under `emit-landing`'s own derived-figure timing rule — *"taken any earlier it is
not an early reading of the same number but a different number, and the landing reports it as
settled"* — and preserves the original as `step.create-pr.pr_number=1411` so nothing is lost.
**Producer gap for the epic:** the landing spec sources `pr` from `create-pr`'s fact, which is only
correct when the PR that was created is the PR that merged. A run that replaces its PR mid-finalize
(close/reopen as a review trigger is a sanctioned technique in this repo) makes that source stale with
no mechanism to refresh it. `branch-cleanup` knows the real number but records it only in prose
`display_detail`, not as a typed fact.

**2. Duplicate step record for the retrospective.** `phase_steps["6-finalize"]` carries BOTH
`plan-marshall:plan-retrospective` (recorded by the step itself) and a bare `plan-retrospective`
(recorded by the orchestrator). Both say `done` with different `display_detail` values. The manifest
step id is the prefixed form; the bare one is an orchestrator-side bookkeeping artifact and is
harmless, but it inflates any count taken over `phase_steps` and would defeat a naive
`len(phase_steps) == len(manifest.steps)` handshake.

**3. `status.json` phase drift, corroborating the retrospective.** `phases[]` records `2-refine` as
`in_progress` while the plan sits at `6-finalize`, and `progress` reports `completed_phases: 4` where
five phases are genuinely complete. The light planning lane collapses refine+outline+derive into one
envelope and never closed out `2-refine`. Not repaired here — a hand-write to `status.json` this close
to `archive-plan` risks more than the inaccuracy does.

**4. `finalize-step-preference-emitter` is structurally unreachable for review-driven plans.** Four
admissible dispositions aggregated into two tuples; the `accepted` tuple recurred 3 times and cleared
`preference_min_recurrence=2`, then was dropped by the attribution gate as an unattributed `default`
bucket. Cause: `pr-comment` finding records carry **no `module` and no `component` field at all**, so
module attribution always falls back to `default` and the gate always drops them. For any plan whose
dispositioned findings are exclusively `pr-comment` — every doc-only and every review-driven plan —
this step can never promote a pattern regardless of recurrence strength. The threshold knob is not the
binding constraint; the missing attribution is.

**5. The merge crossed a review barrier under an explicit authorization, not a clean pass.**
`merge_authorizations` carries `barrier-ask-override` at head `30b32598457c9d221771392625b770c65853e71f`,
gap class `review-barrier-gap`, granted because `cuioss-review-bot`'s participation read as unproven
**only** through the known `head_sha_verified` comment-arm defect (`github_re_review.py:394` hard-codes
`matched_signal == 'review'`, so the comment arm can never verify a SHA). This is the **third**
occurrence of that defect on this epic's plans. The bot's own comment body names the reviewed commit
verbatim, which is what the grant rests on.

**6. Owed follow-ups this run created but did not discharge.** The marshalld daemon reconcile was
**deferred (owed x1)** because a build was in flight at sync time. `finalize-step-review-retrospective`
compared 3 reviewers over 3 actionable comments. One CodeRabbit Major (`89625f`, `.plan/` write
enforcement in the cloud lane) was dispositioned `taken_into_account` — verified and recorded as owed
follow-up work, deliberately not fixed, because the remedy lands in `.claude/settings.json` or a hook
and neither prescribed mechanism can distinguish a lane run from an ordinary one.

**7. Review acquisition cost.** Four PRs (#1412–#1415) were opened purely as CodeRabbit review
triggers; #1411 was the plan's legitimate PR and #1416 the one that merged. The winning technique was
pre-staging close+body and firing a single `pr create` within seconds of the stated hourly reset — the
constraint was contention, not exhaustion.
