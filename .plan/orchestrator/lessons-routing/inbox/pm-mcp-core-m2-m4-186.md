envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T07:34:19Z

# Candidate lesson: let sync-affected-files drop paths no longer declared by the outline

Source: plan-retrospective of plan verify-not-resolve. Proposed component: `plan-marshall:manage-references`. Category: bug. Confidence: medium.

## Context

Q-Gate finding c103cb was fixed by rewriting deliverable 8's relative `../plan-marshall-documentation/...` paths as absolute paths. The outline leaf then reported that `references.affected_files` held 37 entries, 4 of them the old relative paths beside the new absolute ones, and probably the same leftovers in `read_intent_files`. The refresh only adds paths and the workflow has no removal step, so the leaf left them. This is separate from the c103cb finding itself (relative paths breaking under a worktree): the issue here is that the refresh cannot shrink the list after any outline revision.

## Root cause

`sync-affected-files` merges the outline's declared set into the stored list but never subtracts paths the outline no longer declares.

## Proposed action

Make the sync replace the declared-derived portion of the list (or offer a `--prune` mode the outline workflow calls after a revision), and report the removed paths.

## Evidence

- aspect: chat-history-analysis — outline revision leaf: "The refresh step only adds paths and never removes them ... The workflow has no step for removing them, so I left them"
- aspect: llm-to-script-opportunities — prune candidate

Classification is left to the orchestrator.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `verify-not-resolve-021.md` from plan verify-not-resolve (PLAN-18, #43; Claude Code)
