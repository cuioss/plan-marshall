envelope_version=1
sender_type=plan
sender_id=plan-truth-139
epic=truthful-signals
kind=landing
created=2026-09-13T14:23:39Z

## What landed

plan-truth-139 shipped as #1479 (merged): `build.queue.max_slots` now has one machine-scoped home read by both consumers, the per-repo key is demoted to an audibly-not-in-effect override, and the config-scope population is published as an audit.

```landing-facts
schema=landing-facts/1
plan_id=plan-truth-139
epic=truthful-signals
pr=#1479
merge_state=merged
cleanup_owed=false
deliverables_total=8
deliverables_done=8
total_tokens=11600752
total_wall_seconds=450494
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,pre-push-quality-gate:done,project:finalize-step-plugin-doctor:done,pre-submission-self-review:done,finalize-step-simplify:done,finalize-step-security-audit:done,architecture-refresh:done,push:done,create-pr:done,project:finalize-step-era-stamp-fill:done,ci-verify:done,automatic-review:done,sonar-roundtrip:done,adr-propose:skipped,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:done,project:finalize-step-review-retrospective:done,plan-marshall:plan-retrospective:done,lessons-capture:skipped,finalize-step-preference-emitter:done,record-metrics:done,finalize-step-print-phase-breakdown:done,emit-landing:done,archive-plan:done
step.branch-cleanup.merge_mechanism=merge_queue
step.branch-cleanup.action=merged_by_operator
step.create-pr.pr_number=1479
step.finalize-step-sync-baseline.action=rebased
step.finalize-step-sync-baseline.upstream_commit_count=5
step.record-metrics.total_tokens=11600752
step.record-metrics.total_wall_seconds=450494
loop_back_iterations=4
loop_back_ceiling=5
```

## Residue

Seven findings were filed rather than fixed here, each routed out by subject:

- **review-apparatus** — `plan-truth-139-001.md` (this epic's inbox message names it too): the participation detector reported `cuioss-review-bot` as non-participating when its review WAS published; the operator ruled the detector is the defect. Plus `af8660` (the currency test's first-observation arm credited a bot from a comment predating the reviewed range — a false green at the review gate), `867ba4` (no `escalate_ask` reason covers "window claimed, wait delegated to the orchestrator"), `5c3027` (CodeRabbit's `rate_limit_eta_patterns` do not match its own reset phrasing, so the derived window falls back to a default), and `154f51` (the producer noise filter admits our own trigger comments and the bot's own acks as findings).
- **truthful-signals** — `367874`: `sonar-roundtrip` reports `count_status: confirmed` with zero new-code issues while NO Sonar analysis has ever run for the PR (gate 404, newest CE task months old, provider not activated). `confirmed` attests only that the CE queue was settled and empty, so the zero is an empty-surface zero and is structurally indistinguishable from a clean scan. Recurs on every plan in this repo until Sonar is wired into PR CI. Plus `409263` (`triage.md` prescribes `deliverable: 0` for a fix task, which the validator rejects on a falsy check) and `805bc7` (in-process build env inheritance, declined here as out-of-footprint).

Two observations the run recorded about its own gates, both worth the epic's attention:

- The security audit closed FOUR unsanitised report boundaries and CodeRabbit then found the FIFTH — in a function whose declared mirror already routed through the sanitiser. That is a population-derivation gap, not a hard limit of the analysis.
- Two of this run's own fixes introduced the inverse of the defect they fixed: the fix for a false REFUSAL created a possible false SUCCESS (`574fd5`), and the operator-requested single-definition guard was blind to the dictionary carrier that was the actual historical seeder (`9c441d`). Both were caught by the external reviewer, not by the in-house gates.
