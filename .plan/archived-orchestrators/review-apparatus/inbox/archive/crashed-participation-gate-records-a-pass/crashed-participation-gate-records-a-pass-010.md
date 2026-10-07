envelope_version=1
sender_type=plan
sender_id=crashed-participation-gate-records-a-pass
epic=review-apparatus
kind=candidate-lesson
created=2026-08-01T19:36:21Z

# Persist the landed footprint before branch-cleanup removes the worktree

component: plan-marshall:phase-6-finalize
category: bug
confidence: high
source: plan-retrospective (aspects: artifact-consistency, llm-to-script-opportunities)
suggested_epic: truthful-signals (a coverage check reports FAIL when it is actually unmeasurable)

## Context

`check-artifact-consistency` reported:

```
affected_files_recall,fail,Recall 0% below 70% threshold
details.affected_files_recall: declared 9, found 0, recall_pct 0.0
```

with all nine declared files listed as `missing`. The real recall is 9/9 = 100%: every declared file is in the landed merge commit `40bfba08c`.

## Root cause

The coverage contract says the footprint is "derived live from the plan's worktree (`{base}...HEAD` union porcelain) when one is on disk". In the manifest-composed finalize order, `branch-cleanup` (step 16) removes the worktree and `plan-marshall:plan-retrospective` (step 17) runs after it. So by the time the deterministic coverage check runs, its only input source is gone.

The failure is not that the data is missing — it is that the check reports `fail` / `recall 0%` for an **unmeasurable** state instead of `skipped` / `indeterminate`. A reader of the report cannot distinguish "the plan covered nothing" from "the measurement substrate was deleted". This is the same archetype as the routing-decisions false FAIL in the sibling message: an audit check that cannot tell absence-of-evidence from evidence-of-absence.

Three separate aspects needed the same list this run — `check-artifact-consistency`, `check-manifest-consistency`, and `check-routing-decisions` — and the retrospective had to hand-reconstruct it via `git diff --name-only 40bfba08c~1 40bfba08c` and feed it back through `--diff-file`.

## Proposed action

1. At `branch-cleanup`, after the merge lands, persist the landed footprint (merge-commit `--name-only` diff) to a plan-dir artifact, e.g. `work/landed-footprint.txt`. It is durable, survives worktree removal, and is the *authoritative* footprint (what actually shipped) rather than a worktree approximation.
2. Have `check-artifact-consistency` prefer that artifact, then the live worktree, then the legacy `references.modified_files`.
3. Independently of (1) and (2): when NO footprint source resolves, the check MUST emit `skipped` with an explicit unmeasurable reason — never `fail` with `recall 0%`. Fixing only the data source would leave the false-FAIL mode live for any future ordering change.

## Evidence

- aspect: artifact-consistency — `affected_files_recall,fail,Recall 0% below 70% threshold` with `found: 0`
- `git diff --name-only 40bfba08c~1 40bfba08c` returns 10 files including all 9 declared
- `execution.toon` phase_6.steps — `branch-cleanup` at index 15, `plan-marshall:plan-retrospective` at index 16
- `status.metadata.phase_steps["6-finalize"]["branch-cleanup"]` — "merged #1070 via queue, main pulled, branch + worktree removed"
