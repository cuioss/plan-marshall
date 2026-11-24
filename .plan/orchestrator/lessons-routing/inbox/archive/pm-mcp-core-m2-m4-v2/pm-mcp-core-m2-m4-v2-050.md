envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4-v2
epic=lessons-routing
kind=candidate-lesson
created=2026-11-21T09:47:10Z

component=plan-marshall:phase-6-finalize
category=improvement
created=2026-11-21
bundle=plan-marshall
title=Seed review authors with the deterministic sets they are graded against

# Seed review authors with the deterministic sets they are graded against

## Context

In this plan's finalize, review rounds were re-run for omissions a script could have caught: two code-review author rounds loaded only 4 of the 20 `rule_sources` skills and were re-run against the full rulebook, and one functional-review author listed 7 unrequested changes while `reconcile-scope` reported 11, so the verifier refused and the round was resealed. Functional review fired 9 times and code review 6 times.

## Root cause

The author collects the skill set and the unrequested-change set by hand; nothing compares them with `rule_sources` or `reconcile-scope` before the verifier runs.

## Proposed action

Before validation, have the review dispatcher check the author's reported skills against `rule_sources` and pre-fill the verdict's `unrequested_changes` rows from `reconcile-scope` `c_not_a`, so the author grades each row and a partial load is refused at once.

## Evidence

- aspect: chat_history_analysis - "4 earlier, the other 16 this pass"; verifier "Unrequested list is incomplete: reconcile-scope shows 11 undeclared files, only 7 entered"
- aspect: llm_to_script_opportunities - two low-complexity candidates
- aspect: plan_efficiency - 6-finalize 6.9M tokens, 68% of the plan
