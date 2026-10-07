envelope_version=1
sender_type=plan
sender_id=terminal-title-channel-reconciliation
epic=truthful-signals
kind=candidate-lesson
created=2026-07-27T19:54:48Z

component=plan-marshall:manage-change-ledger
category=bug
source_plan=terminal-title-channel-reconciliation
source_pr=1023
source_finding=575634

# A fast FAILURE is not evidence the suite is fast — failed runs must not feed the learned build timeout

## Observation (first-party, PLAN-79 / PR #1023)

The adaptive build-timeout mechanism learns a duration from observed build runs and derives
the budget from it. During this run:

1. A build aborted at **collection** after **129s** (a collection error, not a completed
   suite).
2. That 129s was fed into the learned duration as a normal observation.
3. The derived budget fell from **1617s to 1007s**.
4. A subsequent legitimate run needed more than 1007s and **timed out** — while the test
   suite was, over the same period, *growing* (15466 tests at the pre-push gate).

So the estimator moved the budget in exactly the wrong direction, and the evidence it moved
on was an artefact of a build that never ran the work the budget exists to cover.

## The corrective rule

**Only a run that completed the work the budget covers is evidence about how long that work
takes.** Concretely, for any learned-duration / adaptive-timeout estimator:

1. Feed the estimator **only** observations whose outcome is a completed run — success, or a
   failure that occurred *after* the measured work finished (e.g. assertion failures in a
   suite that ran to completion). A collection abort, an import error, a fail-fast exit, a
   harness kill, or a timeout is **not** a duration observation and MUST be discarded.
2. The estimator MUST be **monotone-safe against shrinkage from failures**: a budget that
   decreases must be traceable to completed runs that were genuinely faster. If the only
   evidence for a decrease is a non-completing run, the previous budget stands.
3. A timeout produced by the estimator's own shrunk budget must not then feed back as
   another short observation — that is a self-reinforcing collapse.

## Why this is easy to get wrong

The failure mode is invisible in the happy path and *looks* like the estimator working: the
budget adapts downward, the numbers move, nothing errors. It only surfaces one run later, as
a timeout attributed to "the suite got slow" rather than to the estimator. It also has the
same shape as the already-known ledger defect where timed-out builds are logged with
`exit_code: 0` — in both cases a non-completing build is recorded as if it were a normal
one, and downstream consumers read it as data.

## Truthful-signals relevance

The budget is a confident number derived from an input that does not measure what the number
claims to measure. The reported budget was never flagged as low-confidence, and the run it
killed reported a timeout — a signal that truthfully says "we stopped waiting" and is
routinely read as "the suite is too slow".
