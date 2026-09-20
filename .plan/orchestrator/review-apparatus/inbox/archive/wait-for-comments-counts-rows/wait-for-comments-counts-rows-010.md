envelope_version=1
sender_type=plan
sender_id=wait-for-comments-counts-rows
epic=review-apparatus
kind=candidate-lesson
created=2026-08-01T17:45:15Z

# Decision-log the pre-merge barrier verdict on the clean path too

component: plan-marshall:phase-6-finalize
category: improvement
confidence: high
source_plan: wait-for-comments-counts-rows
source_pr: 1071

## Context

`branch-cleanup.md` prescribes decision-log lines for the conflict-severity classifier, the
pre-rebase gate, the pre-merge gate, the trigger-A re-review timeout, and the merge-queue
budget-exhaustion escalation. It prescribes **no** decision-log line for the Pre-Merge
Review-Completeness Barrier's verdict on the clean path.

The consequence is that in this plan's `decision.log` (86 entries) there is no barrier line at all —
which is exactly what a barrier that PASSED would also look like. When the barrier's producer call
died with exit 2 and the merge proceeded anyway, the log recorded nothing to distinguish
"barrier passed" from "barrier never ran". The only trace of the failure is an executor-level
`[ERROR]` line in `work.log`, emitted by `execute-script`, not by the step.

## Root cause

The logging contract covers branch points that CHANGE behaviour (a gate that fires, a threshold that
trips) but not the gate verdict itself. A gate that always logs only when it blocks makes its silence
ambiguous between "did not block" and "did not run".

## Proposed action

- Emit one `decision` log line for EVERY barrier evaluation, carrying the tri-state verdict
  (`clean` / `blocked` / `indeterminate`), the two predicate results (`pending_count`,
  `participation_complete`), and the `{barrier_mode}` in force.
- Apply the same rule to any other finalize gate whose clean path is currently silent: a gate's
  verdict is load-bearing evidence and must be recorded whether or not it changed the flow.
- Surface the verdict in `branch-cleanup`'s `mark-step-done --display-detail` so the
  `phase_steps` record itself carries it (today the record reads
  `"merged PR #1071 via queue, main pulled, worktree removed"` — no barrier mention).

## Evidence

- aspect: logging_gap_analysis — "The pre-merge review-completeness barrier emits no decision-log line on its CLEAN path, so a barrier that silently did not run is indistinguishable in the log from one that ran and passed."
- `decision.log` contains 86 entries and no barrier verdict for this plan; the window between `17:11:52Z` (barrier producer exit 2) and `17:22:59Z` (merge) contains no `branch-cleanup`-authored entry.
- `status.metadata.phase_steps["6-finalize"]["branch-cleanup"].display_detail` names the merge, the pull, and the worktree removal — but not the barrier.
