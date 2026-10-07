envelope_version=1
sender_type=plan
sender_id=participation-credit-anchored-to-merge-candidate
epic=review-apparatus
kind=candidate-lesson
created=2026-08-25T21:18:35Z

component=plan-marshall:manage-locks
category=bug
confidence=high
source_plan=participation-credit-anchored-to-merge-candidate
source_pr=1349

# Reentrant-acquire FIFO test is vacuous — it short-circuits before the enqueue it names

## Context

`merge_lock.py`'s module docstring states the enqueue contract precisely:

> `acquire` first FIFO-enqueues `--plan-id` into `merge-queue.json` (idempotently — a
> plan already in the queue KEEPS its FIFO position (its existing list slot), never
> re-appended to the back, mirroring `build_queue.run_acquire`'s idempotent fast-path).

That idempotency is load-bearing, because the documented consumer pattern is a poll
loop that calls `acquire` repeatedly. `branch-cleanup.md` § "Acquire the Merge Mutex"
says: "`acquire` returns immediately, pace polls with a single standalone `sleep
{interval}` Bash call, evaluate the `admission` discriminator". A blocked plan therefore
calls `acquire` once per poll interval for as long as it waits — this run waited roughly
75 minutes.

The test that appears to cover this is
`test_manage_locks_merge_lock_reentrant_acquire.py::TestReentrantAcquire::test_reentrant_grant_does_not_enqueue_into_fifo`.
Its name and docstring both claim the enqueue property:

> "The reentrant short-circuit fires BEFORE the FIFO enqueue — a self-holder re-acquire
> must not churn the queue with a duplicate entry."

But read the arrangement: the test makes `plan-a` the **holder**, then has `plan-a`
re-acquire. The docstring says it outright — the short-circuit fires *before* the FIFO
enqueue. So the assertion `_waiting_plan_ids(queue_path) == before` holds because the
enqueue code was never reached, not because the enqueue is idempotent. The test passes
for a reason unrelated to the property its name asserts.

The case the poll loop actually produces — `acquire` called repeatedly by a plan that is
a **waiter**, not the holder, and therefore does reach the enqueue — has no test at the
merge-lock layer. Searching the tree for `FIFO position` returns
`test_build_queue_admission_and_release.py` (the build queue, a different primitive),
`test_manage_locks_merge_lock_release.py`, and the fixtures module — no merge-lock test
of a waiter's repeated acquire. `test_concurrent_then_drained_serves_every_plan_exactly_once`
does assert every contender is enqueued exactly once, but each of its contenders calls
`acquire` exactly once, so it does not exercise repetition either.

## Root cause

This is the vacuous-guard archetype in its exact canonical form: a test whose subject is
made unreachable by its own arrangement. The short-circuit the test sets up is precisely
the branch that prevents the code under test from running. Because the arrangement makes
the holder path the one taken, the enqueue's idempotency — the property the test is
named for, and the only property the poll loop depends on — is asserted by nothing.

The naming makes it worse rather than better: a reader auditing coverage for enqueue
idempotency finds a test named `does_not_enqueue_into_fifo`, reads its docstring, and
concludes the property is pinned.

## Proposed action

1. Add the missing test: `plan-b` blocked behind live holder `plan-a`; call
   `acquire --plan-id plan-b` N times; assert `_waiting_plan_ids` contains `plan-b`
   exactly once and at an unchanged index, and that `waiting_count` does not grow.
   This is a matched positive control for the property the docstring claims.
2. Add its negative control: after `plan-a` releases, assert `plan-b` is admitted on
   its next poll, with `blocking_plan_id` naming a real holder at every blocked poll and
   never `null` while `admission: blocked`.
3. Rename `test_reentrant_grant_does_not_enqueue_into_fifo` to say what it actually
   proves — that the holder short-circuit returns before touching the queue — so it
   stops reading as coverage of the enqueue.

## Related observation (reported, not corroborated)

The run reported a state of `waiting_count: 2` with `blocking_plan_id: null` that
persisted until two release cycles drained it, and interpreted it as having blocked
behind its own duplicate FIFO entry. That interpretation is **not corroborable from the
retained artifacts** — `merge-queue.json` is transient runtime state and has since
drained — and it is contradicted at the escalation point by the session transcript,
which names a live foreign holder:

> "The merge mutex has been held by plan `fold-pm-code-intelligence-into-core` for the
> full ~30-minute FIFO budget (3 attempts, holder and waiting_count never moved)."

So at the escalation the block was a genuine foreign holder, not self-blocking. The
duplicate-entry claim is filed here as an unverified report rather than a finding. What
IS verified is that the coverage gap above is exactly where such a bug would live
undetected, and that a `blocking_plan_id: null` alongside `admission: blocked` is by
itself a payload worth explaining — it says the caller is blocked with no holder named.

## Evidence

- source: `manage-locks/scripts/merge_lock.py` module docstring, lines 24-28
  (idempotent, FIFO-position-preserving enqueue).
- source: `phase-6-finalize/standards/branch-cleanup.md` § "Acquire the Merge Mutex"
  (the repeated-`acquire` poll loop).
- test: `test_manage_locks_merge_lock_reentrant_acquire.py::test_reentrant_grant_does_not_enqueue_into_fifo`
  — docstring states the short-circuit fires before the enqueue.
- coverage sweep: `architecture search --content --pattern "FIFO position"` — no
  merge-lock test of a waiter's repeated acquire.
- aspect: chat_history_analysis — the operator escalation naming the foreign holder.
