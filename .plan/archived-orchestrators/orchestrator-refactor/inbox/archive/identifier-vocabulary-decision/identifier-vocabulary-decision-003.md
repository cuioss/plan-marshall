envelope_version=1
sender_type=plan
sender_id=identifier-vocabulary-decision
epic=orchestrator-refactor
kind=candidate-lesson
created=2026-09-20T08:24:45Z

component=plan-marshall:manage-execution-manifest
category=bug
title=Reconcile orchestration detection between manifest compose and finalize dispatch

# Reconcile orchestration detection between manifest compose and finalize dispatch

## Context

Two surfaces disagree about whether this plan is orchestrated. At manifest-compose time the decision log recorded: `terminal_emission_orchestration_gate — dropped emit-landing from phase_6.steps: plan is not orchestrated (detection=not_orchestrator_pointer); no epic inbox to write a landing to`. The plan's `request.md` carries `source: description` and has no `source_id` section at all, so the pointer-based detector is answering correctly on the evidence it reads. Yet the plan demonstrably belongs to epic `orchestrator-refactor`: it wrote a message to that epic's inbox during execute, and the finalize dispatcher handed this retrospective `orchestrated: true` with `epic: orchestrator-refactor`.

The consequence is measurable rather than cosmetic. `orchestrator inbox list --slug orchestrator-refactor` reports `queue_reconciliation.queue_count: 7`, `landing_count: 0`, `queue_without_landing_count: 7` — PLAN-01 through PLAN-07, none with a landing. PLAN-04 landed as PR #1543 (merge commit `4804b6976`) and the epic ledger has no way to know it.

## Root cause

Orchestration membership is detected from the request document's `source_id` pointer, but a plan can be launched into an epic without that pointer ever being written, and no second detector reconciles the two. Because `emit-landing` is dropped at compose time, the omission is permanent for that plan's whole lifecycle — there is no later point at which the landing can still be emitted.

## Proposed action

Make the two detections agree, or make the compose-time gate fail loudly when they cannot. Either write `source_id` when a plan is launched from a staged epic plan, or have the terminal-emission gate consult the same signal the finalize dispatcher uses before dropping `emit-landing`. A plan whose retrospective is dispatched with `orchestrated: true` must not have had its landing step pruned as un-orchestrated.

## Evidence

- aspect: manifest_decisions — compose decision log entry `7f9799`, `detection=not_orchestrator_pointer`
- aspect: request_result_alignment — `request read --section source_id` returns `section_not_found`; the document carries `source: description`
- dispatch input — this retrospective was invoked with `orchestrated: true`, `epic: orchestrator-refactor`
- `orchestrator inbox list --slug orchestrator-refactor` — `queue_without_landing_count: 7`, `landing_count: 0`
