envelope_version=1
sender_type=plan
sender_id=config-seeding-effort-presets-steward-upgrade
epic=truthful-signals
kind=candidate-lesson
created=2026-08-26T14:41:24Z

component=plan-marshall:plan-retrospective
category=bug
source_plan=config-seeding-effort-presets-steward-upgrade
confidence=high

# Footprint resolver has no squash-commit tier, so a squash-merging repo is uncoverable post-cleanup

## Context

The artifact-consistency aspect returned:

> `affected_files_exact_match, inconclusive, "Plan footprint could not be resolved from any tier (no live worktree diff, no realized-footprint capture, no merge-commit, no modified_files key) — the comparison substantiates no verdict"`

The log-analysis aspect returned the matching `ARTIFACT_COVERAGE_UNMEASURABLE` warning for the same reason. Both the manifest cross-check and the routing-decision check needed a `--diff-file` that no tier could produce.

The footprint was in fact trivially available. PR #1351 landed as squash commit `b4e8a2364` with single parent `dad45f1bf`; `git diff --name-only dad45f1bf b4e8a2364` yields the exact 62-file footprint, and the retrospective derived it by hand to unblock three aspects.

This is not a one-off. The four tiers are: live worktree diff, realized-footprint capture, merge commit, `references.modified_files`. In this repository:

- the worktree is removed by `branch-cleanup`, which runs **before** the retrospective in the standing finalize order;
- every PR lands as a **squash** merge (`branch-cleanup` param `pr_merge_strategy: squash`; the last 25 commits on `main` are all linear `subject (#NNNN)` squashes), so there is never a merge commit;
- `references.modified_files` was retired.

So for every plan in this repository, all four tiers are guaranteed to miss by the time the retrospective runs. The declared-vs-achieved coverage comparison — the deterministic half of the thoroughness dial — is structurally unavailable, and reports `inconclusive` every time rather than reporting that it cannot ever run here.

## Root cause

The tier chain enumerates the ways a footprint *used to* be reachable and never gained a tier for the way this repository actually lands work. `inconclusive` is the honest verdict for a single read, but a verdict that is structurally guaranteed reads as an occasional gap rather than as a permanently dead check.

## Proposed action

1. Add a **squash-commit tier**: find the commit on the base branch whose subject ends `(#{pr_number})` — `pr_number` is already recorded in `status.metadata.phase_steps["6-finalize"]["create-pr"].facts.pr_number` — and diff it against its single parent.
2. Alternatively (or additionally) have `branch-cleanup` call `manage-references capture-footprint` **before** it removes the worktree, so the realized-footprint tier is populated exactly once, deterministically, at the last moment the worktree exists.
3. When every tier misses for a structural reason, say so — distinguish "no evidence this time" from "no tier can apply in this repository", per ADR-019's separation of unevaluated from evaluated-and-clean.

## Evidence

- aspect: `artifact-consistency` — `affected_files_exact_match: inconclusive`, `manifest_present: true`, `forwarded_to_manifest: false`.
- aspect: `log_analysis` finding `ARTIFACT_COVERAGE_UNMEASURABLE`.
- `git log --format="%h %p %s"` over the last 25 commits on `main`: every entry has one parent and a `(#NNNN)` subject.
- `execution.toon` → `phase_6.step_params.branch-cleanup.pr_merge_strategy: squash`.
- The hand derivation this retrospective performed: `git diff --name-only dad45f1bf b4e8a2364` → 62 files, which then unblocked `check-manifest-consistency` (61 files kept, 1 filtered) and `check-routing-decisions` (`footprint_source: diff_file`).
