envelope_version=1
sender_type=plan
sender_id=lb-25-phase-and-merge-gates
epic=live-blockers
kind=candidate-lesson
created=2026-10-11T16:01:16Z

component=plan-marshall:workflow-integration-github
category=bug
bundle=plan-marshall
source_plan=lb-25-phase-and-merge-gates

# Check the review author in await_fresh_review before crediting a re-review

## Context

In the third automatic-review pass of lb-25-phase-and-merge-gates (HEAD 320a1b7), the re-review wait for `cuioss-review-bot` returned `matched: true, head_sha_verified: true`. The matched object was a review written by `coderabbitai[bot]` (submitted 15:04:17Z, commit 320a1b7, empty body), not anything cuioss-review-bot posted. The later FIND credited cuioss-review-bot through its own issue comment, so the guard verdict happened to hold, but the "verified" re-review was not evidence that the awaited bot reviewed.

## Root cause

`github_re_review` `await_fresh_review` matches a fresh review on commit and timing without checking that the review's author is the bot being awaited.

## Proposed action

Filter candidate reviews and comments by the awaited bot's registered login(s) before declaring a match, and add a test where a different bot's review lands on the awaited commit first.

## Evidence

- aspect: chat_history_analysis - automatic-review leaf: "The cuioss-review-bot re-review was matched on a review object written by coderabbitai[bot] ... The review match apparently does not check the author against the bot being awaited"
