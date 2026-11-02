envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=candidate-lesson
created=2026-10-24T19:59:40Z

# Candidate lesson: `github_pr fetch_findings` re-files an already-handled CodeRabbit review-summary body as a new pending finding at the new HEAD (plan-marshall:workflow-integration-github)

Forwarded from API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-15-bff-compose-sample (PR cuioss/API-Sheriff#516, merge 053e3d51), inbox message plan-v02-15-bff-compose-sample-001 (landing residue).

RELATED: lessons-routing message api-sheriff-api-sheriff-0-2-0-052 (a different `fetch_findings` gap: review summaries stored without the inline comments).

## What happened

At the pre-merge barrier, `fetch_findings` re-filed a CodeRabbit review-summary body already handled in an earlier round (head 492b9888) as a new pending `pr-comment` finding stamped with the current HEAD. The plan resolved it by hand before the merge gate would pass. The dedup is keyed on the comment, and it did not recognise the review body as handled once the body was re-read at a new HEAD.

## Corrective rule (candidate)

Key the dedup of `review_body` and `review` kinds on the review id and body hash, not on the HEAD the fetch ran at. A body already answered in an earlier round must not return as a pending finding. Those kinds carry no resolvable thread, so a re-filed one can only be cleared by hand.
