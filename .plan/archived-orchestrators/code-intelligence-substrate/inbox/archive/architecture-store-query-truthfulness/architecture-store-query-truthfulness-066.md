envelope_version=1
sender_type=plan
sender_id=architecture-store-query-truthfulness
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-09-15T07:59:06Z

component=plan-marshall:plan-marshall
category=improvement

# The phase handshake reported drift caused by the entry protocol's own Q-Gate step

Source: script-failure cluster, notation plan-marshall:plan-marshall:phase_handshake
(exit_code=1, failure_kind=script_internal_failure). 2 occurrences, 5-execute re-entry.
The only NON-argparse cluster of the run.

- 21:36:55 — `verify --phase 4-plan --strict` returned status=drift, drift_count=4:
  task_state_hash changed; unfinished_tasks_count 19 -> 11; pending_findings_by_type
  improvement 0 -> 1; pending_findings_blocking_count 4 -> 2. The leaf refused to
  rationalize and returned a prompt-required envelope.
- 21:48:37 — after an override, drift_count=1: pending_findings_blocking_count
  captured=2, observed=1.

The second drift's cause was established and is the lesson: the ENTRY PROTOCOL'S OWN
Q-Gate step resolved finding be4ef7 (taken_into_account) immediately before the verify
ran, dropping the all-phase pending actionable count from 2 to 1. The handshake compared
a snapshot captured before that resolution against a state the protocol itself had just
changed.

## Solution

A strict invariant check placed AFTER a step that mutates the invariant's inputs will
report drift on every clean run. Either capture the snapshot after the entry protocol's
own mutations, or exclude self-caused deltas from the strict comparison. The leaf's
behaviour was correct throughout — it refused to rationalize and escalated twice — so the
cost landed on the operator, not on correctness.

## Impact

Two phase-entry refusals and an authorized-override decision, both on a self-inflicted
delta.
