envelope_version=1
sender_type=plan
sender_id=exit-code-convention-stops-at-the-skill-boundary
epic=review-apparatus
kind=candidate-lesson
created=2026-09-06T19:31:41Z

# affected_files_recall is easier to pass the more the declaration under-records

component: plan-marshall:plan-retrospective
category: bug
confidence: high
source_plan: exit-code-convention-stops-at-the-skill-boundary
source_pr: 1423, 1429

## Context

`check-artifact-consistency` graded this run:

```toon
affected_files_recall,pass,Recall 78% meets threshold
  declared: 9
  found: 7
  recall_pct: 77.8
```

The realized footprint was **158 files**. The check passed on a declared set
covering under 6% of what the plan actually touched, and reported `passed: 5,
failed: 0`.

The `affected_files_exact_match` sub-check did notice something was wrong
(`references_only[56]`), but it is graded `info` and explicitly defers
("deferred to manifest aspect"). The manifest aspect it defers to then emitted
`findings[0]` — so the deferral terminates in nothing, and the aspect's headline
verdict is a clean pass.

## Root cause

Recall is `found / declared`. The denominator is the **claim**, not the ground
truth — so shrinking the claim *raises* the score. A plan that declares 9 files
and touches 158 scores better than one that declares all 158 and misses 3.

This inverts the detector: the metric improves as the coverage claim degrades,
which is the opposite of what a coverage check is for. It is the same shape as the
project's existing rule that a set-guarding detector must be
population-derived — here the population is available (the realized footprint is
resolved in the very same fragment, `footprint_resolved: true`) and simply is not
used as the denominator.

The two figures never appear side by side, so nothing in the emitted payload lets
a reader see that 78% was computed over 9 of 158.

## Proposed action

1. Publish the realized-footprint size next to the recall figure, always. `Recall
   78% (9 declared of 158 realized)` is self-refuting in a way that `Recall 78%`
   is not.
2. Add the inverse measure — declared-coverage, `declared / realized` — and grade
   against it too. Recall answers "did the plan do what it said"; the inverse
   answers "did the plan say what it did", and only the second catches this run.
3. Do not let `affected_files_exact_match` defer to an aspect that can emit zero
   findings for the same condition. Either the deferral target owns the finding or
   the deferring check keeps it; currently a 56-file discrepancy is reported by
   neither at above `info`.

## Evidence

- `fragment-artifact-consistency.toon` — `affected_files_recall … status: pass`,
  `declared: 9`, `found: 7`, `footprint_resolved: true`, `references_only[56]`
- `fragment-outline-vs-shipped.toon` — `footprint_path_count: 158`,
  `touched_but_unassessed: 158 of 158`
- `fragment-manifest-decisions.toon` — `findings[0]`, `summary.findings: 0`
  (the deferral target), while its own `diff.files_kept` reads 158
- `work/metrics.toon` — `files_modified: 9` (the same under-recorded value,
  propagated into every efficiency ratio)
- Related, already filed: `5a7fff`. This is the detector that failed to catch it.
