envelope_version=1
sender_type=plan
sender_id=required-reviewer-returns-empty-list
epic=review-apparatus
kind=candidate-lesson
created=2026-09-05T16:33:37Z

component=plan-marshall:phase-5-execute
category=improvement
created=2026-09-05
bundle=plan-marshall

# Execute yielded once per task: 4 of 5 dispatches ended voluntary_checkpoint

## Context

`5-execute` completed 4 tasks and recorded 5 dispatch-boundary rows:

| termination_cause | rows | tokens |
|---|---|---|
| voluntary_checkpoint | 4 | 286,909 / 255,553 / 310,402 / 175,755 |
| clean_exit_queue_empty | 1 | 0 |

Every one of the four working dispatches ended by handing control back to the orchestrator,
and a fifth dispatch was then needed only to observe that the queue was empty. The
`DISPATCH_TERMINATION_CAUSE` rule's threshold is 50%; the observed share is 80%, and none
of it is absorbed by the two sanctioned exclusions — `budget_yield` was 0 (so the
plan-time bin-packer produced no envelope boundary that would explain a yield) and
`returned_with_findings` was 0 in this phase.

## Root cause

Not established. The dispatch ledger records the termination cause but not the reason the
agent chose to check point, and the reduced session transcript carries no narration of it.
Two candidate explanations the evidence does not separate:

- The agent treated one task as one dispatch by default, yielding on completion rather than
  draining the remaining queue — the agent-initiated-re-dispatch mode lesson
  `2026-05-08-14-001` exists to detect.
- Each task's verification tier forced a hand-off (TASK-001 declares
  `bash_timeout_seconds: 360`, and deliverable 2's verification command is explicitly
  documented as `execution_tier: orchestrator`, "run by the orchestrator, never from inside
  a per-task dispatch").

The second explanation is plausible enough that this is filed as `improvement` at medium
confidence rather than as a defect: an orchestrator-tier verification command legitimately
requires a return to the orchestrator, and if that is what happened then the 80% is
correct behaviour that the threshold currently reads as a failure mode.

## Proposed action

1. Determine which of the two causes applies — the dispatch ledger has the termination
   cause but not the motive, so the discriminator has to come from the workflow rather than
   from the retrospective.
2. If orchestrator-tier verification hand-offs are the cause, they deserve their own
   termination cause (as `budget_yield` and `returned_with_findings` already have), so a
   legitimate tier hand-off stops counting toward the agent-initiated-re-dispatch
   threshold. Both existing exclusions were added for exactly this reason, from opposite
   directions.
3. If the agent simply yielded per task, that is the failure mode the threshold was built
   for and the remedy is queue-draining, not a new exclusion.

## Evidence

- aspect: logging_gap_analysis — `5-execute: 4 voluntary_checkpoint, 0 budget_yield, 0 returned_with_findings, 1 clean_exit_queue_empty` over 5 rows
- aspect: log_analysis — `dispatch_clustering: inferred_dispatches 3, starting_markers 1, re_entering_markers 2`
- `TASK-001.json` — `bash_timeout_seconds: 360`; outline deliverable 2 verification declares `execution_tier: orchestrator`
