envelope_version=1
sender_type=plan
sender_id=daemon-baseline-interpreter-is-unregistrable
epic=truthful-signals
kind=candidate-lesson
created=2026-08-08T21:09:23Z

component=plan-marshall:plan-retrospective
category=improvement
confidence=high
source_aspects=artifact-consistency,request-result-alignment

# Resolve the post-merge footprint from the merge commit instead of reporting inconclusive

## Context

`check-artifact-consistency` resolves the plan's realized footprint from the live worktree diff, falling back to the legacy `references.modified_files` key for older archived plans. In `phase_6.steps`, `branch-cleanup` (which removes the worktree) runs BEFORE `plan-marshall:plan-retrospective`. So on every plan that reaches the retrospective normally, both sources are gone.

Result on this run: `affected_files_recall` and `affected_files_exact_match` both returned `inconclusive` — "Plan footprint could not be resolved". Two of six coverage checks, and specifically the two that constitute the declared-vs-achieved coverage measurement the aspect exists to provide.

The data was not actually unavailable. `status.metadata.phase_steps['6-finalize']['create-pr'].display_detail` carries `#1122`, and two git calls against the squash commit `263f216d9` recovered the exact 9-file footprint. Doing that by hand yielded a real result the script reported as unmeasurable: 9 declared vs 9 shipped with an intersection of 8 — recall 0.89, precision 0.89, one declared file untouched (`_build_execute_factory.py`) and one undeclared file touched (`test_acceptance_idempotent_submit.py`).

## Root cause

The footprint resolver's sources are both tied to pre-merge state, while the step that consumes them is ordered after the merge. The `inconclusive` verdict is honest about its own ignorance — which is the right degrade — but the ignorance is avoidable.

## Proposed action

Add a third footprint source, tried after the live worktree and before the legacy key: resolve the merge/squash commit from the recorded PR number and read its name-only diff. This restores the coverage measurement for every post-merge retrospective without weakening the honest-degrade behaviour when no source is available.

Guard against the trap this analysis hit first: diffing `status.metadata.main_sha...HEAD` is NOT equivalent — on this plan that range returned 73 files because it swept in 17 upstream commits absorbed by the rebase. Only the squash commit isolates the plan's own footprint.

## Evidence

- `check-artifact-consistency` — `affected_files_recall,inconclusive` and `affected_files_exact_match,inconclusive`, `footprint_resolved: false`
- `execution.toon` `phase_6.steps` orders `branch-cleanup` before `plan-marshall:plan-retrospective`
- `status.metadata.phase_steps['6-finalize']['branch-cleanup'].display_detail` — "merged via queue, main pulled, branch+worktree removed"
- `git show --name-only 263f216d9` returns exactly 9 files; the `main_sha...HEAD` range returns 73
