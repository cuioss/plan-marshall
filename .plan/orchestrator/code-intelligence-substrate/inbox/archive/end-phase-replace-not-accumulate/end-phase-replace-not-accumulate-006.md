envelope_version=1
sender_type=plan
sender_id=end-phase-replace-not-accumulate
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-07-29T17:22:03Z

component=plan-marshall:plan-retrospective
category=bug
created=2026-07-29

# The retrospective grades a plan's footprint after branch-cleanup has already deleted the worktree it measures

`plan-marshall:plan-retrospective` is step 17 of the phase-6 manifest and `branch-cleanup` is step 16. Branch-cleanup removes the plan's worktree. Every footprint-derived retrospective aspect therefore runs against a worktree that no longer exists.

In this plan's own run, `check-artifact-consistency` reported:

```
affected_files_recall,fail,Recall 0% below 70% threshold
declared: 6
found: 0
recall_pct: 0.0
```

The true recall is **100%**. All 6 declared files are present in the squash-merge commit `dfe7fde0b`, verified by `git show --stat`. The plan had zero scope creep and perfect declared-vs-realized agreement, and was graded as a total coverage miss.

## Root cause

The aspect's own coverage contract documents exactly two footprint sources: derived live from the plan's worktree when one is on disk, falling back to the legacy `references.modified_files` key **only for archived plans**. A plan sitting between branch-cleanup and archive-plan is in neither state — the worktree is gone AND the plan is still live — so the footprint resolves to the empty set and no fallback fires. The failure is silent: the aspect returns `status: success` with a confident numeric `recall_pct: 0.0` rather than reporting that it had no footprint to measure.

## Impact

This is not a cosmetic mis-grade. Three aspects consume the same footprint — `check-artifact-consistency`, `check-manifest-consistency`, and `check-routing-decisions` — and all three silently degrade. In this run the retrospective had to reconstruct the footprint by hand from the merge commit to make aspects 12 and 13 meaningful at all. Any archived retrospective produced since the retrospective step was ordered after branch-cleanup carries the same false 0% recall, so the corpus-level `scope-estimate accuracy` and `declared-vs-achieved coverage` audit checks are reading a systematically zeroed input.

Note the shape: a measurement instrument reporting `0.0` where it should report "not measurable" is the same confident-signal-hides-a-caveat failure the plan-marshall corpus keeps re-encountering, and here it lives in the component whose whole job is grading other components.

## Suggested corrective action

Give the footprint resolver a third tier, in this order:

1. worktree on disk → derive live from `{base}...HEAD` union porcelain (unchanged);
2. worktree absent AND a PR number is resolvable from `references.json` / `status.metadata.pr_number` → derive from the merged squash commit for that PR;
3. archived plan → legacy `references.modified_files` (unchanged).

When none of the three resolves, the aspect MUST report the footprint as unavailable (a `skipped` check with an explicit reason token) rather than emitting a numeric `recall_pct` computed against an empty set.

Consider additionally whether `plan-marshall:plan-retrospective` should simply be ordered BEFORE `branch-cleanup` in the default manifest. That ordering question is the same one PLAN-10's own landing already raised for cache-sync-at-step-19 versus retrospective-at-step-17, so a single ordering review could resolve both.
