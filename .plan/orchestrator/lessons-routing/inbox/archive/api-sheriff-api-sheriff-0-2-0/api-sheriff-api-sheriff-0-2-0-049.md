envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=candidate-lesson
created=2026-10-22T09:57:50Z

# Candidate lesson: An operator-accepted review finding does not carry to the next head, so each push after a close re-opens both reviews (plan-marshall:phase-6-finalize)

Forwarded from API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-43-validator-reserved-header-topology-rules (PR cuioss/API-Sheriff#505), local lesson 2026-10-22-08-002.

Related to api-sheriff-api-sheriff-0-2-0-034 and -043 (loop-back / head moves re-fire the review chain).

## What happened

In PLAN-V02-43 (PR #505) the operator closed the `weakened_test` false positive (see lesson 2026-10-22-08-001) for the functional review and the code review at head 841609f. The review-bot fixes (TASK-14, TASK-15) then moved the branch to head ee06753. The next round raised the same finding again in both reviews (7647aa, 5eb913, 57f6a2), with the same file, the same count and the same verifier answer. The operator had to close it a second time on 2026-10-22. The close record names the head it was given for ("operator close of code-review at 841609f..."), so it does not apply to the next head.

A delta review round after the head moves does not inherit an accepted finding. If the finding is caused by something the new commits did not touch, it comes back on every push, and the round cannot close without the operator.

## Why it matters

Every review-bot fix commit in finalize moves the head. With one recurring false positive, each fix costs an extra operator stop in two reviews. In an unattended run this blocks the run until the operator returns. It also adds to the non-converging finalize self-review cost already filed in plan-marshall (`lessons-routing-001`).

## Suggested direction (for plan-marshall)

- Carry an operator acceptance forward to the next head when the finding is identical (same rule, same file, same detail) and the delta between the heads does not touch that file.
- Re-open it only when the delta touches the file the finding is on.
- Keep the head in the record, so it is clear which head the acceptance was first given for.

## Provenance

Observed in plan `plan-v02-43-validator-reserved-header-topology-rules`, epic `api-sheriff-0-2-0`, PR #505 (merged as 1e53ab4f). Filed in the API-Sheriff store only because the plan-marshall `lessons-routing` inbox could not be written from the lessons-capture step. Route it to that inbox and remove this local copy afterwards.
