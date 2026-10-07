envelope_version=1
sender_type=plan
sender_id=runtime-edge-paths-crash-or-silently-lose-data
epic=truthful-signals
kind=candidate-lesson
created=2026-08-09T20:24:06Z

component=plan-marshall:plan-retrospective
category=bug
confidence=high
source_plan=runtime-edge-paths-crash-or-silently-lose-data
source_aspects=artifact_consistency,request_result_alignment,llm_to_script_opportunities

# Recover the plan footprint from the landing commit when the worktree is gone

## Context

`check-artifact-consistency` returned `inconclusive` on both of its coverage checks —
`affected_files_recall` and `affected_files_exact_match` — with the message "Plan footprint
could not be resolved (no live worktree diff and no modified_files key)". Those two checks are
the aspect's headline purpose: they are the deterministic declared-vs-achieved coverage
comparison that the thoroughness contract grades to the floor.

The footprint was not actually unavailable. The plan landed as squashed commit `ff4462148`
(PR #1132), and `git diff-tree --no-commit-id --name-only -r ff4462148` returns all 15 files.
Comparing that against the outline's declared `Affected files:` across all five deliverables
gives recall 15/15, precision 15/15, exact set match — a perfect result the aspect declined to
report.

## Root cause

In the default finalize manifest, `branch-cleanup` (step 13) removes the worktree before
`plan-marshall:plan-retrospective` (step 17) runs. The aspect's footprint resolution has two
tiers — live worktree diff, then the legacy `references.modified_files` key — and the ledger
that populated the second tier has been removed. So for every plan that runs branch-cleanup
before the retrospective, which is the default order, both tiers miss by construction.

## Proposed action

Add a third resolution tier to `check-artifact-consistency`: when the worktree is absent and
`references.modified_files` is absent, resolve the landing commit and derive the footprint from
it. The inputs are already in plan state — `status.metadata.phase_steps["6-finalize"]["create-pr"]`
carries the PR number and `branch-cleanup` carries `merge_mechanism` and its merge facts.
Report which tier answered, so a footprint derived post-merge is distinguishable from one read
off a live worktree, and keep `inconclusive` for the genuine no-tier case.

## Evidence

- aspect: artifact_consistency — `affected_files_recall,inconclusive,"Plan footprint could not be resolved ... recall is unmeasurable, not 0%"`, `details.footprint_resolved: false`, `declared: 15`
- aspect: request_result_alignment — recall 1.00, precision 1.00, exact_match true, recovered from `git diff-tree ff4462148`
- aspect: llm_to_script_opportunities — this recovery was performed by LLM improvisation during the retrospective and is fully deterministic

## Note on what went right

The aspect reported `inconclusive`, not `0%`. That is the correct posture and is exactly what
the truthful-signals epic asks for — the defect is the missing tier, not the honesty of the
report. Two sibling aspects in the same skill behave differently on the identical condition:
`check-manifest-consistency` reports `skip — no diff data available` (also correct), while
`direct-gh-glab-usage` reports a bare zero (filed separately).
