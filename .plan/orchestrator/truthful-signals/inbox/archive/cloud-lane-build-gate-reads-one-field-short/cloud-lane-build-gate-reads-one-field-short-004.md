envelope_version=1
sender_type=plan
sender_id=cloud-lane-build-gate-reads-one-field-short
epic=truthful-signals
kind=candidate-lesson
created=2026-08-23T22:09:09Z

component=plan-marshall:plan-retrospective
category=bug
confidence=high
source_plan=cloud-lane-build-gate-reads-one-field-short
source_aspects=artifact_consistency,log_analysis,llm_to_script_opportunities

# Footprint resolver has no tier that survives a squash-merge, degrading 3 aspects

## Context

Running the retrospective after merge and worktree removal, all four footprint-resolver tiers
missed, and three deterministic aspects degraded:

- `check-artifact-consistency`: `affected_files_recall` and `affected_files_exact_match` both
  `inconclusive` — "no live worktree diff, no realized-footprint capture, no merge-commit, no
  modified_files key"
- `analyze-logs`: emitted `ARTIFACT_COVERAGE_UNMEASURABLE`
- `check-routing-decisions` / `check-manifest-consistency`: would have had no footprint to test
  the prune predicates against

The footprint was in fact trivially available: `git show --name-only 77c9dc70a` returns the
3 files. Supplying it by hand via `--diff-file` made both conditional aspects produce real
verdicts.

## Root cause

The merge-commit tier assumes the landing produces a merge commit. This repository merges through
a **merge queue with squash**, so the landed commit `77c9dc70a` has exactly ONE parent
(`2cd1a19c8`). The merge-commit tier can therefore never fire here — not "rarely", never. Combined
with worktree removal at `branch-cleanup` (which runs before the retrospective at order 995), the
resolver is guaranteed to be empty-handed for every merged plan in this repository.

The aspects degrade honestly (`inconclusive`, not a false clean), which is correct behaviour and
worth preserving. The defect is that the degradation is universal rather than exceptional.

## Proposed action

Add a landed-commit tier to the shared footprint resolver: when no worktree and no merge commit
exist, resolve the recorded PR number (`status.metadata.phase_steps["6-finalize"]["create-pr"].display_detail`
carries `#1336`) or the `pr_title` to its squashed commit on the base branch and use
`git show --name-only`. Alternatively, have `branch-cleanup` persist the realized-footprint
capture before it removes the worktree — that tier already exists in the resolver and is simply
never populated.

## Evidence

- `git log --format="%h %p" 77c9dc70a` -> single parent `2cd1a19c8`
- aspect: artifact_consistency — 2 checks `inconclusive`, `footprint_resolved: false`
- aspect: log_analysis — `ARTIFACT_COVERAGE_UNMEASURABLE` warning
- supplying `--diff-file work/footprint.txt` by hand produced `files_kept: 3` and real verdicts
  from both conditional aspects
