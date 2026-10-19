envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-19T18:47:05Z

component=plan-marshall:phase-3-outline
category=anti-pattern

# Success criterion depended on a cross-repository link fix the plan's own PR could not carry

Source: Q-Gate 6-finalize finding 22e83d (functional-review, unevidenced_criterion at D10.C2; resolved in run as accepted by operator decision), plan plan-70-plan-instance-alignment.

D10.C2 required "no file of either repository links the deleted package file", but `plan-marshall-documentation/doc/roadmap.adoc:233` still linked `doc/plans/plan-instance-alignment.adoc`. The fix lives in another repository (merged as plan-marshall-documentation PR 96), so the criterion was unevidenced at the review head and needed an operator acceptance.

## Rule

When deleting a work package file, open the documentation-repository link fix before the functional review (or phrase the criterion so it is evidenced by this repository's head plus a named, merged foreign PR). Siblings 82db0b, ea6e2e, d90ef8 and 328ad4 are the same D10 issue at the next criteria and the next head.
