envelope_version=1
sender_type=plan
sender_id=post-merge-review-findings-untriaged-in-main
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T09:45:13Z

component=plan-marshall:phase-6-finalize
category=bug
created=2026-07-29
bundle=plan-marshall

# execution.md sequences the 5-execute capture before the transition, but recovery inserts a commit between them

`execution.md` sequences "capture the 5-execute handshake" BEFORE the phase-5-to-6 transition, but
the transition's own `worktree_dirty_at_boundary` recovery path mandates a settlement commit BETWEEN
the capture step and the transition itself. So on any plan that takes the recovery path (this plan
did), the captured handshake is guaranteed stale by the time the transition actually runs — it was
snapshotted before the settlement commit that the recovery required.

## Solution

Re-order (or re-derive) the captured handshake AFTER the `worktree_dirty_at_boundary` recovery's
settlement commit, not before it, so the capture reflects the tree state the transition actually
operates on. Alternatively, have the recovery path explicitly invalidate/refresh the prior capture
once its settlement commit lands.

## Impact

Any plan whose 5-to-6 transition takes the dirty-boundary recovery path inherits a stale-by-
construction capture, silently — the capture step itself reports success without knowing a
settlement commit will land after it. This is a mechanism-level ordering bug, not a one-off plan
mistake.
