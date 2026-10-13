envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T07:34:07Z

# Candidate lesson: sourcery review-budget notice not recognised as a refusal

Source: run event in plan verify-not-resolve (PR #43), automatic-review step.

## What happened

Sourcery posted a notice that it had "used its review budget". The sourcery `refusal_patterns` did not match that notice, so the pipeline treated it as ordinary review content: it was filed as pr-comment findings and also counted as a re-review decline.

## Why it matters

A bot that declines to review because of a quota is a refusal state, not review feedback. Filing it as findings creates triage noise, and reading it as a re-review decline misstates the bot's completion state at the merge gate.

## Suggested correction

Add the review-budget / quota-exhausted wording to the sourcery `refusal_patterns` (owning component likely `plan-marshall:workflow-integration-github` bot profile or `plan-marshall:automatic-review`), with a fixture of the real notice text, so the notice is classified as a refusal and filed as no finding.

Classification is left to the orchestrator.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `verify-not-resolve-001.md` from plan verify-not-resolve (PLAN-18, #43; Claude Code)
