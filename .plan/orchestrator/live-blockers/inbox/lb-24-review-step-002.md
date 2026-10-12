envelope_version=1
sender_type=plan
sender_id=lb-24-review-step
epic=live-blockers
kind=candidate-lesson
created=2026-10-10T11:57:36Z

component=plan-marshall:workflow-integration-github
category=bug

# Do not credit CodeRabbit's in-progress summary as a finished re-review

## Context

During the CodeRabbit quota recovery on PR #1742, `github_re_review re-review --escalated` returned `matched: true, head_sha_verified: true` 34 seconds after posting, because CodeRabbit had edited its summary comment to "review in progress" over the files at the head commit. No review existed yet. The same happened at head c6571e103: the matched comment was the "Currently processing new changes ... between 8fc4ed52 and c6571e10" state, verified after 35 seconds.

## Root cause

The head-verification test accepts any bot comment that names the head commit, and CodeRabbit's in-progress summary names the head as the end of the range it is about to review. A started review is read as a finished one.

## Proposed action

Classify CodeRabbit's in-progress summary (and any comment whose bot check-run is observed in progress) as not-yet-an-answer in the re-review matcher, so the await keeps polling. Add a fixture with the in-progress summary text and assert `matched: false` until the finished review lands.

## Evidence

- decision.log 2026-10-09T23:27:21Z: verb returned matched=true, head_sha_verified=true on the in-progress notice after 34 seconds
- decision.log 2026-10-10T09:25:01Z: re-review matched CodeRabbit's 'currently processing' summary as a head-verified fresh review
- automatic-review hand-back at c6571e103: matched comment still carried covered commit 8fc4ed52
