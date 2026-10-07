envelope_version=1
sender_type=orchestrator
sender_id=cui-http-quality-report-remediation
epic=truthful-signals
kind=candidate-lesson
created=2026-10-05T07:59:07Z

component=plan-marshall:workflow-integration-github
category=bug

# Pre-merge re-fetch files a bot's in-place-edited "no issues" summary as a new pending pr-comment

## Source

- Plan: plan-12-javadoc-samples-and-api-prose (PR #260)
- Signal: observed by the orchestrator during the pre-merge barrier; confirmed against this plan's pr-comment store
- Evidence: findings 1843a7 and e2cf70 have the same `comment_id` (`IC_kwDOPwSbp88AAAABZP8fUA`,
  cuioss-review-bot issue_comment) but different `edit_term` values (06:36:50Z vs 07:23:31Z) and
  different `reviewed_commit_sha` values (d91fc7a vs c2e67d1)

## What happened

cuioss-review-bot edits its "PR Reviewer Guide" summary comment in place on each new push
("Review updated until commit ..."). The pre-merge barrier re-fetch keyed the comment on
(`comment_id`, `edit_term`), saw a new edit term, and filed a second pending pr-comment finding.
The comment still said "no relevant tests / no security concerns / no major issues", and the first
copy (1843a7) was already resolved `accepted`. The new pending finding blocked the merge until it
was resolved by hand.

## Why it matters

Any review bot that keeps one summary comment and edits it per push re-blocks the merge gate after
every push. The extra finding carries no new actionable content, so the block is pure friction.
Resolving these by hand also trains operators to skim pr-comment findings.

## Suggested correction

When a re-fetched comment has the same `comment_id` as an already-resolved finding, carry the prior
resolution forward if the bot's verdict did not change. The verdict here is the informational,
non-actionable summary, recognised by the same kind/author classification used for the first copy.
At minimum, auto-accept an edited issue_comment summary from a configured review bot that reports
no issues, rather than filing it as a fresh pending finding.

## Routing

From cui-http epic `quality-report-remediation`, PLAN-12 (cuioss/cui-http #260), inbox message `plan-12-javadoc-samples-and-api-prose-005.md`. Routed by the cui-http orchestrator on 2026-10-05.
