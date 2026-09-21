envelope_version=1
sender_type=plan
sender_id=finalize-step-contract-guard-residue
epic=truthful-signals
kind=candidate-lesson
created=2026-08-24T10:23:15Z

component=plan-marshall:plan-retrospective
category=improvement
confidence=high
source_plan=finalize-step-contract-guard-residue

# Add a post-merge tier to the footprint resolver keyed on the recorded PR number

## Context

The shared footprint resolver has four tiers: live worktree diff, persisted realized-footprint capture, merge-commit fallback, and the legacy `references.modified_files` key. On this plan **all four returned unresolvable**, because by retrospective time the worktree had been removed at `branch-cleanup` and the PR had been **squash**-merged — and a squash-merge commit has a single parent, so the merge-commit tier finds no merge to diff.

The downstream degradation is wide:

- `check-artifact-consistency` graded both `affected_files_recall` and `affected_files_exact_match` `inconclusive` — declared-vs-achieved coverage, the deterministic half of the thoroughness dial, was simply not measured.
- `analyze-logs` emitted `ARTIFACT_COVERAGE_UNMEASURABLE`, disabling the `[ARTIFACT]` emission floor.
- `check-routing-decisions` and `check-manifest-consistency` needed a footprint fed in by hand.
- The same condition had already fired at **plan** time: `manage-execution-manifest compose` logged `pre_push_quality_gate_inactive — kept pre-push-quality-gate on an unknown build verdict: plan footprint unresolvable` twice.

Every one of these components failed safe and said so plainly, which is the system working. But the answer was one deterministic call away the whole time.

## Root cause

No tier consults what the plan already recorded about its own landing. `status.metadata.phase_steps['create-pr'].facts.pr_number` holds `1339`, and `branch-cleanup` recorded `merge_mechanism: merge_queue` / `merge_state: merged`. From the PR number the squash commit is discoverable, and `git show --pretty=format: --name-only <sha>` yields the 26-file footprint — which is exactly how this retrospective obtained it by hand.

## Proposed action

Add a fifth resolver tier, ordered after the merge-commit fallback and before the legacy key: read the recorded `pr_number` (and the branch-cleanup merge facts) from `status.metadata`, resolve the squash-merge commit, and take `git show --name-only`. Have the resolver publish which tier answered, so every consumer can report its footprint provenance rather than only its verdict.

Note that the existing merge-commit tier is specifically defeated by squash merges, which are this project's configured strategy (`pr_merge_strategy: squash` in the plan's own manifest) — so the gap is the default path here, not an edge case.

## Evidence

- aspect: artifact_consistency — both coverage checks `inconclusive`, `footprint_resolved: false`, `declared: 22`
- aspect: log_analysis — `ARTIFACT_COVERAGE_UNMEASURABLE` warning
- aspect: manifest_decisions — `pre_push_quality_gate_inactive` logged twice at plan time for the same reason
- status.json — `phase_steps['create-pr'].facts.pr_number: 1339`; `branch-cleanup.facts.merge_mechanism: merge_queue`
- manifest — `branch-cleanup.pr_merge_strategy: squash`, so the single-parent commit shape is the configured norm
