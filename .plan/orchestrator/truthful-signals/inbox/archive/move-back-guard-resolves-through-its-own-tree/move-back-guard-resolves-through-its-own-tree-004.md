envelope_version=1
sender_type=plan
sender_id=move-back-guard-resolves-through-its-own-tree
epic=truthful-signals
kind=candidate-lesson
created=2026-08-27T18:48:52Z

component=plan-marshall:manage-tasks
category=bug
confidence=high
source_plan=move-back-guard-resolves-through-its-own-tree
source_pr=1361

# A pending-task TOON schema rejection can remove shipped work from the task ledger

## Context

At the end of phase-5, TASK-13 surfaced a real residual and correctly declined it as outside its four declared steps: `workflow-integration-git/SKILL.md`'s worktree-remove error table documented only `worktree_remove_failed`, omitting `plan_dir_not_moved_back` (pre-existing) plus `cwd_inside_removal_target` and `worktree_remove_timed_out` — both **created by this plan**. Shipping without it would have left the caller-facing skill doc under-reporting the very verb the plan changed.

An attempt to record this as TASK-14 was made and **failed three times on the pending-task TOON schema**. The attempt was abandoned rather than continuing to guess at the schema, and the operator authorised folding the edit in with no task record.

Consequences that survived into merged main:

- Phase-5 task metrics read **13/13** while the real unit count for that phase was **14**.
- The only audit trail for that unit of work is decision entry `50d3fe` plus the commit itself.
- A stray unconsumed staging file remains at `work/pending-tasks/default.toon`.
- Every downstream figure derived from the task count under-reports the run.

## Root cause

The pending-task TOON staging path rejects malformed input without telling the caller what shape it wanted, so a caller with a legitimate task to record has no convergent repair loop — each retry is another guess. When the ledger is harder to write than the code is, the ledger loses, and the loss is silent: nothing downstream reports "this plan shipped work with no task record".

## Proposed action

1. Make the pending-task schema rejection self-describing: return the offending field, the expected shape, and a minimal accepted example, so a third attempt is informed rather than another guess.
2. Provide a minimal single-task add path that does not route through the batch TOON staging file at all, for exactly this late-arriving-single-task case.
3. Have the phase-5 completion check compare the task count against the commit count for the phase and surface a divergence, so shipped-work-without-a-task-record is a reported condition rather than an invisible one.
4. Clean up the staging file on abandonment, or report it — a leftover `work/pending-tasks/default.toon` is state nobody owns.

## Evidence

- decision.log 50d3fe (2026-08-27T12:03:10Z) — "A task-14 record was attempted and abandoned after three pending-task TOON schema rejections; operator chose to fold the edit in without a task record, so the audit trail is this entry plus the commit, and phase-5 task metrics show 13/13 while the plan's real footprint is 14 units. affected_files updated 15 -> 16. A stray unconsumed staging file remains at work/pending-tasks/default.toon."
- aspect: chat_history_analysis — operator gate answer "Fold it in, skip the task record"
- aspect: request_result_alignment — `scope_creep[]` entry for `workflow-integration-git/SKILL.md`
