envelope_version=1
sender_type=plan
sender_id=lb-22-finalize-loop-control
epic=live-blockers
kind=candidate-lesson
created=2026-10-08T20:57:09Z

component=plan-marshall:workflow-integration-github
category=improvement
source_plan=lb-22-finalize-loop-control
confidence=high

# Filter bot acknowledgements of our own re-review trigger out of pr-comment findings

## Context

The workflow posts `@coderabbitai review` to request a re-review after a fix commit. When CodeRabbit has already reviewed that commit on its own, it answers the trigger with a short status comment ("Action not completed - Already reviewed the last commit"). `fetch_findings` stored that reply as a pending `pr-comment` finding - twice in this plan (`573a81` at head `57c5c8be3`, `c1ca5f` at head `f42bd6b85`).

A pending `pr-comment` finding blocks the pre-merge barrier, so each one needed a full unified-triage hand-off to be accepted, and the triage step then posted a reply to the PR for it. The reply carries no file, no line and no requested change.

## Root cause

The fetch already skips the workflow's own trigger comments (counted as `own-trigger`) and several noise classes, but not the bot's answer to such a trigger. The answer is authored by the bot, so it passes the author filter and is treated as review feedback.

## Proposed action

- Add a per-bot acknowledgement pattern to the review-bot registry (for CodeRabbit: the "Already reviewed the last commit" status reply) and have `fetch_findings` count matches under their own skip class, beside `own-trigger`.
- Longer term, avoid the trigger when the bot's latest review already names the current head: the first pass here confirmed `head_sha_verified: true` from CodeRabbit's own summary comment before the reply arrived.

## Evidence

- aspect: chat_history_analysis - automatic-review hand-backs for both passes describe the finding as "a command reply, not code feedback"; the triage hand-back for `573a81` reports "ACCEPT ... names no file, line or change" and one posted PR comment.
- fetch counts on the third pass: 17 fetched, 7 noise, 2 duplicate, 1 refusal, 2 self-response, 4 own-trigger, 1 stored - the one stored record is the acknowledgement.
- review retrospective: coderabbitai row shows 4 raw comments of which 3 are meta.
