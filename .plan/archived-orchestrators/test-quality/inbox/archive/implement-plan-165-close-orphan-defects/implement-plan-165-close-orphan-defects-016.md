envelope_version=1
sender_type=plan
sender_id=implement-plan-165-close-orphan-defects
epic=test-quality
kind=landing
created=2026-09-13T11:28:06Z

## What landed

implement-plan-165-close-orphan-defects shipped as PR #1480 (merged via the platform merge queue, landing commit c89beb88).

```landing-facts
schema=landing-facts/1
plan_id=implement-plan-165-close-orphan-defects
epic=test-quality
pr=#1480
merge_state=merged
cleanup_owed=no
deliverables_total=4
deliverables_done=4
total_tokens=4969190
total_wall_seconds=58542.0
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,pre-push-quality-gate:done,project:finalize-step-plugin-doctor:done,pre-submission-self-review:done,finalize-step-simplify:done,architecture-refresh:done,push:done,create-pr:done,project:finalize-step-era-stamp-fill:done,ci-verify:done,automatic-review:done,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:done,project:finalize-step-review-retrospective:done,plan-marshall:plan-retrospective:done,lessons-capture:done,finalize-step-preference-emitter:done,record-metrics:done,finalize-step-print-phase-breakdown:done,emit-landing:done,archive-plan:done
step.branch-cleanup.merge_mechanism=merge_queue
step.branch-cleanup.merge_state=merged
step.create-pr.pr_number=1480
step.finalize-step-sync-baseline.action=noop
step.record-metrics.any_phase_missing_end_time=false
merge_commit_sha=c89beb88b4291755f8eddd00253c71092df22c04
```

## Residue

Narrative-only items this run's step facts do not carry:

- **D4's strict serial reverse-order pass is UNMEASURED, not green.** `module-tests plan-marshall --no-parallel` with `PM_TEST_ORDER=reverse` was attempted twice and killed both times by host memory pressure; no daemon-side job survived either attempt, so no verdict exists in either direction. The reverse-order evidence that DOES exist is the canonical parallel form (21006 tests green). An earlier revision of the PR body asserted the serial pass had run and passed; that claim was false and was corrected in the body before the merge gate.

- **The merge-queue enqueue is unfalsifiable, and it cost this run two full budget windows.** `ci pr merge-queue` returned `enqueued: true` twice, corroborated only by "merge_queue rule active on branch" — which proves the queue RULE exists, not that this PR joined the queue. The PR sat `open`/`mergeable`/`clean` with all 11 checks green through both windows. It landed only after the operator enqueued it by hand. Recorded as candidate-lesson -001; flagged here because the landing's own `merge_state=merged` would otherwise read as a routine queue merge.

- **The pre-merge review barrier blocked on a stale required reviewer, and the prescribed loop-back would not have cleared it.** `cuioss-review-bot` had reviewed d55f2f90 but not the three commits that landed during review. Its registry declares no auto-review-on-push, and `automatic-review` was already recorded `done` at the live HEAD — so a bare loop-back would have SKIPPED the review step on the re-entry check and re-entered the barrier with the identical verdict. The remedy was the explicit re-review trigger the bot's registry names; the first trigger timed out at 559s, the second matched with the bot naming commit 56d5d442. Worth the epic's attention as a barrier/loop-back interaction, not just a bot latency.

- **`automatic-review` returned `escalate_ask{reason=re_review_timeout, outcome=declined}` on a HEAD the bot had in fact reviewed.** Both CodeRabbit and cuioss-review-bot publish re-reviews by editing a persistent issue comment in place, and that path reports `head_sha_verified: false` unconditionally — even when the body names the reviewed commit explicitly, as both did here. The escalation was resolved on evidence (a direct `fetch_findings` at the merge candidate) rather than by taking the `declined` verdict or by recording "proceeded unreviewed", which would have been false.

- **Sourcery scores 0% on every approved PR by construction.** Its registry declares no `review_body_summary_patterns`, so a content-free `**Approved.**` counts as actionable, enters the denominator, and can never enter the numerator. Surfaced by the review retrospective; a registry entry for the `### Sourcery assessment` shape would classify it meta, as CodeRabbit's status line already is.

- **CodeRabbit found a defect class the project's own self-review gate nominally covers.** The `ROUTES` mirror-list drift is a source-of-truth duplicate, surfaced by the reviewer on a branch where `pre-submission-self-review` had just recorded "10 candidates examined, no check matched". Both review escapes were classified gate-addressable: a rule exists for them and it did not fire.
