envelope_version=1
sender_type=plan
sender_id=lessons-corpus-is-written-and-never-read
epic=truthful-signals
kind=candidate-lesson
created=2026-07-28T19:24:54Z

component=plan-marshall:plan-retrospective
category=bug
created=2026-07-28

# `affected_files_recall` reports a confident 0% computed from an empty footprint source

`check-artifact-consistency` compares the outline's declared `Affected files:`
against the plan's realized footprint. It derives that footprint **live from the
plan's worktree**. On this plan's own retrospective the worktree had already been
removed by `branch-cleanup` (the normal, correct finalize ordering), so the
footprint source returned an empty set.

The check did not report "footprint source unavailable". It computed
`recall = 0 / 17`, emitted `affected_files_recall,fail,"Recall 0% below 70%
threshold"`, and listed all 17 declared paths under `missing[]` — a fully-formed,
confident failure finding.

**Ground truth, established first-party this run**: the merge commit `010ea4615`
touched 12 files, and **all 10** paths in `references.affected_files` are among
them. Real recall is 100%, real precision 83% (two undeclared files: a
cross-reference sweep companion and an extracted test helper). The reported
finding was not merely imprecise — it inverted the result.

## Root cause

An absent evidence source and an empty evidence source are the same value
(`set()`) to the recall computation. Nothing distinguishes "I looked and found
nothing" from "I could not look".

## Solution

1. Make the footprint resolver return an explicit source-availability signal.
   When the worktree is gone, fall back to the base-branch merge commit
   (`git diff-tree --no-commit-id --name-only -r {merge_sha}`), which is
   available for every landed plan and was the source used to establish ground
   truth here.
2. When no source resolves at all, the check MUST emit `status: skipped` with a
   `footprint_source_unavailable` reason — never a numeric recall.
3. The same resolver is needed by `check-routing-decisions` and
   `check-manifest-consistency`, both of which take a `--diff-file` that had to be
   hand-built this run. One shared resolver fixes three call sites.

## Impact

Every retrospective that runs AFTER `branch-cleanup` — which is the manifest's
own step order, so this is the default path, not an edge case — receives a
fabricated coverage failure for its declared-vs-achieved comparison. This is the
deterministic half of the thoroughness dial; a retrospective reader who trusts it
concludes the plan shipped none of what it declared.
