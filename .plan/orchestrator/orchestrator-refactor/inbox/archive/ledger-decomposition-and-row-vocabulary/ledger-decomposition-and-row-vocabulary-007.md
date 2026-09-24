envelope_version=1
sender_type=plan
sender_id=ledger-decomposition-and-row-vocabulary
epic=orchestrator-refactor
kind=candidate-lesson
created=2026-09-24T09:05:12Z

# Recurrence: transition mailbox probe misreports not_orchestrated

component: plan-marshall:manage-status
category: bug

## Context

In ledger-decomposition-and-row-vocabulary, an orchestrated plan launched from epic orchestrator-refactor's staged spec PLAN-02, the manage-status transition mailbox probe reported `not_orchestrated`. The finalize dispatcher resolved the plan as `orchestrated: true, epic: orchestrator-refactor`. So two readers of the same plan disagree about whether it is orchestrated.

## Root cause

This recurs lesson 2026-09-23-15-001. The transition-time probe uses a different orchestration test than the `request.md source_id` + `orchestrator inbox detect` seam that phase-6-finalize uses.

## Proposed action

Merge this into lesson 2026-09-23-15-001 as a recurrence. Route the transition mailbox probe through the same two-call seam (`manage-plan-documents request read --section source_id`, then `orchestrator inbox detect --source-id`) rather than a third detector.

## Evidence

- dispatcher run facts — "the manage-status transition mailbox probe misreports not_orchestrated (lesson 2026-09-23-15-001)"
- request.md source_id: .plan/orchestrator/orchestrator-refactor/plans/PLAN-02-ledger-decomposition-and-row-vocabulary.md
