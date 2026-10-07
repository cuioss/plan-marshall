envelope_version=1
sender_type=plan
sender_id=shipped-guards-assume-the-meta-projects-own-layout
epic=truthful-signals
kind=landing
created=2026-09-05T07:59:08Z

## What landed

`shipped-guards-assume-the-meta-projects-own-layout` shipped as #1397; `branch-cleanup` recorded no `merge_state` fact, so the key is reported `unknown` — see Residue for what was independently observed.

```landing-facts
schema=landing-facts/1
plan_id=shipped-guards-assume-the-meta-projects-own-layout
epic=truthful-signals
pr=#1397
merge_state=unknown
deliverables_total=6
deliverables_done=6
total_tokens=11892145
total_wall_seconds=129905
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,pre-push-quality-gate:done,project:finalize-step-plugin-doctor:done,pre-submission-self-review:done,finalize-step-simplify:done,architecture-refresh:done,push:done,create-pr:done,project:finalize-step-era-stamp-fill:done,ci-verify:done,automatic-review:done,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:done,project:finalize-step-review-retrospective:done,plan-marshall:plan-retrospective:done,lessons-capture:done,finalize-step-preference-emitter:done,record-metrics:done,finalize-step-print-phase-breakdown:done,emit-landing:done,archive-plan:pending
step.create-pr.pr_number=1397
step.record-metrics.total_tokens=11892145
step.record-metrics.total_wall_seconds=129905
step.record-metrics.any_phase_missing_end_time=false
step.finalize-step-sync-baseline.action=rebased
step.finalize-step-sync-baseline.upstream_commit_count=1
step.finalize-step-sync-baseline.work_performed=true
```

## Residue

**`merge_state=unknown` is a producer gap, not an unknown merge.** `branch-cleanup` recorded
no `facts` sub-dict at all — no `merge_state`, no `merge_mechanism`, no `action` — so the
key this step is required to read from the step's own typed facts does not exist. The
payload spec forbids substituting a corroboration for the step's recorded claim, so
`unknown` is written rather than a value this step would be fabricating. What the run
actually observed, recorded here as operator narrative:

- `branch-cleanup`'s `display_detail` reads `merged 28b578f1e via queue, worktree removed, refs pruned`.
- The merge was independently corroborated two ways before this landing: PR #1397 state
  `merged`, and `git merge-base --is-ancestor 28b578f1e origin/main` exit 0. The
  double-check was deliberate — there is a recorded incident of `ci pr merge` returning
  `merged=true` while never merging.

So the plan did land. The gap is that `branch-cleanup` does not persist the fact its
consumer is specified to read, which makes every landing this epic drains report
`merge_state=unknown` for a successful merge. That is worth fixing at the producer.

**Orchestration verdict was misresolved mid-finalize.** The dispatcher forwarded
`orchestrated: false` / `epic: ""` to `lessons-capture`, which therefore took Branch A and
allocated into the GLOBAL lessons corpus instead of emitting candidate-lesson messages
here. Corrected in-run: the two candidates were re-emitted as messages 003 and 004, each
carrying a dedup note naming its global twin (`2026-09-05-07-007`, and a `## Recurrence`
appended to `2026-09-04-08-014`). The global artifacts were left in place rather than
destroyed. Message 005 files the defect itself, whose sharpest point is that
`emit-landing`'s presence in the manifest was already persisted independent evidence of
orchestration that no runtime consumer cross-reads.

**One gate shipped DEGRADED, deliberately, and is recorded as such.** The whole-tree
plugin-doctor arm emitted 173 false `manage-invocation-invalid` findings against the plan's
worktree and 0 against main on identical source (finding `cb3735`, resolution `accepted`,
already filed to this inbox). The gate was recorded DEGRADED rather than green, and
`pre-push-quality-gate`'s `display_detail` names the un-gated dimension. Unreachable by CI,
which checks out source and has no worktree executor.

**`pre-submission-self-review` terminated out-of-budget, not converged.** 12 rounds, 26
findings fixed, last round NOT clean, 15 firings of which 11 recorded `failed`. Operator
decision was to close the loop as out-of-budget and let PR review see the diff.

**Token figures are floors.** `enrich` attributed only 2 of 6 phases and 39 subagent calls
from the last session id; the plan spans two sessions (`58bafd5f…`, `66f3c434…`) and
`enrich` takes one. `totals_billing_weighted_total_population_count` is 2 of 6 for the same
reason. `any_phase_missing_end_time` is `false`, so every phase carries its boundary marker
— that says the rows were closed, not that the figures on them are complete.

**`uv.lock` is dirty on the main checkout.** The post-run tracked-source guard fired on it
at two consecutive post-merge steps. Content shows a uv re-resolution of ruff 0.16.4 →
0.16.6, side effect of `project:finalize-step-deploy-target`'s `./pw generate-claude` — a
step declaring `mutates_source: false`. Past the merge gate, so no push path remains on
this plan. Filed as finding `3d8e95`.
