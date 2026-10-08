envelope_version=1
sender_type=plan
sender_id=lb-22-finalize-loop-control
epic=live-blockers
kind=candidate-lesson
created=2026-10-08T20:57:15Z

component=plan-marshall:workflow-integration-git
category=bug
source_plan=lb-22-finalize-loop-control
confidence=high

# Keep the merge lock held across integrate_into_main during branch-cleanup

## Context

`branch-cleanup` acquires the cross-plan merge lock before the merge and documents its release after `switch-and-pull`. In between it calls `integrate_into_main`, which acquires the same lock under the same plan id and releases it when it returns. The release is real: the lock file is removed at that point. The worktree removal and the pull that follow run without the lock, and the documented release afterwards finds nothing to release.

Call order recorded for this plan (2026-10-08): `merge_lock acquire` 20:05:12, `worktree-remove` 20:43:52, `switch-and-pull` 20:43:57, `merge_lock release` 20:44:02.

## Root cause

The lock is reentrant on acquire and not counted on release. `merge_lock.py` says so directly: a second acquire by the same plan id returns `already_held`, and "the reentrant grant is not a second independent acquisition: release stays idempotent and holder-scoped, so the single os.unlink fires once when the holder releases". `integrate_into_main.py` releases on every exit path, including success (`_release_and`), so the first release to run is the inner one.

## Proposed action

One of:

- let `integrate_into_main` skip its release when its acquire answered `already_held` (it did not take the lock, so it must not drop it); or
- count holds per plan id so only the outermost release unlinks.

Add a test that holds the lock, runs `integrate_into_main`, and asserts the lock is still held afterwards. A test for the reentrant acquire exists (`test_manage_locks_merge_lock_reentrant_acquire.py`); the release side is the gap.

## Evidence

- source at main `6b00815e0`: `workflow-integration-git/scripts/integrate_into_main.py` lines 478-495 and 517-529 (acquire, then `_release_and` on success); `manage-locks/scripts/merge_lock.py` module docstring, the `acquire` bullet on reentrancy.
- aspect: log_analysis - the four script-log entries above.
- limit of the evidence: the `integrate_into_main` call itself ran while the plan directory was still in the worktree and is not in the script-log window read here, and the lock-event log was not read. The early release is established from the two sources; the operator observed it in the run.
