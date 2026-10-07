envelope_version=1
sender_type=plan
sender_id=manage-lessons-mixes-local-time-and-utc
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T18:06:25Z

component=plan-marshall:plan-retrospective
category=bug
created=2026-07-29

# The declared-vs-achieved coverage check is structurally vacuous because it runs after the worktree is deleted

`check-artifact-consistency` derives the plan's realized footprint live from the plan worktree. In the manifest's `phase_6.steps` ordering, `branch-cleanup` (which removes the worktree) is step 14 and `plan-marshall:plan-retrospective` is step 15. By the time the coverage check runs, its only footprint source is gone.

On this plan the check reported:

```
affected_files_recall,fail,Recall 0% below 70% threshold
findings: warning,"Recall 0% below 70% threshold"
details.affected_files_recall: declared: 5, found: 0, recall_pct: 0.0
```

The merged commit `f8a361972` touches exactly the five declared files. **Real recall is 100%.** The check reported the worst possible coverage score for a plan with perfect coverage, and reported it as a substantive `warning` finding about the plan rather than as a data-availability problem with itself.

## Why it is a truthful-signal defect, not just a bug

`found: 0` is emitted with the same confidence and in the same field shape as a genuine `found: 0`. Nothing in the fragment says "footprint source unavailable". A reader of the report — or an aggregate audit across archived plans — sees a plan that declared five files and delivered none. The signal is not merely wrong, it is *confidently* wrong in the direction that manufactures false findings.

This is the same finalize-ordering archetype as PLAN-10: a step cannot be exercised by a finalize whose earlier steps have already destroyed its inputs.

## Solution

Two independent fixes, both needed:

1. **Fix the ordering or the source.** Either move `plan-marshall:plan-retrospective` ahead of `branch-cleanup`, or make the footprint derivation fall back to the merged commit / recorded branch tip when the worktree is absent.
2. **Make the absence honest regardless.** When the footprint source cannot be read, the check MUST emit `status: skip` with an explicit `footprint_source_unavailable` reason — never `fail` with `found: 0`. A check that cannot see its input must not report a score.

## Impact

Every orchestrated plan that runs the retrospective as a post-`branch-cleanup` finalize step produces a false 0%-recall warning. Any cross-plan audit that aggregates `affected_files_recall` over archived plans is reading a population contaminated by this, and the contamination is systematic (always 0%), not noisy — so it will not average out.
