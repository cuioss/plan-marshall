envelope_version=1
sender_type=plan
sender_id=plan-203-inbox-consumed-vs-missing
epic=truthful-signals
kind=candidate-lesson
created=2026-07-30T10:22:30Z

# check-artifact-consistency derives its footprint from a worktree branch-cleanup already removed

component: plan-marshall:plan-retrospective
category: bug
confidence: high
source: plan-retrospective (plan-203-inbox-consumed-vs-missing)

## Context

`check-artifact-consistency` reported for PLAN-203:

```
affected_files_recall,fail,Recall 0% below 70% threshold
details.affected_files_recall: declared: 13, found: 0, recall_pct: 0.0
```

with all declared files listed under `missing[]`. The true footprint of the merged commit
(`e82b466ee`) is 8 files, every one of them declared. The real recall over write-intent declarations is
8/8.

## Root cause

The aspect derives the footprint live from the plan's worktree (`{base}...HEAD` union porcelain). In
the finalize manifest, `branch-cleanup` is step 16 and removes the worktree; `plan-marshall:plan-retrospective`
is step 17. The footprint source is therefore **guaranteed absent** every time this check runs inside a
finalize flow. The check does not distinguish "no changed files" from "no tree to look at" — it returns
`found: 0` and grades that as a 0% recall failure.

This is the audited plan's own archetype, in the retrospective tooling that audited it.

## Compounding defect (filed separately as well)

Five of the 13 "missing" declarations are deliverable-4 gate inputs carrying `intent: read`. Even with a
live worktree the comparison would report a false over-declaration, because `references.json` flattens
`intent` away.

## Proposed action

1. When no worktree is present, fall back to a commit-based footprint. The plan already records
   per-deliverable commit SHAs in `work.log` (`1f7385665`, `0809a6376`, `4644cce9c`, `a1bd759d5`) and
   the merge commit is resolvable from the PR number in `phase_steps`.
2. If no footprint source can be resolved, emit `status: skipped` with reason
   `footprint_source_unavailable` — never a 0% recall `fail`. A coverage check that cannot see the
   footprint must say so, not grade it as zero coverage.
3. Consider whether `plan-marshall:plan-retrospective` should be ordered before `branch-cleanup` in the
   default finalize step list. Note the known finalize-ordering constraint: a plan that fixes a
   finalize-time component cannot have that fix exercised by its own finalize.

## Evidence

- fragment-artifact-consistency.toon — `recall_pct: 0.0`, `declared: 13`, `found: 0`
- execution.toon `phase_6.steps` — `branch-cleanup` at index 15, `plan-marshall:plan-retrospective` at 16
- status.json — `branch-cleanup` outcome `"PR #1064 merged via queue, main pulled, worktree removed, branch gone"`
- `git show --name-only e82b466ee` — 8 files, all declared
