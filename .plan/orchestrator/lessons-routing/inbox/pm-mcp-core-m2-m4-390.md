envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-19T18:47:10Z

component=plan-marshall:phase-5-execute
category=improvement

# Log execute-time operator decisions to decision.log and re-sync the outline

Source: plan-retrospective of plan-70-plan-instance-alignment (aspects logging-gap-analysis, request-result-alignment, chat-history-analysis).

## Context

After envelope 2 the operator answered two scope questions mid-execute: allow empty lists in call values (grammar, parser, ADR workflow-dsl/006) and make the engine settle a pruned merge gate (WorkflowValidator, VerificationRule, ADR workflow-plan/016). They became TASK-17..20. Neither answer has a decision-log entry; only the TASK-19 pull-forward (c0961a) was logged, so the functional review had to reconstruct both from task text and ADRs. The outline was not re-synced either, and the 20 resulting undeclared files later surfaced as a scope-creep warning.

## Root cause

The execute hand-back path that turns an operator answer into new tasks has no step that records the decision or refreshes the declared footprint.

## Proposed action

When the orchestrator turns an execute-phase operator answer into new tasks, log one `[DECISION]` entry per answer (question, choice, tasks created) and append the newly touched files to the owning deliverable's declared set (or the references affected_files) in the same step.

## Evidence

- logging-gap-analysis: 0 decision entries for the two execute-time operator decisions
- request-result-alignment: 20 realized-but-undeclared files, several from those decisions
- chat-history-analysis: operator answers "Allow empty lists now" and "Make the engine support it"
