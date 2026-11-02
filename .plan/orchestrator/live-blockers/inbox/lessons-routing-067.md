envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-11-02T10:27:10Z

# Review-bot findings are lost or hidden before triage: long bodies are cut at 8,000 characters ahead of the request, and a re-review's inline comments are never fetched

Severity: **high (operator ruling, 2026-11-02 sweep)** against a medium default. Bundle: `plan-marshall` (`workflow-integration-github` `fetch_findings`; pr-comment promotion / `untrusted-ingestion` body cap).

## Sources (API-Sheriff epic api-sheriff-0-2-0)

- `lessons-routing-013`: plan-v02-09-token-sheriff-integration-fidelity, PR cuioss/API-Sheriff#530 (plugin 0.1.2021)
- `api-sheriff-api-sheriff-0-2-0-044`: plan-v02-45-request-body-and-h2-buffer-bounds, PR #506
- `api-sheriff-api-sheriff-0-2-0-052`: plan-v02-22-demo-client-and-doc-leftovers, PR #512

## Observation

1. **Truncation hides the request.** A 36,938-character CodeRabbit comment was cut to 8,000 characters at pr-comment promotion (#530); the change request came after the cut and survived only in `raw_input`. On #506 a stored inline body ends mid-quote; the cut removed the conclusion of a real defect (a callback writing RoutingContext data from the wrong event loop), which triage reconstructed from the code. CodeRabbit writes its analysis transcript before its conclusion, so a head-keeping cut removes exactly the substantive part. Nothing marks the body as truncated.
2. **Re-review inline comments dropped.** On #512 `github_pr fetch_findings` stored only the review summaries of CodeRabbit's re-reviews of later heads (64db644, f7ffa02), not the four inline comments they posted. The threads were answered on the PR by hand, outside the findings ledger.

## Ground truth (c431a8193)

- The literal 8000 cap was located in `untrusted-ingestion` `validate_struct.py`; the path from fetch to promoted `body` was **not traced end to end**.
- The `fetch_findings` paging / per-review dedup cause for (2) is **unverified** — single occurrence.

## What to consider

- Flag a body that hits the cap as truncated (flag + original length), and keep the tail (or head+tail) for CodeRabbit bodies, or extract the actionable section before cutting. Until then, triage reads `raw_input` / the PR comment whenever a body is at the cap.
- Check whether `fetch_findings` pages or dedups review comments by review id; add a case with two reviews on one PR where the second carries inline comments.
