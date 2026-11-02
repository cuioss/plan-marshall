envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=candidate-lesson
created=2026-10-24T15:38:01Z

# Candidate lesson: review_support delta scope equalled the full plan footprint, so "clean delta then closing full round" ran the same review twice (plan-marshall:phase-6-finalize)

Forwarded from API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-23-cookie-forwarding-policy-r2 (PR cuioss/API-Sheriff#515, merge bd730f5a), inbox message(s) plan-v02-23-cookie-forwarding-policy-r2-003.

Three times in finalize the attribution delta covered all 8 deliverables and all 93 changed files, identical to the full scope. The rule "clean delta round, then a closing full round" then ran the same full review twice.

Suggested direction: when the delta scope equals the full scope, treat the delta round as the closing full round. Show delta-vs-full size on the review dispatch so the collapse is visible.
