envelope_version=1
sender_type=plan
sender_id=a-failing-ci-call-reports-success
epic=review-apparatus
kind=landing
created=2026-08-27T15:54:40Z

## What landed

a-failing-ci-call-reports-success shipped as #1356 (merged).

```landing-facts
schema=landing-facts/1
plan_id=a-failing-ci-call-reports-success
epic=review-apparatus
pr=#1356
merge_state=merged
deliverables_total=6
deliverables_done=6
total_tokens=11431698
total_wall_seconds=120159.0
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,pre-push-quality-gate:done,project:finalize-step-plugin-doctor:done,pre-submission-self-review:done,finalize-step-simplify:done,architecture-refresh:done,push:done,create-pr:done,project:finalize-step-era-stamp-fill:done,ci-verify:done,automatic-review:done,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:done,project:finalize-step-review-retrospective:done,plan-marshall:plan-retrospective:done,lessons-capture:done,finalize-step-preference-emitter:done,record-metrics:done,finalize-step-print-phase-breakdown:done,emit-landing:done,archive-plan:pending
step.branch-cleanup.merge_mechanism=merge_queue
step.branch-cleanup.action=rebased
step.branch-cleanup.upstream_commit_count=5
step.create-pr.pr_number=1356
step.record-metrics.any_phase_missing_end_time=false
landing_commit_sha=26645688bf2fb43a96e574e4d946993303efb088
loop_back_iterations=3
```

## Residue

- **`archive-plan:pending` is structural, not a gap this run could close.** `emit-landing` is `order: 1000` and `archive-plan` is `order: 1100`, so the archive outcome does not exist when this message is written. Every other step's outcome is its recorded terminal value.

- **Reviewer coverage was one bot deep on a 4493-line diff.** Of three enabled reviewers, exactly one was measurable: `coderabbit` produced all 22 `pr-comment` findings (16 actionable, 100% of resolved-actionable resolved as `fixed`) and was at its 1-review-per-hour ceiling throughout. `pr-agent` — the sole REQUIRED bot — resolved `participated_but_empty` on every HEAD, reporting "No major issues detected" on the same diff where coderabbit filed a Major finding. `sourcery` refused STRUCTURALLY on every HEAD (`cause=size`, stated cap 150000 diff characters vs 4493 changed lines) and read none of it. `participation_complete: true` was therefore satisfied by a quorum in which one optional, quota-limited bot did all the reading. This is participation, not review quality.

- **The `cohort_size`-of-1 artefact is the instrument defect this run exposed.** Nine of ten `pre-submission-self-review` findings published a per-round class count as though it were a property of the tree. Three consecutive rounds each closed exactly ONE member of the same `contract_drift` class and reported `cohort_size: 1`; a directed exhaustive class-closure sweep then found FOUR at once, including one (`verification-feedback.md`'s `pr-state` producer) that collapsed every `ci pr view` non-success into "no PR exists" and returned a clean "nothing to triage" — a vacuous green in the very component this epic governs. Already routed as candidate-lesson `-001`.

- **The plan repeatedly reproduced its own target defect.** TASK-021 introduced the closed five-field enumeration TASK-023 existed to remove; TASK-022 replaced an *unreachable* honest-degradation branch with an *over-reachable* one (branching on bare `status: error`, which `cmd_resolve` returns from four paths, three of which prove nothing), caught one round later by finding `5ca1b4`; TASK-020 widened 9 of 18 exit-code-convention carriers and broke 16 tests. The vacuous-guard archetype recurring inside its own remedy.

- **One live defect filed, not fixed: finding `5ec6d3`.** `github_re_review`'s `head_sha_verified` extractor does not recognise a reviewed-commit SHA embedded in a commit URL. A pr-agent Guide reading "Review updated until commit https://github.com/cuioss/plan-marshall/commit/6fc21555..." returned `head_sha_verified: false`, which `branch-cleanup-rereview.md` routes into `declined_bots` → the blocking `declined` state at the pre-merge barrier. Left un-actioned this manufactures a FALSE merge block on a bot that genuinely reviewed the HEAD. Note `fetch_findings`' own participation detector credits the same comment shape as `participated`, so two detectors disagree on one artifact.

- **Cost shape, not correctness, is the headline.** 11.4M tokens against a `(multi_module, bug_fix)` anchor of 2.0M, across 3 loop-back iterations and 12 `pre-submission-self-review` firings. The retrospective measured 2,189,320 tokens spent on 8 error-terminated dispatches that examined nothing and returned nothing — four of them clustered in a 14-second window before a `blocked_session_restart`, so one infrastructure event cost four dispatches while `retryable_total_tokens` read `0`.

- **A late upstream conflict forced an operator gate.** PR #1359 landed on `main` mid-finalize and edited the same four files this plan did, taking the PR to `mergeable: conflicting`. The classifier returned `overlap_with_content_conflict` / `auto_reconcilable: false`, the operator authorized rebase-and-resolve, and 33 commits were replayed with 0 skipped, all four conflicts resolved additively (both sides preserved). This is the `use_merge_queue: true` rebase-skip being deliberately overridden: the platform queue cannot accept a conflicting PR, so a conflict-resolving rebase is the precondition for any enqueue — a case the routing section does not currently name.
