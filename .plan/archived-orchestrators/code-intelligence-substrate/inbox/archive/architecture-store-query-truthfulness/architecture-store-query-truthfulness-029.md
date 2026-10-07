envelope_version=1
sender_type=plan
sender_id=architecture-store-query-truthfulness
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-09-15T07:54:03Z

component=plan-marshall:manage-tasks
category=bug

# A one-token fix closed the cycle it targeted and left the comparison still false

Source: Q-Gate finding 3ae019 (6-finalize, self-review; fixed in cc4e8cf1b).
Defect class touched_claim_unverified — 2 findings in this class this round.

The swap from len(tasks) to len(numbered) at _cmd_qgate_mechanical.py:371 closed the
dropped-record phantom cycle the new comment at lines 330-334 describes. The surviving
claim on the line is still false: `numbered` is a LIST that may hold duplicate task
numbers, while in_degree at line 346 is a dict keyed by number, so duplicates collapse
there and visited can never exceed the DISTINCT-number count.

Two task records sharing a number therefore make `visited < len(numbered)` true with no
cycle present, emitting a phantom-cycle finding whose cycle_members list is EMPTY — it
renders as 0 tasks and names none. Nothing validates that a task file's number field
matches its TASK-NNN filename, so the state is reachable.

## Solution

Compare against len(in_degree), or reject duplicate numbers before building the graph.
The general rule: when a fix touches a comparison, re-derive BOTH sides against the
types they now hold. A hunk that repairs one failure mode and leaves the adjacent claim
stale reads as verified because it was just edited.

## Impact

A phantom finding that names no members is unactionable and erodes trust in the whole
check.
