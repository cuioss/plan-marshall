envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-11T14:52:44Z

Candidate lesson (source: process observation during PR #28 review handling, plan http-baseline; reported by the orchestrating session).

The triage verb `workflow-integration-github post_responses` transmitted "fixed" replies for review comments (d89a45, c9636e, 2b2657, responded 08:23Z) before the fix commit existed on the branch. Their resolution_detail reads "Will be addressed by TASK-9 ... see follow-up commit on this branch", i.e. the reply promised a commit that had not been pushed yet. The verb offers no deferral option, so the reply cannot be held until the fix lands.

Corrective candidate: post_responses should support deferring `fixed` replies until a named commit is on the remote (or the triage flow should transmit only after the remediation commit is pushed), so a reviewer never sees "fixed" on an unchanged branch.

Component candidates: plan-marshall:workflow-integration-github (post_responses), plan-marshall:automatic-review (triage ordering).

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `http-baseline-006.md` from plan http-baseline (PLAN-05, #28)
