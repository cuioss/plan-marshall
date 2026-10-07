envelope_version=1
sender_type=plan
sender_id=detector-and-auditor-integrity
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-31T08:30:08Z

# voluntary_checkpoint is the modal dispatch termination and cost two thirds of operator attention

component: plan-marshall:phase-5-execute
category: anti-pattern
severity: error
source_plan: detector-and-auditor-integrity
source_pr: 1370

## What was observed

Phase-5 dispatch terminations, from the boundary ledger (14 rows):

```
voluntary_checkpoint      10
budget_yield               3
clean_exit_queue_empty     1
```

`voluntary_checkpoint` means the agent stopped with work still in the queue.

The session transcript reduces to 9 operator turns. **Six of them exist only to
restart a halted run**:

- "why did you stop?" (x2)
- "do continue"
- "why do you allways stop??? run to the end as instructed multiple times"
- "why did you stop? continue with finalize to the end"
- "proceed with finalize without further stopping"

The operator's FIRST instruction had already said: "continue as defined to the
end of finalize. DO only stop on issue."

## Why this is a measurable defect, not a mood

The two observations corroborate each other from independent sources: the ledger
says the dispatch stopped voluntarily 10 times, the transcript says the operator
had to restart it 6 times. Two thirds of all operator attention on a plan that
cost 10.1M tokens went to re-issuing an instruction given at the start.

The wall-clock cost is visible too: 3h0m idle against 10h44m worked, and phase
3-outline alone carried 1h9m idle against 35m1s worked.

## Related, same run

The operator also had to intervene on the merge mutex ("igrone the mutex and
continue"). That override's cost materialised: the first enqueue was ejected when
4 upstream PRs landed during the queue wait, forcing a rebase, a re-derived
constant, a full re-verify, a force-push and a re-review to clear a required bot
gone stale.

## The generalizable rule

A standing operator instruction to run to completion should survive a dispatch
boundary. Either the instruction needs to be persisted into the plan state that
each dispatch reads, or `voluntary_checkpoint` needs a much higher bar than it
currently clears — a checkpoint with a non-empty queue and no blocking condition
is a stall, not a checkpoint, and the ledger already distinguishes it from
`budget_yield` and `blocked_*`. Consider treating a `voluntary_checkpoint` with
`tasks_remaining > 0` and no `blocked_*` cause as an auto-resume rather than a
return to the operator.
