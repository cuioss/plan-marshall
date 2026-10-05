envelope_version=1
sender_type=orchestrator
sender_id=cui-http-quality-report-remediation
epic=truthful-signals
kind=candidate-lesson
created=2026-10-05T15:50:46Z

component=plan-marshall:workflow-integration-github
category=bug

# Candidate lesson: github re-review matcher ignores the requested bot's author

- Suggested component: plan-marshall:workflow-integration-github (github_re_review)
- Suggested category: bug
- Signal source: automated review (PR #262)
- Evidence: orchestrator observation during the PR #262 review loop. Not recorded as a distinct line in the plan work/decision logs; the decision log shows the barrier tracked coderabbit and cuioss-review-bot separately (decision 045c11), which is the context the mismatch occurred in.

## What happened

`github_re_review re-review --bot-kind cuioss-review-bot` returned `matched: true`, but `matched_review.user` was `coderabbitai[bot]`. A CodeRabbit review satisfied a re-review request that was scoped to cuioss-review-bot.

## Why it matters

A wrong match tells the caller that the requested bot has re-reviewed when it has not. The pre-merge participation barrier then reads a different bot's review as fresh for the requested bot.

## Suggested fix

The re-review matcher should filter candidate reviews by the requested bot kind's `author_login` before it reports `matched: true`. Add a test with two bots reviewing the same head, where only the non-requested bot has a fresh review.

## Routing

From cui-http epic `quality-report-remediation`, PLAN-13 (cuioss/cui-http #262), inbox message `plan-13-asciidoc-specs-requirements-adrs-001.md`. Routed by the cui-http orchestrator on 2026-10-05 (operator directive: all plan-marshall findings go to `truthful-signals`).
