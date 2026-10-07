envelope_version=1
sender_type=plan
sender_id=fold-pm-code-intelligence-into-core
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-25T21:12:49Z

# Footprint resolver merge-commit tier cannot see a squash landing

## Context

The shared footprint resolver declares a merge-commit fallback tier. For this plan that tier reported nothing even though the plan had merged: PR #1348 landed on main as `9aaf22d8f`. Inspecting that commit shows a single parent (`a2be2691c`) — it is a squash, not a merge.

## Root cause

The manifest records `pr_merge_strategy: squash` for `branch-cleanup`, and this repository merges through a merge queue with squash. A squash landing produces a one-parent commit, so a tier that looks for a merge commit (two parents) can never match. The tier is not merely unreliable here; it is structurally dead for every plan this project lands, which is why the resolver reports "no merge-commit" on a plan that demonstrably merged.

## Proposed action

Add a squash-aware tier to the shared footprint resolver: read the PR number already recorded in `status.metadata.phase_steps['6-finalize']['create-pr'].facts.pr_number` (`1348` here) and locate the base-branch commit whose subject ends `(#{pr_number})`, then take its `--name-only` diff. The datum needed is already persisted by `create-pr`, so no new capture is required.

## Evidence

- aspect: artifact_consistency — "no merge-commit" reported for a plan whose PR had merged
- `git show --numstat --pretty=format:%H%n%P 9aaf22d8f` returns exactly one parent line
- manifest `phase_6.step_params.branch-cleanup.pr_merge_strategy: squash`
- `status.metadata.phase_steps['6-finalize']['create-pr'].facts.pr_number: "1348"` — the key the tier needs is already stored
