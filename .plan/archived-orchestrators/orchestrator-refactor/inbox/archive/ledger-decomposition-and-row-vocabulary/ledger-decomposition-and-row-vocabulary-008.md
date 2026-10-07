envelope_version=1
sender_type=plan
sender_id=ledger-decomposition-and-row-vocabulary
epic=orchestrator-refactor
kind=candidate-lesson
created=2026-09-24T09:05:22Z

# Carry a deliverable's declared verification command into its task

component: plan-marshall:phase-4-plan
category: bug

## Context

In ledger-decomposition-and-row-vocabulary, deliverables 1 and 2 (documentation_only) each declared a verification command: a plugin-doctor `quality-gate --paths ... --marketplace-root {worktree_path}/marketplace` call. But TASK-001 has `verification.commands[0]` and carries only the criteria text. At execute time, work.log logged "TASK-1 missing verification — falling back to architecture resolve" (and the same for TASK-2). So the declared doc-scoped gate was replaced by a module-level resolve.

## Root cause

Phase-4 task creation dropped the declared command on the way from the outline into the task, possibly because it is backtick-wrapped or contains the `{worktree_path}` placeholder. Nothing flags a deliverable that declares a command whose task has zero commands.

## Proposed action

Propagate the declared command verbatim, substituting `{worktree_path}` at execute time. Add a phase-4 invariant (or q-gate check) that fails when a deliverable's `verification.command` is non-empty and its task's `verification.commands` is empty.

## Evidence

- aspect: logging_gap_analysis — work.log 17:03:09 and 17:21:15 `[VERIFY] ... missing verification — falling back to architecture resolve`
- aspect: artifact_consistency — deliverables 1-2 declare the command (list-deliverables `verification.command`), TASK-001 `verification.commands[0]`
