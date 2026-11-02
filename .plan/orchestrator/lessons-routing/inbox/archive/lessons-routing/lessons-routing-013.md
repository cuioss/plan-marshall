envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=lessons-routing
kind=finding
created=2026-10-28T05:46:44Z

# pr-comment promotion truncates a long review-bot body before the actual request, and dispatched leaves force their own step marks

Source: API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-09-token-sheriff-integration-fidelity (PR #530), candidate lesson 003 and the landing residue. Observed with plugin and executor 0.1.2021.

## Observation

1. One CodeRabbit comment body was 36,938 characters. When the pr-comment finding was promoted, the body was cut to 8,000 characters. The part that states the actual change request came after the cut, so it survived only in the finding's `raw_input`. Anyone triaging from the promoted `body` or `detail` alone would have missed what the bot asked for.
2. Several dispatched leaves recorded their own step with `mark-step-done --force` (adr-propose, lessons-capture). The reason was not investigated.

## What to consider

- Mark a truncated body as truncated (a flag and the original length), or extract the actionable part of a CodeRabbit comment (title, prompt-for-agents section) before truncating. Until then, triage should read `raw_input` whenever a promoted body is at the cap.
- Find out why leaves reach for `--force` on their own step marks, and whether the forced mark hides a refused transition.
