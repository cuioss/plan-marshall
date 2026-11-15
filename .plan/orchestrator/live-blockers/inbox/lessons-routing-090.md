envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-11-15T21:16:35Z

# HIGH (plan-marshall, operator-graded): a dispatched branch-cleanup stalls on its own background merge-queue wait, and a skipped adr-propose is caught by no guard before the merge

Filed by the `lessons-routing` drain of 2026-11-15. Source message: `api-sheriff-security-hardening-tier-1-004` (API-Sheriff plan `plan-sec-03-pending-authorization-store-fairness`, PR #581, 2026-11-09). Bundle: `plan-marshall` (`phase-6-finalize` `branch-cleanup`, pre-merge gate, `adr-propose`). Severity: high. The operator graded it high from a borderline medium/high in this session; the Linux session's 38-message drain of the same day (which also read this message) kept it medium, so the two operator rulings differ and the later one is filed.

## 1. `branch-cleanup` stalls on itself under `use_merge_queue: true`

- The step ran as a dispatched agent, enqueued the PR, then started a background wait for the queue landing and post-merge CI. A dispatched leaf is not woken by its own background task, so it stalled waiting on itself and had to be stopped.
- The orchestrator then did the whole post-merge cleanup by hand: `integrate_into_main integrate`, `worktree-remove` from the main checkout, `switch-and-pull`, `prune-local-and-remote-ref`, and recording the merge on the step.
- Sender's ask: make the merge-queue landing wait an orchestrator-owned barrier (the leaf enqueues and returns a wait signal; the orchestrator waits through `await-long-running`, then re-dispatches the post-merge half).

## 2. A skipped `adr-propose` (order 62) before `branch-cleanup` (order 70) is caught by no guard

- Neither the re-entry check nor the merge gate noticed. It surfaced only at the tail, when the manifest still listed `adr-propose` with no record, after the branch was merged and the worktree removed. The only enforcement is the end-of-phase `phase_steps_complete` handshake, which fires after the point where the step could still have run in order.
- This is the second recorded occurrence: API-Sheriff lessons `2026-10-12-07-004` / `-07-008` / `2026-10-13-14-005` ("adr-propose skipped after a hand-driven final round") are archived in `lessons-archive/` as an earlier occurrence.
- Sender's ask: a pre-merge guard that refuses the merge while any manifest step ordered before `branch-cleanup` has no terminal record.

## Related, not the same

Local corpus lessons `2026-11-12-19-003` (branch-cleanup with `use_merge_queue=true` escalates on a squash message) and `-19-004` (branch-cleanup as a leaf cannot remove the worktree) sit in the same step; they are `ingest` scope and not folded here.

## Evidence

The sender's own observation; not re-run on the plan-marshall side and not checked in code at the drain. Please check both halves at the head `live-blockers` works from, and decide whether either is already owned by a shipped or running plan.
