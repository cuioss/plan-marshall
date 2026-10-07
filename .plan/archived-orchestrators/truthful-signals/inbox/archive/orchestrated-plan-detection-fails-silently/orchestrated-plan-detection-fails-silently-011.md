envelope_version=1
sender_type=plan
sender_id=orchestrated-plan-detection-fails-silently
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T16:17:16Z

component=plan-marshall:plan-retrospective
category=bug
bundle=plan-marshall

# Artifact-consistency reports "Recall 0% — FAIL" when the worktree it measures was already removed, and its escape hatch defers to a check that does not exist

## What happened

`check-artifact-consistency` on PLAN-114 emitted:

```
affected_files_recall,fail,Recall 0% below 70% threshold
  declared: 6
  found: 0
  recall_pct: 0.0
```

The true recall is **5 of 6 (83%)**, comfortably above the 70% threshold. The check reported a hard failure because it derives the realized footprint **live from the plan's worktree** — and by the time the retrospective runs (finalize step 17 of 22), `branch-cleanup` (step 16) has already removed that worktree. The script measured an absent tree, found zero files, and reported zero as a measured value.

Deriving the footprint from the merge commit instead gives the correct 5 files immediately.

## Two distinct defects, same aspect

**Defect A — measuring an absent substrate as a zero.** `found: 0` is emitted with the same shape and confidence as a genuine `found: 0` on a plan that really changed nothing. The script has no "substrate unavailable" state, so "I could not measure" and "I measured nothing" are the same output. Every post-merge retrospective on a worktree-using plan gets a spurious `fail` here, which trains readers to discount the check — the classic path by which a real recall failure will one day be waved through.

**Defect B — a dead-letter deferral.** The sibling check emits:

```
affected_files_exact_match,info,Set mismatch — deferred to manifest aspect (see check-manifest-consistency)
  outline_only[6]: …
  forwarded_to_manifest: true
```

`check-manifest-consistency` performs **no outline-vs-footprint set comparison**. Its five checks are `manifest_version_recognized`, `docs_only_diff`, `early_terminate_diff`, `tests_only_diff`, `branch_cleanup_changes`. The forwarded finding is received by nobody.

This is not academic on this run: the `outline_only` set is exactly where the phantom declared path (see the companion `phase-3-outline` candidate-lesson) would have surfaced. The one check positioned to catch it downgraded itself to `info` and handed the finding to a check that does not implement the receiving end. `forwarded_to_manifest: true` is a claim about a contract that was never built.

## Corrective rule

1. **Persist the realized footprint before the worktree dies.** `branch-cleanup` should write the footprint (one path per line, from `{base}...HEAD`) into the plan directory. Every post-merge consumer then reads a recorded fact. `check-routing-decisions` needs the same input and has the same problem.
2. **Add a distinct `unavailable` outcome.** When the worktree path does not exist and no persisted footprint is present, the check must emit `status: skipped` with reason `footprint_substrate_absent` — never `fail` with `found: 0`. A measurement that could not be taken is not a measurement of zero.
3. **Close the deferral, or delete it.** Either implement the outline-vs-footprint set comparison in `check-manifest-consistency`, or have `affected_files_exact_match` own the finding at `warning` severity itself. A cross-aspect handoff must have a named receiver that actually performs the check — and `forwarded_to_manifest: true` must be computed from the receiver's capability, not hardcoded.

## Why it matters for truthful signals

Both halves are the epic's theme inside the epic's own auditing tool. Defect A is a **confident hard failure with a hidden caveat** ("…because I had nothing to measure"). Defect B is a **confident hand-off with a hidden caveat** ("…to a check that does not exist"). Together they mean the retrospective's declared-vs-achieved coverage arm reported a FAIL it should not have, while routing the one finding it should have escalated into a void.

## Recurrence signature

Sweep every retrospective aspect that reads the worktree for the same post-cleanup blindness, and sweep every `deferred to X` / `forwarded_to_X: true` emission in the codebase against X's actual check list. The second sweep must be population-derived from the receiver's implemented checks, not from reading the deferral prose.
