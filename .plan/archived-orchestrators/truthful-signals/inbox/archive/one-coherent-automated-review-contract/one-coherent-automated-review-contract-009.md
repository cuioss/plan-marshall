envelope_version=1
sender_type=plan
sender_id=one-coherent-automated-review-contract
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T05:04:51Z

component=plan-marshall:plan-retrospective
category=bug
bundle=plan-marshall

# Running the retrospective after branch-cleanup makes every footprint-derived aspect report a confident wrong answer

## Observation

In `one-coherent-automated-review-contract` (PLAN-92) the manifest orders
`plan-marshall:plan-retrospective` AFTER `branch-cleanup`. By the time the retrospective ran, the
worktree had been removed and the branch deleted, so the live footprint derivation
(`{base}...HEAD` union porcelain) had nothing to read. The footprint-derived aspects did not report
"unmeasurable" — they reported measurements:

- `check-artifact-consistency` → `affected_files_recall, fail, "Recall 0% below 70% threshold"`,
  with `declared: 59, found: 0`. Read literally this says the plan modified none of its declared
  files. The plan in fact modified 47 of them.
- `direct-gh-glab-usage` → `status: success`, `counts.total: 0`, `diff_leak: 0`. A clean bill of
  health for a diff surface that did not exist at read time.

Both are **vacuous**: a `fail` that means "could not measure" and a `pass` that means "nothing to
measure", each rendered in the same vocabulary a real result uses. The retrospective then compiles
them into a report a human reads as findings.

Recovering the real footprint was possible and cheap — `git diff --name-only {base}..{merge_commit}`
over the merged range returned the true 47 files, and re-running the manifest and routing aspects
against it produced meaningful output.

## Do this instead

- **Derive the footprint from the merged range when the worktree is absent.** The merge commit and
  base are both recoverable from `references.pr_number` / the plan's branch record long after
  cleanup. Add this as the documented fallback ahead of the legacy `references.modified_files` key.
- **A footprint-derived aspect that cannot resolve a footprint MUST emit `status: skipped` with an
  explicit reason token**, never a numeric result. `recall_pct: 0.0` and `counts.total: 0` are
  forbidden outputs when the input surface was unavailable — this is the same
  `transcript_too_large` vs `transcript_unavailable` discipline the chat-history aspect already
  specifies, applied to the footprint channel.
- Alternatively (or additionally) **order the retrospective before `branch-cleanup`** in the
  default finalize step list, so the worktree is still on disk.

## Recurrence context

Epic theme `truthful-signals`, and specifically the `vacuous guard` archetype: a check whose
predicate cannot fire still reports in the vocabulary of a check that ran. Note the asymmetry that
makes it dangerous — the same root cause produced a false RED in one aspect and a false GREEN in
another, so neither the alarm nor the silence can be trusted.
