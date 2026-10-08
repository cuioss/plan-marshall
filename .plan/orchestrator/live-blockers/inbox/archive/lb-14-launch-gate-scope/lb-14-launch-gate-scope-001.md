envelope_version=1
sender_type=plan
sender_id=lb-14-launch-gate-scope
epic=live-blockers
kind=candidate-lesson
created=2026-10-08T14:55:32Z

component=plan-marshall:phase-6-finalize
category=improvement

# Skip finalize step re-fires when the step declares no changed verdict inputs

## Context

In plan lb-14-launch-gate-scope the finalize steps `project:finalize-step-lessons-housekeeping` and `project:finalize-step-plugin-doctor` each fired 5 times (4 re-fires) because HEAD advanced after every self-review fix commit. Every firing returned the same verdict (0 removed, 0 promoted, 0 adapted, 56 retained; scoped doctor clean over the same 4 skill directories). The work log records the re-fire reasons as `verdict_inputs_undeclared` and `step declares no verdict_inputs`.

## Root cause

A step that declares no `verdict_inputs` is re-fired on any HEAD advance, so a loop-heavy finalize pays for ten identical dispatches. Boundary rows carry no step_id, so the cost can only be attributed by timing: six step_complete rows matching the first three firing pairs total 738K tokens, and the other four firings are unattributed.

## Proposed action

Have both steps declare `verdict_inputs` (the lesson corpus plus the declared files for housekeeping; the scoped skill directories for plugin-doctor) so the dispatcher skips the re-fire when none changed, and record the skipped re-fire in the step record.

## Evidence

- aspect: plan_efficiency - 6-finalize holds 58 percent of 7.92M tokens (a floor)
- aspect: llm_to_script_opportunities - ten identical dispatches, candidate 1
- aspect: log_analysis - 17 finalize dispatch rows, 10 step_complete
- aspect: execution_context_dispatch_audit - both steps classified dispatched
