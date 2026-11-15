envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-security-hardening-tier-1
epic=lessons-routing
kind=candidate-lesson
created=2026-11-09T11:45:57Z

component=plan-marshall:phase-6-finalize
category=bug
title=Dispatched branch-cleanup stalls on its own background merge-queue wait; a skipped adr-propose is caught by no guard before the merge

# Dispatched branch-cleanup stalls on its own background merge-queue wait; a skipped adr-propose is caught by no guard before the merge

Source: API-Sheriff epic `security-hardening-tier-1`, inbox message `plan-sec-03-pending-authorization-store-fairness-004.md` (plan `plan-sec-03-pending-authorization-store-fairness`, PR cuioss/API-Sheriff#581, 2026-11-09). The `adr-propose` half recurs an archived item: lessons-archive INDEX row for API `2026-10-12-07-004` / `-07-008` / `2026-10-13-14-005` ("`adr-propose` skipped after a hand-driven final round"). The `branch-cleanup` stall half is new.

## Observations

1. **`branch-cleanup` stalls on itself.** The step ran as a dispatched agent with `use_merge_queue: true`. It enqueued the PR and then started a background wait for the queue landing and the post-merge CI. A dispatched leaf cannot be woken by its own background task, so the agent stalled waiting on itself and had to be stopped. The orchestrator then did the whole post-merge cleanup by hand: `integrate_into_main integrate`, then `worktree-remove` from the main checkout, then `switch-and-pull`, then `prune-local-and-remote-ref`, then recording the merge on the step.
2. **A skipped `adr-propose` is caught by no guard (recurrence).** `adr-propose` (order 62) did not run before `branch-cleanup` (order 70). Neither the re-entry check nor the merge gate caught the ordering gap. It surfaced only at the tail, when the manifest still listed `adr-propose` with no record, after the branch was already merged and the worktree removed.

## Why it matters

- A leaf that backgrounds a wait whose result it needs violates the leaf contract: only the orchestrator-tier `await-long-running` seam may do that. The stall cost wall-clock time and left the cleanup half-done.
- Steps ordered before the merge can be silently skipped. The only enforcement is the end-of-phase `phase_steps_complete` handshake, which fires after the point where the skipped step could still have run in order. This is the second recorded occurrence of the skip.

## Suggested correction (from the reporting plan)

- Make the merge-queue landing wait in `branch-cleanup` an orchestrator-owned barrier: the leaf enqueues and returns a wait signal, the orchestrator waits through `await-long-running`, then re-dispatches the post-merge half.
- Add a pre-merge guard (for example in the pre-merge gate) that refuses the merge while any manifest step ordered before `branch-cleanup` has no terminal record.
