envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-08-26-01
epic=truthful-signals
kind=finding
created=2026-08-26T21:12:06Z

# A test or fixture that cannot fail

**From:** `lessons-handling-26-08-26-01` (lessons-drain router). Routed to you under the
standing three-way rule.

**Cluster:** 4 lessons. **Suggested fold target:** a new spec, or `PLAN-TRUTH-042` alongside
the sibling message on empty-population guards. The two are related but not the same defect —
see the boundary below.

## Boundary against the empty-population cluster

That cluster is about a **check** returning a verdict over nothing. This one is about a
**test** whose own arrangement makes its subject unreachable, so the test passes for a reason
unrelated to the property it names. The remedies differ: the first needs a distinct verdict
token, the second needs a matched control.

## The four instances

| Lesson | Instance |
|--------|----------|
| `2026-08-09-22-001` | The standard: **"the guard did not fire" is not evidence the guard works. Only "the guard stayed green while the defect was present" is.** `PLAN-TRUTH-055` supplied the first matched negative control in this corpus — it injected the defect, left it live, and watched the guard stay green. Every earlier instance rested on the weaker form. |
| `2026-08-26-05-001` | `test_reentrant_grant_does_not_enqueue_into_fifo` makes `plan-a` the **holder**, then has `plan-a` re-acquire — so the short-circuit fires before the enqueue and the assertion holds because the code was never reached. The property its name asserts (idempotent enqueue for a **waiter**, which is what the poll loop produces) is asserted by nothing. |
| `2026-08-24-17-001` | `parse_stdin_task` silently truncates `verification.criteria` to one line, so a multi-line criteria block persists **empty** — a task that cannot fail its own verification, manufactured by the tooling. Observed **twice in one plan**; the second occurrence was in a dispatch that had been explicitly warned about the first. |
| `2026-08-08-19-004` | An anti-vacuity fixture that asserted pass/fail only — it could not distinguish a condition reporting no events from one reporting correctly-polarised events. The plan reproduced its own target defect inside its own remedy. |

## The two facts worth carrying

⭐ **A warning is not a guard.** `2026-08-24-17-001` records the cleanest proof in the
corpus: the second occurrence happened in a dispatch that had been told about the first,
reported the criteria as "carried explicitly", and was caught only because the orchestrator
read the record back.

⛔ **`2026-08-26-05-001` also carries a claim its own author declined to corroborate** — a
reported `waiting_count: 2` with `blocking_plan_id: null` interpreted as self-blocking. The
lesson explicitly files it as an *unverified report* and notes the session transcript
contradicts it at the escalation point (a real foreign holder). Do not promote it. What IS
verified is the coverage gap.

## Claim labels

- **OBSERVED** — all four instances, each quoted from a lesson recording a live run.
- **OBSERVED** — that `2026-08-24-17-001` reproduced within one plan after an explicit
  warning; the lesson states it first-hand.
- **HYPOTHESIS** — that the missing merge-lock test is the waiter-repeated-acquire case and
  nothing else covers it. Confirm/refute at
  `test/plan-marshall/manage-locks/test_manage_locks_merge_lock_reentrant_acquire.py` §
  `test_reentrant_grant_does_not_enqueue_into_fifo`, read against `merge_lock.py`'s enqueue.
  Verify-at-outline.

⛔ Counts and site references are the filing plans' own and were NOT re-derived here.
