envelope_version=1
sender_type=plan
sender_id=runnable-slice-keys-on-the-floor-not-the-measurement
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T06:12:26Z

component=manage-locks
category=bug
created=2026-07-29

# An unreadable merge lock was reported as a free merge lock

The merge-lock monitor's event stream reads, verbatim:

```
LOCK_READ_ERROR: Expecting value: line 1 column 1 (char 0)
... (nine consecutive identical lines) ...
LOCK_FREE: merge.lock absent
```

Nine consecutive JSON-decode failures are positive evidence that the lock file
was PRESENT but unreadable — mid-write, truncated, or empty. That is close to the
opposite of absent. The monitor collapsed "I could not read the lock" into "there
is no lock" and fired its ready signal on that basis.

An error state silently mapped onto the most permissive outcome is the highest-
risk shape of this epic's theme: for a mutex, "unknown" and "free" have opposite
safety properties, and mapping the former to the latter defeats the mutex on
exactly the occasions it matters (concurrent writers). This run also required the
operator to intervene manually ("lift the mutex"), so lock-state handling was
already the run's friction point.

This compounds the standing rule that a merge lock's staleness must never be
judged from a worktree-scoped store — an empty worktree-scoped read means
"unknown", not "free". Same inversion, different input.

## Impact

Lock-state reads need three values, not two: `held`, `free`, and `unknown`.
A parse failure, a permission error, and a partial read all yield `unknown`, and
`unknown` must be treated as `held` for admission purposes (fail-closed). A
repeated `unknown` should escalate to the operator rather than decay into `free`.
Emitting `LOCK_FREE: merge.lock absent` after nine failed reads asserts a fact
the reader specifically did not establish.
