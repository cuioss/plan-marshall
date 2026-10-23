envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-19T17:28:51Z

# Do not escalate an optional bot's budget decline to an operator prompt

- Source: plan-retrospective (chat-history-analysis, automatic-review returns)
- Plan: plan-37-ported-primitive-tests (pm-mcp-core)
- Candidate component: plan-marshall:automatic-review
- Category: improvement
- Confidence: high

## Context

On PR #106 the optional bot sourcery posted an account review-budget notice twice. The first time, `fetch_findings` filed it as an ordinary pr-comment finding (refused_bots was empty), so it went through unified triage. On the loop-back re-review, trigger B classified the same notice as a decline and routed it into the timeout sub-block; with `re_review_on_timeout: ask` that produced `escalate_ask` and an operator prompt, although both required bots (cuioss-review-bot, coderabbit) were satisfied at the HEAD and sourcery's gap had already been accepted for this PR.

## Root cause

The re-review timeout sub-block does not exempt optional bots, and the sourcery refusal pattern does not match the budget notice, so the same non-gating event is handled two different ways and one of them stops the run for the operator.

## Proposed action

Treat an optional bot's decline or budget notice as non-gating in the trigger-B sub-block (record it as a known coverage gap, no ask), and extend the sourcery refusal pattern so `fetch_findings` classifies the budget notice as a refusal instead of filing a finding.

## Evidence

- aspect: chat-history-analysis -- operator answered "Merge anyway - proceed unreviewed" to a prompt caused by sourcery alone
- automatic-review return (iteration 1): "Sourcery's refusal notice was not classified as a refusal by the producer"
- re-review return: status escalate_ask, declined_bots sourcery, both required bots satisfied
