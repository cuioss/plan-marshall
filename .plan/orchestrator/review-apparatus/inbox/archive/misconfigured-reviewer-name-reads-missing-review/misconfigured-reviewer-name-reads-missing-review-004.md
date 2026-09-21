envelope_version=1
sender_type=plan
sender_id=misconfigured-reviewer-name-reads-missing-review
epic=review-apparatus
kind=landing
created=2026-09-03T23:47:32Z

## What landed

misconfigured-reviewer-name-reads-missing-review shipped as #1392 (merged).

```landing-facts
schema=landing-facts/1
plan_id=misconfigured-reviewer-name-reads-missing-review
epic=review-apparatus
pr=#1392
merge_state=merged
deliverables_total=6
deliverables_done=6
total_tokens=7926426
total_wall_seconds=116539
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,pre-push-quality-gate:done,project:finalize-step-plugin-doctor:done,pre-submission-self-review:done,finalize-step-simplify:done,architecture-refresh:done,push:done,create-pr:done,project:finalize-step-era-stamp-fill:done,ci-verify:done,automatic-review:done,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:done,project:finalize-step-review-retrospective:done,plan-marshall:plan-retrospective:done,lessons-capture:done,finalize-step-preference-emitter:done,record-metrics:done,finalize-step-print-phase-breakdown:done,emit-landing:done,archive-plan:pending
step.branch-cleanup.merge_mechanism=merge_queue
step.branch-cleanup.action=merged
step.branch-cleanup.merge_state=merged
step.create-pr.pr_number=1392
step.record-metrics.total_billing_weighted=64172158
step.record-metrics.total_worked_seconds=33140
merge_commit_sha=cc5ea40a1a6e600e3a7a7b957eace9e085e21129
final_head_sha=39b6190388458696e98edf83c8a41a2b9f38950a
```

## Residue

**The shipped fix does not close the defect the plan was written for.** `unregistered_kind`
fires only for tokens outside the registry. `coderabbit` is a *registered* kind that was
merely sitting in `optional_bots`, so the new state never applies to it. A correctly-named
required reviewer placed in the wrong list still buys `participation_complete: true` with
zero diff-readers. Recorded as lesson `2026-09-03-23-003`.

**The false green reproduced inside this plan's own finalize.** Three of four
`automatic-review` iterations reported `participation_complete: true` / `proves:
participation_only` while no reviewer had read the diff — the required-bot quorum satisfied
by an empty `cuioss-review-bot` review while `coderabbit` was quota-refused and `sourcery`
refused structurally. An operator, not a gate, caught it.

**OWED — durable config correction.** The operator's mid-run fix was applied to the
plan-local manifest snapshot ONLY. Tracked `.plan/marshal.json` still reads
`required_bots: cuioss-review-bot` / `optional_bots: coderabbit,sourcery`. Every future plan
in this repo inherits the misconfiguration until `/marshall-steward` is run. A second
divergence on the same step (`review_rate_window_await` true in snapshot, false tracked) is
recorded as an observation to classify, not an assumed owed change.

**OWED — epic-invisible corpus entries.** The `plan-marshall:plan-retrospective` step was
dispatched with `orchestrated=false` / `epic=""` — an unverified assertion by this
orchestrator, corrected only afterwards. Its six lessons (`2026-09-03-23-001` … `-006`) plus
two recurrence merges (`2026-08-27-16-002`, `2026-09-03-00-001`) went to the GLOBAL lessons
store rather than this inbox. Inbox candidate `-002` carries the full index marked
do-not-re-file.

**Mechanism behind that misroute, located not guessed.** The composed manifest runs
`plan-marshall:plan-retrospective` (order 995) BEFORE `lessons-capture` (order 991) —
positions 17/18 inverted. Item 4b.a0, the sole site resolving `orchestrated`/`epic`, is
nested inside the lessons-capture gate, so the verdict's producer runs after its first
consumer. The same inversion is present in tracked `marshal.json`. Inbox candidate `-001`
names two untested leads rather than asserting the compose-layer cause.

**Efficiency observation, measured on this run.** `6-finalize` cost 4,419,369 tokens — 56%
of the plan total — and the settle band ran three full passes. Replay cost was at least
1,292,373 tokens (33% of finalize). Every head-dependent step re-fired on each HEAD advance
because it declares no `verdict_inputs` surface; `project:finalize-step-era-stamp-fill`, the
one step that DOES declare one, fired once and survived both advances. Eleven re-fires
against one.

**Ledger gap.** 736,467 tokens (19.6% of finalize dispatch spend) are invisible to any
`execution_log` sum, so `refire-report` under-reports the re-fire count by 4 firings —
concentrated on the steps that re-fire most.
