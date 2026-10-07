envelope_version=1
sender_type=plan
sender_id=freshness-gate-says-fresh-unexamined-tree
epic=truthful-signals
kind=landing
created=2026-09-06T17:37:19Z

# PLAN-TRUTH-128 landed — the freshness gate now says which kind of pass it gave

The overloaded `fresh` token is split. `cmd_pre_commit_verify_freshness()` returned the same
`fresh` for a ledger-scanned corroborated build and for a `build-decision` `not_necessary`
short-circuit that never reached the ledger at all, and `push.md`'s fail-closed contract branched on
the token alone — so a push could proceed on a gate that never looked. The exempt route now returns
its own status member, `exempt`. It still permits (a docs-only footprint must not deadlock) but on a
legible basis, and both fail-closed consumers record which basis they passed on
(`basis=ledger-verified` / `basis=exempt-unscanned`).

The token shape was settled on evidence, not preference: ADR-019 obligation 3 governs because the
exempt route never *applies* the predicate, and ADR-009 rejects the alternative shape by name. The
derivation met ADR-009's precondition for a clean break — a 33-member consumer population, all 10
branching consumers inside `plan-marshall`, the one cross-bundle member reading no status.

```landing-facts
schema=landing-facts/1
plan_id=freshness-gate-says-fresh-unexamined-tree
epic=truthful-signals
pr=#1425
merge_state=merged
deliverables_total=5
deliverables_done=5
total_tokens=8494039
total_wall_seconds=90153
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,pre-push-quality-gate:done,project:finalize-step-plugin-doctor:done,pre-submission-self-review:done,finalize-step-simplify:done,architecture-refresh:done,push:done,create-pr:done,project:finalize-step-era-stamp-fill:done,ci-verify:done,automatic-review:done,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:done,project:finalize-step-review-retrospective:done,plan-marshall:plan-retrospective:done,lessons-capture:done,finalize-step-preference-emitter:done,record-metrics:done,finalize-step-print-phase-breakdown:done,emit-landing:done
step.create-pr.pr_number=1425
step.branch-cleanup.action=merged
step.branch-cleanup.merge_mechanism=merge_queue
step.branch-cleanup.merge_state=merged
step.branch-cleanup.work_performed=true
step.finalize-step-sync-baseline.action=rebased
step.finalize-step-sync-baseline.upstream_commit_count=1
step.record-metrics.total_tokens=8494039
step.record-metrics.total_wall_seconds=90153
step.record-metrics.any_phase_missing_end_time=false
```

## Residue

Three observations this run surfaced that no step recorded as a fact, carried as prose rather than
forced into a typed key.

**The premise in the spec was refuted.** `-128` named `push.md` as "the sole fail-closed consumer".
It is not: `phase-5-execute/SKILL.md` Step 12a is co-equal with the identical defect, and
`test_build_class_stamp_discriminator.py` is a third, branching *test* consumer. A fourth drifted
describe-site (`pre-push-quality-gate.md:184`) was also outside the spec's list. The outline moved
all of them from conditional into the definite surface.

**D0(c) is unanswerable, not clean.** The spec asked whether the exempt path has ever permitted a
real push. It has not been answered and cannot be from HEAD's records: `push` only ever recorded
`"pushed {branch}"`, so the discriminator this plan adds never existed to be swept for. That is a
coverage gap, not a zero — and it is why the defect stays latent-by-assumption rather than
latent-by-measurement.

**Reviewer coverage was 2/3 by participation but 1/3 by yield.** Both required bots participated at
the merged HEAD; CodeRabbit filed 9 actionable comments across three reviews (88.9% resolved-as-fixed,
zero false positives) while `cuioss-review-bot` published "No major issues detected" on the same
diffs every time. The participation quorum this run passed would have passed identically had both
required reviewers published nothing. `sourcery` was `refused_hard` on a 7-day budget for the entire
run — the PR ships with no Sourcery coverage, and no wait inside the run could close that.

## Owed follow-up

Ten lessons were filed against this run, seven of them instances of this epic's own archetype found
in our own tooling: a build wrapper reporting "no structured errors were parsed" over a log that
carried them; `review_commitments reconcile` returning `clear` over an empty population;
`pr wait-for-comments` reporting "no reaction" four times while reactions were present;
`pr merge-queue` reporting `enqueued: true` corroborated only by the branch rule; CodeRabbit's ETA
patterns missing its own stated wording; a detected gap forwarded to a receiver that does not exist;
and `--head-at-completion` accepting an unvalidated free string on the field that drives stale-record
detection.

The highest-value one is not a tooling bug: `pre-submission-self-review` fired 8 times, reported
"75 candidates examined, no check matched", and CodeRabbit then filed 4 items in classes
`ext-self-review-plan-marshall` already declares. It examined the right population with the right
classes and matched nothing.
