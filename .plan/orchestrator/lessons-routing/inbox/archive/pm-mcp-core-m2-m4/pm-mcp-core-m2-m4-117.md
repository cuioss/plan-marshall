envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-12T05:31:58Z

# commit-add rejected fix tasks allocated by verification-feedback with `deliverable: 0`

Source: orchestrator observation for this run. The script log matches it: the first `manage-tasks commit-add` at 2026-10-11T19:52:49Z (b1998c) returned in 0.17s and was followed by repeated commit-add calls at 19:53:22 to 19:53:29 (f68d4c, b21a3f, 73f3e1). That pattern fits a fast refusal and a retry. The refusal text itself was not captured in the plan logs.

## What happened

Verification-feedback triage in round 1 allocated the fix tasks TASK-10, TASK-11 and TASK-12 for pr-comment 28dec1 and six sonar-issue findings. They were allocated with `deliverable: 0`, because a review fix belongs to no outline deliverable. `manage-tasks commit-add` refused them with "Missing required field: deliverable". The truthiness check treats `0` as missing, so the loop-back fix tasks could not be committed until the payload was corrected.

## Candidate rule / fix

Either the validator must accept `0` (check for presence, not truthiness), or verification-feedback must allocate fix tasks against a real deliverable number or a documented sentinel that commit-add accepts. Right now the producer and the consumer of the field disagree on what a valid value is. Owner: plan-marshall `manage-tasks` (commit-add validation) / phase-6-finalize verification-feedback.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `static-verifier-and-fuzzer-004.md` from plan static-verifier-and-fuzzer (PLAN-10, #32)
