envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-19T18:47:06Z

component=plan-marshall:phase-6-finalize
category=improvement

# Accepted functional-review findings re-fire after a correction commit advances the head

Source: Q-Gate 6-finalize finding d90ef8 (functional-review, unevidenced_criterion at D10.C3 at the new head; resolved in run as accepted), plan plan-70-plan-instance-alignment.

The operator had already accepted the D10.C3 finding (82db0b) at head 44a74168. The correction commit 8c36987 that fixed the code-review findings advanced the head, which voided the earlier close, so the functional review ran again and re-raised the identical, structurally unevidenceable criterion; the operator had to repeat the same decision.

## Rule

A finding accepted by operator decision whose subject is outside the diff of the head-advancing commit (here: the PR body and a foreign-repo PR) should carry forward to the new head instead of being re-raised. Short of that, avoid criteria that cannot be evidenced at review time (see 82db0b).
