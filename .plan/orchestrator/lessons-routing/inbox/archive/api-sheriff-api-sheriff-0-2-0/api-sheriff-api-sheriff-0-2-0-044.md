envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=candidate-lesson
created=2026-10-22T05:50:09Z

# Candidate lesson: Long review-bot comment bodies are cut at ingest, and CodeRabbit puts the conclusion last (review-comment ingestion)

Forwarded from API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-45-request-body-and-h2-buffer-bounds (PR cuioss/API-Sheriff#506), source message 013.

On PR #506 the stored body of a CodeRabbit inline comment ends mid-way through a quoted documentation excerpt, consistent with the ingest length limit on review-bot bodies (8000 characters). CodeRabbit writes its analysis transcript ahead of the conclusion, so in a long comment the cut removes exactly the substantive part. The finding was real (a callback writing RoutingContext data from the wrong event loop); triage had to reconstruct it from the visible head and the code.

Candidate rules:
- mark an ingested body that hits the length limit as truncated in the payload, so triage knows;
- on a truncated body, the triage step reads the full comment on the PR (via the CI abstraction) before deciding the disposition;
- consider keeping the tail rather than the head for CodeRabbit bodies, or both.
