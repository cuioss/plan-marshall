envelope_version=1
sender_type=plan
sender_id=lb-25-phase-and-merge-gates
epic=live-blockers
kind=candidate-lesson
created=2026-10-11T16:01:17Z

component=plan-marshall:manage-locks
category=bug
bundle=plan-marshall
source_plan=lb-25-phase-and-merge-gates

# Key merge-lock ownership on the session, not only on plan_id

## Context

lb-25-phase-and-merge-gates changed the merge-lock admission wait and the integrate_into_main lock lifecycle. Every review round after that produced a new real defect in the same lifecycle: a blocked move-back left the plan queued (4fda7b), a mid-wait error skipped the dequeue (f25863), a same-plan concurrent lock could be released by a refused call and the lock was not released on failure paths (e9adb0, cfbc65), the abandon/Skip-merge paths never dequeued, and finally the landing-gate failure path releases while not holding the lock after an unobserved enqueue. The self-review budget ran out and the operator accepted the residual; CodeRabbit 2e71e5 (same class as Q-Gate bc5abc) names the root: ownership is keyed on `plan_id`, so a second session of the same plan gets `already_held` and can release a lock it does not own.

## Root cause

`merge_lock` identifies the holder by `plan_id` alone, so "held by me" and "held by another session of my plan" are indistinguishable, and every cleanup path must reason about which verb (release vs dequeue) is safe case by case.

## Proposed action

Record a session (or acquisition) token with the holder and require it on release, so release is safe by construction and the per-path release/dequeue reasoning collapses. Fix the residual `branch-cleanup.md` landing-gate failure path (release after an unobserved enqueue while not holding the lock) in the same change, and model the admission/lock states as one documented state table that every exit path is tested against.

## Evidence

- aspect: chat_history_analysis - operator decision: "the landing-failure path does a plain merge_lock release while not holding the lock, which can delete a concurrent same-plan session's lock" -> "Accept and merge as is"
- aspect: chat_history_analysis - triage leaf: "accepted CodeRabbit's merge-lock comment (2e71e5) under the operator's earlier decision in bc5abc"
- aspect: request_result_alignment - D10 shipped with an operator-accepted residual
