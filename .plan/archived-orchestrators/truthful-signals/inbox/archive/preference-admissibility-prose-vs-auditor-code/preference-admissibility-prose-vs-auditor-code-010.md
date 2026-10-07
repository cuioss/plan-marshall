envelope_version=1
sender_type=plan
sender_id=preference-admissibility-prose-vs-auditor-code
epic=truthful-signals
kind=landing
created=2026-09-05T14:33:04Z

## What landed

preference-admissibility-prose-vs-auditor-code shipped as #1398 — one executable authorship-admissibility predicate under `manage-findings`, delegated to by both the cross-plan auditor and the per-plan preference emitter, replacing the emitter's prose gate with a call.

```landing-facts
schema=landing-facts/1
plan_id=preference-admissibility-prose-vs-auditor-code
epic=truthful-signals
pr=#1398
merge_state=unknown
deliverables_total=4
deliverables_done=4
total_tokens=12067640
total_wall_seconds=250894.0
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,pre-push-quality-gate:done,project:finalize-step-plugin-doctor:done,pre-submission-self-review:done,finalize-step-simplify:done,architecture-refresh:done,push:done,create-pr:done,project:finalize-step-era-stamp-fill:done,ci-verify:done,automatic-review:done,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:done,project:finalize-step-review-retrospective:done,plan-marshall:plan-retrospective:done,lessons-capture:done,finalize-step-preference-emitter:done,record-metrics:done,finalize-step-print-phase-breakdown:done
step.finalize-step-sync-baseline.action=rebased
step.finalize-step-sync-baseline.upstream_commit_count=4
step.finalize-step-sync-baseline.work_performed=true
step.create-pr.pr_number=1398
step.record-metrics.total_tokens=12067640
step.record-metrics.total_wall_seconds=250894.0
step.record-metrics.any_phase_missing_end_time=false
```

## Residue

**`merge_state` is a producer gap, not an open PR.** `branch-cleanup` recorded NO typed facts at all — its
`phase_steps` entry carries `outcome`, `display_detail` and `head_at_completion` and no `facts` map — so the
`merge_state` fact this landing is specified to read does not exist. Per the spec's could-not-read class it is
written `unknown`, which correctly drains as INCOMPLETE at that key rather than as a settled end state. This is
the finding-#6 producer-gap shape: the step's own `display_detail` reads `merged via queue #1398, main pulled,
branch+worktree removed`, and `head_at_completion` is `d94c928580d9ab55a43b525273274ce4b39e0944`, but re-parsing
a merge state out of prose is exactly what the spec forbids. The fix belongs in `branch-cleanup`: record
`merge_state` (and `merge_mechanism`) as `--fact`.

**The `steps` list ends at `finalize-step-print-phase-breakdown` by construction.** The composed roster has 23
entries; the two absent from the list are `emit-landing` (this step, whose own outcome cannot exist while it
writes) and `archive-plan` (order 1100, which runs after). No step outcome is being withheld — the terminal pair
is structurally unrepresentable in a landing the terminal step itself emits.

**Token totals disagree across read points.** `record-metrics` closed the ledger at 12,067,640 tokens
(69h41m wall, 8h3m worked). The retrospective, reading before its own 200,496-token dispatch was accumulated,
reported 11.9M and measured the run at 4.7x its `multi_module + tech_debt` error anchor of 2.5M, with 77% of the
spend in `6-finalize`. Both figures are correct for their read point; the landing carries the closed-ledger one.
Cause: finalize loop re-firing — `pre-submission-self-review` fired 12 times with 7 consecutive failures, and six
other steps re-fired 6-7 times each. `firing_count` and `prior_firings[]` are already persisted per step and no
consumer reads them, so the data a circuit-breaker would need already exists.

**Billing weight is unmeasured on 5 of 6 phases.** `generate` returned
`totals_billing_weighted_total_population_count: 1` against `totals_population_denominator: 6`. The 149,214,666
billing-weighted figure is therefore a single-phase reading, not a run total, and must not be read as one.

**`automatic-review`'s recorded detail is stale.** It reads `1 comment(s) found - 1 reviewed, 1 empty, 1 refused
(unified triage pending)`; the triage subsequently completed — the findings store now holds 6 `accepted` and 2
`taken_into_account` `pr-comment` dispositions with 0 pending. The step never re-recorded after its triage closed.

**CodeRabbit review acquisition cost roughly a day of wall-clock.** `@coderabbitai review` is a documented no-op
against an already-enumerated HEAD ("applicable only when automatic reviews are paused"); the only remedy that
works is a NEW COMMIT, after which the automatic review fires. Combined with the 1-review-per-hour quota this
produced several refused windows. `use_merge_queue: true` was load-bearing at the merge gate: it skips the
pre-merge rebase and force-push, so the hard-won review survived to the merge.

**Three retrospective findings are already routed** as `candidate-lesson` messages 007/008/009 and are not
repeated here: `architecture search`/`find` returning a coverage-clean zero over a deleted worktree root (affects
every finalize step ordered after `branch-cleanup` — six ran here); every change-ledger build row stamped
`NO_PLAN`, making ~8.7h of build time unattributable; and cache accounting unmeasured on 41 of 41 dispatch rows.

**Retrospective coverage caveats, carried rather than papered over.** Permission-prompt analysis examined 4 of
1907 turns from 1 of 2 recorded sessions — a could-not-look, not a clean zero. `ARTIFACT_EMISSION` reported
`change_attribution: unavailable`. The `outline-vs-shipped` gating classes both had denominator 0
(`assessments_store_present: false`) while the top-level verdict read `comparison: measured`.
