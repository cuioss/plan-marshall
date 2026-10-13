envelope_version=1
sender_type=plan
sender_id=lb-33-leaf-test-scope-and-executor
epic=live-blockers
kind=candidate-lesson
created=2026-10-10T19:57:34Z

component=plan-marshall:workflow-integration-github
category=bug
confidence=high
source_aspects=chat_history_analysis,llm_to_script_opportunities

# Exclude the operator's own full-review trigger from pr-comment findings

## Context

On PR #1745, every automatic-review pass after a manual `@coderabbitai full review` trigger filed that operator comment as a `pr-comment` finding (8ef608, 59e7b9, 069e61), plus CodeRabbit's "Full review finished" acknowledgement (46a121, dca531, e66a98). Each unified triage round then had to close both as `taken_into_account` with no reply. This happened in 4 consecutive triage rounds.

## Root cause

The own-trigger exclusion in `fetch_findings` matches only the literal `@coderabbitai review`, so the `full review` variant falls through as a human-authored finding with no bot attached. The acknowledgement reply has no noise classification.

## Proposed action

Widen the own-trigger exclusion to every `@coderabbitai {review|full review}` comment by the operator or the plan's own identity, and classify the bot's "Full review finished" acknowledgement as noise, with a regression test for both forms.

## Evidence

- aspect: chat_history_analysis — automatic-review leaves at c7f65b0e2, 94c3cba2e and e91623235 each report the own trigger was "filed as a finding, not excluded as an own trigger: the exclusion only matched `@coderabbitai review`"
- aspect: llm_to_script_opportunities — trigger/ack triage repeated 4 times with a deterministic answer
