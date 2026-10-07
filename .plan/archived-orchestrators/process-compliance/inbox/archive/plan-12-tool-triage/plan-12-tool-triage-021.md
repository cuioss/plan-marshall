envelope_version=1
sender_type=plan
sender_id=plan-12-tool-triage
epic=process-compliance
kind=finding
created=2026-09-29T13:43:58Z

# integrate_into_main silently releases the merge lock held by branch-cleanup's widened hold

**Observed (plan-12-tool-triage, branch-cleanup, 2026-09-29):** branch-cleanup acquired the merge mutex under `merge_hold_window=full_window_release_at_waits` (`action: acquired`, before the enqueue) and held it through the queue landing. Per `branch-cleanup.md` the terminal release fires after `switch-and-pull`. The move-back (`integrate_into_main integrate`), which the finalize SKILL sequences between the merge and `worktree-remove`, acquires and releases the same lock internally. When the terminal `merge_lock release` ran after `switch-and-pull`, it returned `action: noop, message: lock not held (already free)`.

**The defect:** the move-back's own release ends the widened hold early — before `worktree-remove` and `switch-and-pull` — and the mutex's re-entrant acquire lets it do so without either caller noticing. The documented hold window ("releasing only after `switch-and-pull` has pulled the merge commit") is therefore not what runs whenever a worktree plan reaches the move-back inside branch-cleanup. The terminal release's `noop` looks identical to a legitimate re-entry no-op, so the early release is invisible.

**Suggested fix:** have `integrate_into_main` release only a lock it acquired itself (report `already_held` → skip release), or document the move-back as the sanctioned end of the hold and move the terminal release accordingly; either way make the terminal release distinguish "released by an inner holder" from "never held".
