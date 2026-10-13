envelope_version=1
sender_type=plan
sender_id=lb-25-phase-and-merge-gates
epic=live-blockers
kind=candidate-lesson
created=2026-10-11T16:01:24Z

component=plan-marshall:manage-architecture
category=improvement
bundle=plan-marshall
source_plan=lb-25-phase-and-merge-gates

# Stop module-tests execution tier oscillating within one plan

## Context

In 5-execute of lb-25-phase-and-merge-gates, `module-tests plan-marshall` first resolved `per_task` and ran in 243-256s. One run then timed out at its learned 333s budget with no verdict; the next resolve returned `execution_tier: orchestrator` with a 762s budget, and three successive envelopes (TASK-13, TASK-14, TASK-16) yielded `voluntary_checkpoint` hand-backs to the orchestrator. Envelope 4 then resolved the same command `per_task` (567s) and ran it inline. Envelope 2 also had to split `verify` into its halves for the same reason. The operator asked "did you stop?" during this stretch.

## Root cause

The learned timeout budget feeds the tier decision directly, so one slow run flips the tier, and the next fast-enough estimate flips it back; nothing damps the oscillation within a plan.

## Proposed action

Apply hysteresis to the tier decision within a plan (once orchestrator-tier, stay there unless several runs come in well under the ceiling), or separate a timeout from a tier signal so a single killed run raises the budget without forcing a hand-back. Report the tier history in the build verdict so a leaf can tell a flip from a stable decision.

## Evidence

- aspect: chat_history_analysis - "TASK-13's scoped module-tests plan-marshall timed out at 333s with no verdict ... A fresh resolve returns execution_tier: orchestrator with a 762s budget, so I yielded"
- aspect: chat_history_analysis - envelope 4: "module-tests plan-marshall resolved live as per_task (567s), not orchestrator-tier, so I ran it here"
- aspect: logging_gap_analysis - 4 of 10 5-execute dispatch boundaries are voluntary_checkpoint, all orchestrator-tier build hand-backs
