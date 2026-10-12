envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-11T07:42:11Z

# Candidate lesson: make sibling-repo deliverables first-class in footprint, worktree and PR linking

Source: plan-retrospective of plan-04-service-unit (aspects artifact-consistency, manifest-decisions, request-result-alignment, chat-history). Not covered by the 10 lessons-capture messages.

## Context

Deliverable 4 declared 6 files in the sibling checkout `../plan-marshall-documentation` and shipped them through documentation PR #26. Three things around that deliverable ran outside the framework:

- The realized footprint covers only this repository. All 6 sibling paths showed up as `outline_only`, so artifact-consistency reported 73% recall and manifest rule M6 (`declared_vs_realized_set`) failed for a deliverable that was in fact fulfilled.
- The executor created the documentation worktree by hand under the plan worktree's `.plan/temp/plan-marshall-documentation`, because the docs checkout was on another branch. Its cleanup ("`git worktree remove` once PR #26 is merged") was left as a note. plan-06-store-substrate uses the same nested layout.
- The deliverable required the docs PR to name the code PR, but the code PR only exists at finalize. The executor named the branch instead, and the PR number had to be added by hand later.

## Root cause

Phases 3 to 6 assume a single repository. A deliverable whose files live in a sibling checkout has no worktree provisioning, no footprint source, no PR cross-link step and no cleanup.

## Proposed action

- The footprint resolver and check-artifact-consistency classify declared paths outside the repository root as `cross_repo` and leave them out of recall and M6, reporting them separately, for example by the linked PR's file list.
- A sanctioned way to provision and remove a sibling-repo worktree for a plan, recorded in status metadata so that worktree removal or archive-plan cleans it up.
- A finalize step, or a create-pr follow-up, that writes the code PR number into the linked sibling PR body.

## Evidence

- artifact-consistency: `affected_files_recall` 72.7%, missing = the 6 `../plan-marshall-documentation/...` paths
- manifest-decisions: M6 fail, `outline_only_count: 6`, `references_only_count: 0`
- chat-history: TASK-7 report ("separate worktree at .../worktrees/plan-04-service-unit/.plan/temp/plan-marshall-documentation"; "Once the code PR exists, its number should be added to PR #26")

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `plan-04-service-unit-011.md` from plan plan-04-service-unit (PLAN-04, #25)
