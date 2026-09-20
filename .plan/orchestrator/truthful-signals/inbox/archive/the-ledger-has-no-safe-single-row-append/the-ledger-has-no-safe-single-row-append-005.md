envelope_version=1
sender_type=plan
sender_id=the-ledger-has-no-safe-single-row-append
epic=truthful-signals
kind=candidate-lesson
created=2026-09-07T08:07:19Z

component=plan-marshall:workflow-integration-github
category=bug
confidence=high

# Verify a body-published reviewed SHA on the issue_comment path

## Context

`cuioss-review-bot` publishes the commit it reviewed in the BODY of its PR Reviewer Guide comment, as the line "Review updated until commit <sha>". It does not populate a structured reviewed-commit field, because its participation arrives as an `issue_comment` rather than as a review object.

`github_re_review.py` calls `_references_head_sha` exactly once, at line 571, inside the review branch and against `review['commit_sha']`. The `issue_comment` branch (lines 363, 617) never calls it. The consequence is that a re-review by this bot can never reach `head_sha_verified: true`, and is therefore disposed as declined on every cycle.

This is not undocumented — `workflow-integration-github/SKILL.md` line 39 records the resulting state as "`matched_signal: issue_comment` with `head_sha_verified: false`". The symptom is documented; the gap is not closed.

## Root cause

SHA verification was attached to the review path only, on the implicit assumption that reviewed-commit evidence always arrives as a structured field. A bot whose evidence is in prose is structurally unverifiable, so the correct outcome (it did review this head) is unreachable rather than merely unproven.

## Proposed action

Apply `_references_head_sha` to the matched comment BODY on the `issue_comment` path as well, so a bot that names its reviewed SHA in prose can reach `head_sha_verified: true`. Keep the field/prose distinction visible in the returned record, so a caller can tell a structured verification from a body-derived one.

## Evidence

- marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_re_review.py — `_references_head_sha` defined at line 203, called only at line 571 inside the review branch; the `issue_comment` branch at lines 363 and 617 does not call it. Verified against HEAD.
- decision.log 2026-09-07T06:12:45Z — "re-review (trigger B) ... returned matched=true head_sha_verified=false (matched_signal=issue_comment). DIVERGENCE: head_sha_verified is false because the issue_comment path carries no reviewed-commit evidence FIELD, but the matched comment BODY names the commit verbatim - 'Review updated until commit .../bae20a4a43b228745df43f14ed8db3daf5704889'."
- The run had to override the disposition by hand and defer to the producer currency test instead.
