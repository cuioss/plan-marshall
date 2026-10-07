envelope_version=1
sender_type=plan
sender_id=sweep-the-three-single-instance-defect-classes
epic=test-quality
kind=candidate-lesson
created=2026-09-14T03:21:44Z

component=plan-marshall:plan-retrospective
category=bug
confidence=high
source_plan=sweep-the-three-single-instance-defect-classes
source_aspects=manifest_decisions,artifact_consistency,outline_vs_shipped

# Anchor the realized footprint to the merge base, not to a post-merge HEAD

## Context

This retrospective runs at `order: 995`, after `default:branch-cleanup` (order lower) has already squash-merged the PR into `main` and removed the worktree. Every aspect that needs the plan's realized footprint therefore resolves it from a checkout where the plan's own changes are indistinguishable from `main`.

Three aspects produced three different footprints for one plan:

- `check-manifest-consistency --base-ref origin/main` reported `files_total: 0`, `diff_available: true` — it diffed a merged branch against its own merge target. It then emitted `branch_cleanup_without_changes`: "phase_6.steps includes branch-cleanup but the observed diff is empty — the footprint resolved to no changed path at all, so no implementation file changed." That finding is false; the plan changed 87 files.
- The shared footprint resolver returned 130 paths. Roughly 43 of them belong to sibling commits rebased under this branch — `automatic-review/**`, `phase-5-execute/SKILL.md`, `branch-cleanup*.md`, `tools-integration-ci/standards/**`, `workflow-integration-github/scripts/**`, `tools-script-executor/generate_executor.py`, `tools-file-ops/**` — and are not this plan's work.
- `references.affected_files` held 86 paths, which matches the merged commit's 87 almost exactly.

Ground truth is `git show --stat f21a0dc66`: 87 files changed, 2082 insertions, 132 deletions.

## Root cause

The footprint resolvers assume a live worktree on an unmerged branch. After branch-cleanup they are asked the same question in a state where the question has no answer: the diff against `origin/main` is empty because the branch *is* `origin/main`, and any wider base sweeps in whatever else was rebased under the branch. The order-995 placement guarantees this state, so it is systematic, not incidental.

## Proposed action

Record the merge base (or the pre-merge branch head) as a plan fact at the point branch-cleanup merges, and have the retrospective's footprint resolution read that anchor instead of re-deriving a base from the post-merge checkout. `status.metadata` already holds `worktree_sha` and `main_sha`, so the anchor may already be available and merely unread. Separately, `check-manifest-consistency` must not emit `branch_cleanup_without_changes` from an empty diff it cannot distinguish from an unresolvable one — an empty diff against a base that equals HEAD is a could-not-look, and the script's own `indeterminate` disposition is the right verdict for it.

## Evidence

- aspect: manifest_decisions — `diff.base: origin/main`, `files_total: 0`, and a false `branch_cleanup_without_changes` finding
- aspect: artifact_consistency — `references_only[119]`, dominated by paths belonging to sibling commits
- aspect: outline_vs_shipped — `footprint_path_count: 130`, `touched_but_unassessed: 130 of 130`
- ground truth: `git show --stat f21a0dc66` — 87 files changed
