envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=candidate-lesson
created=2026-10-24T15:38:03Z

# Candidate lesson: an operator ruling that removes an item is not recorded against the frozen success criterion that names it (plan-marshall:phase-6-finalize)

Forwarded from API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-23-cookie-forwarding-policy-r2 (PR cuioss/API-Sheriff#515, merge bd730f5a), inbox message(s) plan-v02-23-cookie-forwarding-policy-r2-011.

A frozen criterion required a specific LogRecord Javadoc and template. During execution an operator ruling removed that item, but the criterion was not touched. The finalize functional review then flagged a residual, and the criterion had to be rewritten and re-authorized late.

Suggested direction: record a ruling and rewrite the affected criterion plus criteria-authorize in the same step. Tooling could check, when a ruling is recorded, whether any frozen criterion text references the affected artifact.
