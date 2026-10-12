envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-12T05:31:57Z

# Sourcery review-budget refusal was not recognised as a bot refusal by fetch_findings

Source: pr-comment finding 28e8a7 on PR #32 (sourcery-ai issue_comment); triage decision 363341.

## What happened

Sourcery posted this:

> Sorry @cuioss-oliver, this account has used its review budget of 2,500,000 diff characters for the last 7 days. You can request another review in 4 days and 14 hours by commenting `@sourcery-ai review`.

`workflow-integration-github` `fetch_findings` filed it as an ordinary pr-comment finding. `refused_bots` and `unrecognised_refusal` were both empty. Triage then had to classify it by hand ("Sourcery review-budget refusal from an optional bot, not a code finding") and accept it without a reply. Sourcery went on to approve in rounds 2 and 3, so on round 1 it had not reviewed at all. Because the refusal went unrecognised, round 1 counted Sourcery as having participated.

## Candidate rule / fix

Add a quota/budget refusal shape to the provider's `refusal_patterns` for sourcery: "used its review budget", "request another review in". The refusal should then land in `refused_bots` and feed the participation verdict, instead of reaching triage as a comment. Owner: plan-marshall `workflow-integration-github` (refusal patterns) / `automatic-review`.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `static-verifier-and-fuzzer-002.md` from plan static-verifier-and-fuzzer (PLAN-10, #32)
