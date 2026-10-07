envelope_version=1
sender_type=orchestrator
sender_id=cui-http-quality-report-remediation
epic=truthful-signals
kind=candidate-lesson
created=2026-10-05T15:50:47Z

component=plan-marshall:phase-6-finalize
category=improvement

# Candidate lesson: CodeRabbit hourly review quota blocks the pre-merge barrier after rapid fix pushes

- Suggested component: plan-marshall:phase-6-finalize (pre-merge review barrier) / plan-marshall:manage-locks (review-bot rate window)
- Suggested category: improvement
- Signal source: automated review
- Evidence: decision log 045c11, "coderabbit participated_stale at 0697017 (last review 52c6e79, quota exhausted) ... barrier-ask-override granted". Decision log b8898f: "unproven_bots=[coderabbit refused_awaitable (quota)] under authorization barrier-ask-override".

## What happened

On this plan's tier, CodeRabbit allows 1 review per hour. After several fix pushes in quick succession, its last review was stale at the merge head and it refused new reviews because of the quota. The pre-merge participation barrier could not be met. PR #262 merged under an operator barrier-ask-override.

## Why it matters

When the bot quota is lower than the number of review loop-back rounds, the barrier is guaranteed to need an override. That makes the override routine.

## Suggested fix

- Batch fixes into fewer pushes when a quota-limited bot is in the barrier set. Or account for the bot's quota window in the review-bot rate-window claim before pushing.
- Let the barrier treat a quota refusal as its own state, with a bounded wait for the quota window, before it asks the operator.

## Routing

From cui-http epic `quality-report-remediation`, PLAN-13 (cuioss/cui-http #262), inbox message `plan-13-asciidoc-specs-requirements-adrs-005.md`. Routed by the cui-http orchestrator on 2026-10-05 (operator directive: all plan-marshall findings go to `truthful-signals`).
