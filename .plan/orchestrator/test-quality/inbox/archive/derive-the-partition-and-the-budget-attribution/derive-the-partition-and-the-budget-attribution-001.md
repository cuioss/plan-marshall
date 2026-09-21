envelope_version=1
sender_type=plan
sender_id=derive-the-partition-and-the-budget-attribution
epic=test-quality
kind=candidate-lesson
created=2026-08-25T08:57:31Z

component=plan-marshall:phase-6-finalize
category=bug
confidence=high
source_plan=derive-the-partition-and-the-budget-attribution

# Capture the realized footprint at branch-cleanup before the worktree is removed

## Context

Five independent consumers asked for this plan's realized footprint during its own run and post-merge retrospective, and none could answer:

- `check-artifact-consistency` returned `inconclusive` on BOTH `affected_files_recall` and `affected_files_exact_match`, with `footprint_resolved: false` — "no live worktree diff, no realized-footprint capture, no merge-commit, no modified_files key".
- `analyze-logs` emitted `ARTIFACT_COVERAGE_UNMEASURABLE`, disabling the `[ARTIFACT]`-emission floor.
- `manage-execution-manifest compose` recorded decision `4ffcc8` at plan time: "kept pre-push-quality-gate on an unknown build verdict: plan footprint unresolvable — no materialized worktree carries evidence of what this plan changed".
- `check-routing-decisions` had to be handed a `--diff-file` this retrospective built by hand.
- The metrics denominator `files_modified` fell back to the stale declared `references.affected_files` count (10) against a realized 14.

The footprint is recoverable — `git show --name-only --format= 00b92fca` yields all 14 files in one call — but no tier of the shared resolver looks there.

## Root cause

Every tier of the shared footprint resolver depends on state that `branch-cleanup` destroys before the retrospective runs: the worktree is removed, the branch is deleted, and the merge-commit tier does not match how this repository actually lands PRs (a squash through a merge queue, whose commit has no second parent). `references.modified_files` — the legacy key — is never written; only `affected_files`, the *declared* set, exists.

## Proposed action

Persist the realized footprint at `branch-cleanup`, BEFORE the worktree is removed, at the plan-relative path the shared resolver already probes for its realized-footprint capture tier. One path per line, from the same `{base}...HEAD` diff the step already has in hand.

Secondary, and independently valuable because it repairs already-archived plans that no forward-looking capture can reach: add the squash-merge commit as an explicit resolver tier, derived from the merge sha the plan already records.

## Evidence

- aspect: artifact_consistency — `footprint_resolved: false`; 2 of 6 checks `inconclusive`, 0 failed
- aspect: log_analysis — "ARTIFACT_COVERAGE_UNMEASURABLE: ... This is an unmeasured check, not a clean one."
- aspect: manifest_decisions — decision `4ffcc8`, recorded during 4-plan, long before merge
- aspect: routing_decisions — ran only because `--diff-file work/footprint.txt` was hand-built from the squash-merge commit
- aspect: llm_to_script_opportunities — candidate 1, repetition_count 4, complexity low
