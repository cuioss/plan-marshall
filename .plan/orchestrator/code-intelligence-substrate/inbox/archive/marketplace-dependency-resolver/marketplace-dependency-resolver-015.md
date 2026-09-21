envelope_version=1
sender_type=plan
sender_id=marketplace-dependency-resolver
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-01T23:18:52Z

component=plan-marshall:plan-retrospective
category=bug
title=Stop reporting an unresolvable footprint as 0% coverage recall

# Stop reporting an unresolvable footprint as 0% coverage recall

## Context

`check-artifact-consistency` reported for this plan:

```
affected_files_recall,fail,Recall 0% below 70% threshold
  declared: 16
  found: 0
  recall_pct: 0.0
```

The plan's true write-target recall is **100%**. All 13 files the outline
declared with `intent=write-replace` or `intent=write-new` are present in the
landed squash commit `021305e26`.

A reader of the report sees the most severe possible coverage failure on a plan
with perfect coverage.

## Root cause

Two independent defects compound, one in the numerator and one in the
denominator.

**Numerator — empty footprint rendered as zero coverage.** The footprint is
derived live from the plan's worktree. `branch-cleanup` removed the worktree at
22:47 (with `--force`, after the initial removal timed out). The retrospective
runs *after* `branch-cleanup`, so the derivation returns an empty set every time
it runs on a merged plan. The aspect renders `found: 0` as `recall_pct: 0.0` with
status `fail`, rather than as *footprint unavailable*. A missing measurement is
reported as a measured zero.

**Denominator — intent is discarded.** `references.json` stores `affected_files`
as a flat path list. The outline stores `{path, intent}` pairs. Three of this
plan's 16 declared files carry `intent=read`:

- `…/tools-marketplace-inventory/scripts/_dep_detection.py`
- `…/tools-marketplace-inventory/scripts/_dep_index.py`
- `…/build-maven/scripts/extension.py`

The plan correctly only *read* them. The check counts them as expected
modifications, so a compliant plan is scored as having missed three files. Even
with a correct numerator the reported recall would be 13/16 = 81%, not 100%.

The same empty-footprint blindness affects `direct-gh-glab-usage`, which reported
`total: 0` with no indication of whether it scanned a diff and found nothing or
found no diff to scan.

## Proposed action

1. Add an explicit `footprint_unavailable` state. When the footprint cannot be
   derived, the aspect must emit that token and SKIP the recall check — never
   emit `recall_pct: 0.0` with `fail`.
2. Add a merge-commit fallback: when the worktree is gone, derive the footprint
   from the landed commit on the base branch (`git show --name-only {sha}`). The
   PR number is already in `phase_steps`, and the squash SHA is resolvable from
   it. This makes post-merge retrospectives measure the real footprint.
3. Filter the denominator by intent. Add a `manage-solution-outline write-targets`
   verb returning only `write-replace`/`write-new` paths, and have the check
   consume that instead of `references.affected_files`.
4. Apply the same `footprint_unavailable` treatment to `direct-gh-glab-usage`, so
   a zero there carries provenance.

## Evidence

- aspect: artifact_consistency — `recall 0%`, `found: 0`, `missing[10]`.
- aspect: request_result_alignment — 13/13 write targets present in `021305e26`;
  the 3 "missing" non-test files are all `intent=read`.
- `manage-solution-outline list-deliverables` — the `{path, intent}` pairs the
  flattened `references.json` discards.
- This retrospective had to reconstruct the footprint by hand via
  `git show --name-only 021305e26` before any coverage statement was possible.
