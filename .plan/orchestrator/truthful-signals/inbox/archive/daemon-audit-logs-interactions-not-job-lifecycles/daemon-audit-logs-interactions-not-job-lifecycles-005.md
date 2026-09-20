envelope_version=1
sender_type=plan
sender_id=daemon-audit-logs-interactions-not-job-lifecycles
epic=truthful-signals
kind=candidate-lesson
created=2026-07-28T15:48:02Z

component=plan-marshall:manage-build-server
category=bug
bundle=plan-marshall

# A scheduler admission and a terminal-state store are two authorities that must be reconciled at the admission seam

## What was observed

`Daemon._admit_ready` admitted and executed a job whose journal entry **already held a
terminal status**. The consequences compounded in three directions from one missing
check:

1. the build re-ran;
2. `_journal.record_status(job_id, STATUS_RUNNING)` clobbered a terminal status back to
   `running` — a durable record of a finished job silently reverted to in-flight;
3. a SECOND `job_fate` audit record was appended for a single terminalization.

Consequence (3) is what surfaced it: a duplicate-`job_fate` test failure in TASK-007
(Q-Gate findings `a7828a` + `78ffc4`). Consequences (1) and (2) were found by
root-causing, not by a failing assertion.

## Root cause

The scheduler's admission queue and the journal's status field are **two independent
authorities on "has this job ended?"**, and nothing reconciled them at the seam where
admission becomes execution. The scheduler could hold a pending admission for a job the
journal already knew was finished.

## Fix

An `_is_terminalized(job_id)` guard at the top of the admit loop, which **releases** the
admission (`self._scheduler.complete(entry.job_id)`, freeing both the slot and the
idempotency fingerprint) and continues, instead of executing. One terminalization can
therefore emit only one fate.

Deliberate polarity in the guard: a job with **no** journal entry reads as NOT
terminalized. Absence is not evidence of an outcome, and a job whose entry has not been
written yet must still be allowed to run. Defaulting the other way would have converted
a duplicate-execution bug into a silent never-execute bug.

## Why it matters to this epic

The journal's `running` status was a **confident signal that had been overwritten by a
later, less-informed writer**. Anything reading the journal after the re-admission would
have been told a finished job was in flight, with no trace of the terminal status it
used to hold. The duplicate audit record was the only externally visible symptom — the
status regression left no evidence of itself.

## Proposed rule

Wherever a work queue and a durable state store both answer "is this finished?", the
admission/dispatch seam must consult the durable store before acting, and a write that
would move a record BACKWARD out of a terminal state should be refused (or at minimum
detectable), not silently applied. A terminal state is an absorbing state; treat any
transition out of it as a defect signal rather than a normal update.
