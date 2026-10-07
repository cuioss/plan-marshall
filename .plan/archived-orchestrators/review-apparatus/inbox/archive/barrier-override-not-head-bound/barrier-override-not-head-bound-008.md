envelope_version=1
sender_type=plan
sender_id=barrier-override-not-head-bound
epic=review-apparatus
kind=candidate-lesson
created=2026-08-02T13:17:14Z

# Derive the footprint from the merge commit when the plan worktree is gone

component: plan-marshall:plan-retrospective
category: bug
confidence: high

## Context

`check-artifact-consistency` derives the plan's realized footprint live from the plan worktree
(`{base}...HEAD` union porcelain). By the time `plan-marshall:plan-retrospective` runs it is manifest
step 17, and `branch-cleanup` at step 16 has already removed that worktree. The aspect therefore found
zero files and reported `affected_files_recall: fail — Recall 0% below 70% threshold`, listing all nine
declared files as `missing`.

The true recall was 100%. The merged squash commit `967ba03f5` contains exactly the nine files
`references.json` declared — perfect precision and perfect recall, zero scope creep.

## Root cause

The aspect's evidence source (the worktree) is destroyed by an earlier step in the same phase. The
fallback documented in SKILL.md (`references.modified_files`) is legacy-only and was removed from live
plans, so there is no surviving source. The failure is silent in the sense that matters: it produces a
confident, specific, wrong FAIL rather than an "unknown".

## Proposed action

Give the footprint-derived aspects a shared post-cleanup resolver: when the plan worktree is absent,
derive the footprint from the merged commit (`git show --name-only --format= {merge_sha}`), resolving
`merge_sha` from the PR recorded in `phase_steps["6-finalize"]["create-pr"]`. When neither the worktree
nor a merge commit is resolvable, emit `status: skipped` with an explicit reason token — never a 0%
recall FAIL. The same resolver serves `check-manifest-consistency` and `check-routing-decisions`, both of
which needed the identical file list in this run and neither of which can derive it today.

## Evidence

- aspect: artifact_consistency — `affected_files_recall,fail,Recall 0% below 70% threshold`, `found: 0`, all 9 files listed under `missing`
- aspect: request_result_alignment — realized footprint from `967ba03f5` is exactly the 9 declared files; `precision_pct: 100.0`, `recall_pct: 100.0`
- aspect: llm_to_script_opportunities — hand-derived footprint was needed 3 separate times in this retrospective run
- `git worktree list` confirms `.plan/local/worktrees/barrier-override-not-head-bound` no longer exists
