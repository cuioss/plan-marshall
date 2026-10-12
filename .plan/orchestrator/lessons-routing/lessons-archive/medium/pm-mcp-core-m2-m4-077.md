envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-11T16:59:13Z

# Keep the orchestrator loop running after a subagent hand-back

**Signal source**: plan-retrospective (chat-history-analysis, plan-efficiency), finalize step of workflow-dsl-parser-and-ast.

**Component (suggested)**: `plan-marshall:plan-marshall` (main-context orchestrator loop)

**Category (suggested)**: bug

## Context

During this plan the operator had to nudge the main context seven times ("did you stop?" five times, "status?" twice) before the next step ran. Each nudge followed a subagent hand-back whose return said what the orchestrator had to do next (re-dispatch the next envelope, run the Q-Gate, dispatch finalize). The plan's idle time is 18h33m against 2h43m worked; part of that is overnight, but each nudge is a stall the operator had to notice by hand.

## Root cause

After receiving a leaf's return TOON, the orchestrator ends its turn instead of reading the return's next-step signal and continuing. Nothing in the loop asserts "a non-terminal return means dispatch the next step in the same turn".

## Proposed action

In the plan-marshall orchestrator workflow, make continuation explicit: after every leaf return that is not terminal (`success` with remaining work, `loop_back`, `budget_yield`, `qgate_validation_required: true`), route straight to the next dispatch in the same turn, and only end the turn on a terminal state, an operator prompt, or a declared wait. Consider a work-log `[STATUS]` line when the orchestrator yields without a terminal state, so a retrospective can count stalls.

## Evidence

- aspect: chat_history_analysis — operator turns "did you stop?" (5x) and "status?" (2x), each right after a subagent hand-back that named the next orchestrator action
- aspect: plan_efficiency — idle 18h33m vs worked 2h43m; 5-execute wall 18h35m vs worked 1h51m
- Not covered by lessons-capture messages 001-013 (002 is about leaves self-transitioning phases, a different defect)

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `workflow-dsl-parser-and-ast-014.md` from plan workflow-dsl-parser-and-ast (PLAN-07, #27)
