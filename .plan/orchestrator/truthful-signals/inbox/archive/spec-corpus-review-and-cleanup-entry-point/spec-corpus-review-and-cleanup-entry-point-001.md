envelope_version=1
sender_type=plan
sender_id=spec-corpus-review-and-cleanup-entry-point
epic=truthful-signals
kind=candidate-lesson
created=2026-08-22T16:16:11Z

component=plan-marshall:plan-retrospective
category=bug
confidence=high
source_plan=spec-corpus-review-and-cleanup-entry-point
source_aspects=artifact_consistency,log_analysis,request_result_alignment,llm_to_script_opportunities

# Footprint resolver cannot see a squash landing, so every post-merge retrospective grades blind

## Context

This plan's retrospective ran after `branch-cleanup` had removed the worktree and after PR #1134 landed on main as squash commit `c0bbd2d8b`. The shared footprint resolver reported that all four of its tiers failed — no live worktree diff, no realized-footprint capture, no merge-commit, no legacy `references.modified_files` key — so `check-artifact-consistency` returned `inconclusive` for both `affected_files_recall` and `affected_files_exact_match`, and `analyze-logs` emitted `ARTIFACT_COVERAGE_UNMEASURABLE`.

The footprint was never actually lost. `git show --name-only c0bbd2d8b` returns the exact 16-file realized footprint, and supplying that list via `--diff-file` made both `check-manifest-consistency` and `check-routing-decisions` produce real verdicts (16 files kept, `branch_cleanup_changes` pass, prune predicates re-evaluated) instead of `indeterminate`.

## Root cause

The resolver's post-landing tier looks for a *merge commit*. This repository merges through a GitHub merge queue configured with `pr_merge_strategy: squash` (visible in this plan's own manifest `step_params.branch-cleanup`), so a landing produces a single-parent commit and that tier can never fire here. Every plan in this repository that reaches its retrospective after `branch-cleanup` therefore loses footprint-dependent grading — the tier is not merely unlucky, it is structurally dead for this repository's merge strategy.

## Proposed action

Add a squash-landing tier to the shared footprint resolver, ordered after the merge-commit tier:

1. Read the PR number from `status.metadata` (this plan carried it in `phase_steps["6-finalize"]["create-pr"].display_detail`, and `branch-cleanup` records the landing).
2. Resolve the landing SHA through the CI abstraction (`plan-marshall:tools-integration-ci:ci`), never `gh` directly.
3. Read the file list from that single-parent commit.

Until the tier exists, the honest reporting is already in place and should be preserved: `inconclusive` is correctly distinguished from a clean pass, and `ARTIFACT_COVERAGE_UNMEASURABLE` correctly refuses to present an un-run check as a passing one. The defect is the missing capability, not the labelling.

## Evidence

- aspect: artifact_consistency — `affected_files_recall,inconclusive,"Plan footprint could not be resolved from any tier ... recall is unmeasurable, not 0%"`; `footprint_resolved: false` against `declared: 15`
- aspect: log_analysis — `ARTIFACT_COVERAGE_UNMEASURABLE: ... so ARTIFACT coverage could not be graded (artifact_entries=26). This is an unmeasured check, not a clean one.`
- aspect: request_result_alignment — footprint recovered manually from `c0bbd2d8b` (16 files); all 9 deliverables then graded at 100% mutation-intent coverage, a verdict no automated tier could reach
- aspect: llm_to_script_opportunities — 3 separate consumers each independently reported the same unresolvable footprint in one retrospective run
- corroborating: the manifest compose decision log for this plan already recorded a footprint failure at the other end of the lifecycle — `pre_push_quality_gate_inactive — kept pre-push-quality-gate on an unknown build verdict: plan footprint unresolvable — worktree not yet materialised`
