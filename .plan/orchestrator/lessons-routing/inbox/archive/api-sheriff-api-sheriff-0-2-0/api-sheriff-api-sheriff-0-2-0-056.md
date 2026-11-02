envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=candidate-lesson
created=2026-10-24T15:38:02Z

# Candidate lesson: for a plan that is itself a security control, outline should enumerate the input space the control must cover (plan-marshall:phase-3-outline)

Forwarded from API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-23-cookie-forwarding-policy-r2 (PR cuioss/API-Sheriff#515, merge bd730f5a), inbox message(s) plan-v02-23-cookie-forwarding-policy-r2-007.

For a plan whose subject is a security control (here a cookie forwarding policy), the finalize security audits repeatedly found genuine coverage gaps, each costing a late fix, review and CI cycle. Details are deliberately not recorded here; they are in the project's git-ignored local security notes.

Suggested direction: for plans that add or change a security control, run a security-expert lens in phase-3-outline that enumerates what the rule does NOT cover (edge-case names, empty or malformed values, every mode and variant of the deployment) and turns each into a success criterion and a test. Keep weakness details out of tracked artifacts.
