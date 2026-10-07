envelope_version=1
sender_type=plan
sender_id=always-on-is-not-a-resolve
epic=operator-ux
kind=landing
created=2026-09-03T19:31:32Z

## What landed

always-on-is-not-a-resolve shipped as #1391 (merged).

```landing-facts
schema=landing-facts/1
plan_id=always-on-is-not-a-resolve
epic=operator-ux
pr=#1391
merge_state=merged
deliverables_total=2
deliverables_done=2
total_tokens=3987911
total_wall_seconds=44454.0
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,pre-push-quality-gate:done,project:finalize-step-plugin-doctor:done,pre-submission-self-review:done,finalize-step-simplify:done,architecture-refresh:done,push:done,create-pr:done,project:finalize-step-era-stamp-fill:done,ci-verify:done,automatic-review:done,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:done,project:finalize-step-review-retrospective:done,plan-marshall:plan-retrospective:done,lessons-capture:done,finalize-step-preference-emitter:done,record-metrics:done,finalize-step-print-phase-breakdown:done,emit-landing:done,archive-plan:pending
step.branch-cleanup.merge_mechanism=merge_queue
step.branch-cleanup.merge_state=merged
step.create-pr.pr_number=1391
step.record-metrics.any_phase_missing_end_time=false
```

## Residue

- **Reviewer coverage on #1391 was near-zero, and the quorum does not say otherwise.** `review_completeness` returned `participation_complete: true` with `proves: participation_only`. The bot states behind that pass: `pr-agent` (required) `participated_but_empty`, `coderabbit` `absent`, `sourcery` `refused_hard` (cause `quota`, ETA ~3d17h). Zero comments here means near-zero review, not a clean review. The `project:finalize-step-review-retrospective` step reached the same conclusion independently and recorded `comparative_verdict: unmeasurable`.

- **A scope deviation was accepted in-plan by the operator.** Sourcery declined review with a third, unregistered refusal wording (`used your own review budget of ... for the last 7 days`). No refusal-recognition arm fired, so the bot was credited as *participating* in a review it declined — the false-green the refusal branch exists to prevent. The operator chose FIX-here-anyway over Split, so the fix landed on this PR outside its original footprint: `automatic-review/standards/sourcery.md` (third `refusal_patterns` entry, `rate_limit_eta_patterns` populated) plus two tests. Verified working in the same run: the pre-merge barrier's re-fetch classified sourcery into `refused_bots` with cause `quota`.

- **The pre-push quality gate does not cover what review sees.** `pre-push-quality-gate` is `order: 5`; `finalize-step-simplify` is `order: 8`. The gate certified `43ed295b`, simplify then advanced HEAD to `8827a7f2`, so the tree reviewers saw was never locally gated. The review-retrospective recorded its review-vs-gate delta as `excluded` / `gates_did_not_cover_reviewed_tree` with `structural_share: null` — withheld, not zero. Lesson `2026-09-03-11-002` already tracks this ordering hole.

- **Cost is the dominant finding.** A `single_module` / `bug_fix` plan touching 5 files spent 3,987,911 tokens and 12h20m wall (2h26m worked). `6-finalize` alone is 2,476,740 tokens. Driver: HEAD moved four times inside finalize, re-arming every head-bound step — `pre-push-quality-gate` and `finalize-step-simplify` fired 4x each for 3 implementation tasks; `automatic-review` fired 3x, `ci-verify` 2x. One dispatch terminated in `error` for zero detection.

- **`prune-local-and-remote-ref` has an ordering bug with `worktree-remove`.** `worktree-remove` deletes the local branch ref as part of its own cleanup, so the later `prune-local-and-remote-ref` fails `branch_delete_failed` on an already-absent branch and aborts *before* its remote-tracking step — leaving `refs/remotes/origin/{branch}` stale. This run issued the single targeted `update-ref -d` the standard permits and verified both refs gone, but the verb should tolerate an already-deleted local branch rather than abandoning the remote-ref prune.

- **Argparse-position recurrences continue.** Nine script-call rejections across the run, on `manage-references`, `ci pr prepare-body` / `ci pr edit` (the router-vs-verb `--plan-id` split), `manage-status read`, and `phase_handshake`. The `ci` position trap is documented in the standards and was hit anyway, including by the main orchestrator. Four candidate-lessons (`-008` through `-011`) target making the rejection teach its own fix.
