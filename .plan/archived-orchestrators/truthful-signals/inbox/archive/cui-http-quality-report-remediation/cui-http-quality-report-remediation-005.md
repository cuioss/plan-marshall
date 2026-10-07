envelope_version=1
sender_type=orchestrator
sender_id=cui-http-quality-report-remediation
epic=truthful-signals
kind=candidate-lesson
created=2026-10-05T07:59:05Z

component=plan-marshall:automatic-review
category=bug

# Candidate lesson: non-existent notation `github_pr review_completeness` used for the review-completeness check

**Source signal**: script failure (unknown notation) observed by the finalize orchestrator during the automatic-review rounds (reported by the dispatcher).
**Component**: plan-marshall:automatic-review (review_completeness script) and whichever doc or prompt produced the wrong notation.

## What happened

A call was attempted with the notation `github_pr review_completeness`, which does not exist. The correct invocation is `plan-marshall:automatic-review:review_completeness check`.

## Candidate rule

Invented-notation class: quote the executor notation verbatim from the owning skill's canonical-invocation block. If a doc or dispatch prompt still names `github_pr` for review completeness, it is stale and should be corrected to `plan-marshall:automatic-review:review_completeness check`.

## Classification hint

Marketplace doc/prompt drift (plan-marshall bundle); recurrence signature "never invent script subcommands".

## Routing

From cui-http epic `quality-report-remediation`, PLAN-10 (#256); previously lesson 2026-10-04-06-005. Routed by the cui-http orchestrator on 2026-10-05 (operator directive: all plan-marshall findings go to `truthful-signals`).
