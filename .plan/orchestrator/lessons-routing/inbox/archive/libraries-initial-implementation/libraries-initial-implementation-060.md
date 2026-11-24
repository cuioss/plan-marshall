envelope_version=1
sender_type=orchestrator
sender_id=libraries-initial-implementation
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:07:38Z

component=plan-marshall:platform-runtime
category=bug
title=chat extract-signal counts relayed subagent hand-backs and task notifications as operator turns
source_lesson=2026-11-23-12-006
source_repo=git-document-repository (epic libraries-initial-implementation)
source_created=2026-11-23

# chat extract-signal counts relayed subagent hand-backs and task notifications as operator turns

# Candidate lesson: chat extract-signal counts relayed subagent hand-backs and task notifications as operator turns

- Source signal: plan-retrospective of plan-23-forms-hardening (inbox plan-23-forms-hardening-014; chat_history_analysis aspect).

## What happened

For session 4365e558 `chat extract-signal` returned `operator_turn_count: 25` and `kept_raw_count: 25`. Every one of those user-role turns is a harness-relayed subagent hand-back ("Another Claude session sent a message: <agent-message ...> [Subagent hand-back]") or a background-task notification, not text the operator typed; the only operator-authored signal is the 10 recovered gate decisions (`gate_decision_count: 10`).

## Candidate rule

Exclude user-role turns whose body is an `<agent-message>` subagent hand-back or a `[SYSTEM NOTIFICATION - NOT USER INPUT]` task notification from `operator_turn_count`, and keep them, if at all, under a separate agent-relay counter, so `no_signal` and the chat-history aspect read true operator signal. Owning component: `plan-marshall:platform-runtime`.
