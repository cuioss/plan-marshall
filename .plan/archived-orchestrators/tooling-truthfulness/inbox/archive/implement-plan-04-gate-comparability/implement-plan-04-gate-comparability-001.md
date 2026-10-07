envelope_version=1
sender_type=plan
sender_id=implement-plan-04-gate-comparability
epic=tooling-truthfulness
kind=candidate-lesson
created=2026-09-12T10:45:13Z

# Surface canonical script forms at call time to stop invented-flag drift

## Context

The implement-plan-04-gate-comparability retrospective recorded 5 argparse rejections (exit 2) in the plan's script-execution log: an invented flag on `architecture find` (2 occurrences), an invented `--plan-id` on `github_pr bot_completion`, a router-scoped `--plan-id` placement rejection on `ci`, and an argparse rejection on `manage-solution-outline get-deliverable`. (A sixth rejection in the window was the retrospective's own exploratory `--output-file` probe, excluded from this count.)

## Root cause

The canonical-forms table (persona-plan-marshall-agent argument-naming) already names every legal verb and flag, but callers do not consult it at call time — the same invented-verb/flag drift recurs across components.

## Proposed action

Surface the canonical invocation (or a `--help` pre-check reminder) at the call site — e.g. a pre-dispatch lint or a prompt-level reminder quoting the canonical-forms entry — so invented flags fail before execution rather than as exit-2 rejections in the log.

## Evidence

- aspect: script_failure_analysis — 5 findings across 4 components, all exit_code 2, occurrence counts 2/1/1/1
- component: plan-marshall:persona-plan-marshall-agent
- category: improvement
- confidence: medium
- plan: implement-plan-04-gate-comparability
