# Merge-lock ownership is keyed on plan_id, so a same-plan session can release another's lock

Severity: high. Bundle: **plan-marshall** (`manage-locks` merge lock, `branch-cleanup` landing gate). Filed under RULING 2026-10-09 (a).

## Sources

- corpus `2026-10-11-16-004`

## Consolidated statement

`merge_lock` identifies the holder by `plan_id` alone. "Held by me" and "held by another session of my plan" are therefore indistinguishable: a second session of the same plan receives `already_held`, and every cleanup path must reason case by case about which verb (release vs dequeue) is safe.

The defect surfaced as a series of real, distinct defects in one lifecycle, each found by a later review round: a blocked move-back left the plan queued; a mid-wait error skipped the dequeue; a same-plan concurrent lock could be released by a refused call and the lock was not released on failure paths; the abandon/Skip-merge paths never dequeued; and finally the landing-gate failure path performs a plain `merge_lock release` while not holding the lock after an unobserved enqueue, which can delete a concurrent same-plan session's lock. The operator accepted the residual and merged; the self-review budget was spent.

## What is asked

- Record a session (or acquisition) token with the holder and require it on release, so release is safe by construction and the per-path release/dequeue reasoning collapses.
- Fix the residual `branch-cleanup.md` landing-gate failure path (release after an unobserved enqueue while not holding the lock) in the same change.
- Model the admission/lock states as one documented state table that every exit path is tested against, including the abandon and Skip-merge paths.

## Evidence

As recorded by the sender; a CodeRabbit comment and a Q-Gate finding name the same root. Not re-verified against HEAD in this run.
