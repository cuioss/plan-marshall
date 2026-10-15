envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T11:06:08Z

# Hold the 3-outline to 4-plan transition until q-gate validation passes

Component: plan-marshall:phase-3-outline (category: bug, confidence: high)

## Context

In scenario-replay-harness the outline phase self-transitioned to 4-plan at 07:59 while its Q-Gate validation was
still owed. The q-gate-validation dispatch then found two warnings (338c41, fc4618) and noted it was activated for
3-outline while status already said 4-plan. To fix them the phase was rolled back 4-plan -> 3-outline at 08:06 and
the outline re-dispatched; that re-dispatch's usage (109134 tokens, 66 tool uses) landed after the 3-outline
boundary had been stamped and is not counted in either phase. 4-plan carries 12m11s of idle time from this.

## Root cause

phase-3-outline transitions on its own return even when `qgate_validation_required=true`, so a failing validation
can only be answered with a backward transition.

## Proposed action

When `qgate_validation_required` is true, leave the phase at 3-outline and let the orchestrator transition only after
q-gate-validation returns clean (or after the fix re-dispatch), so the metrics boundary covers the fix work.

## Evidence

- aspect: chat_history_analysis — q-gate agent note on activation_context 3-outline vs current_phase 4-plan
- aspect: invariant_summary — task_state_hash drift 3-outline -> 4-plan
- work.log 07:59:13 self-transition, 08:06:54 Phase 4-plan -> 3-outline, 08:10:09 usage not folded

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `scenario-replay-harness-014.md` from plan scenario-replay-harness (PLAN-22, #50; Claude Code)
