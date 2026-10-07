envelope_version=1
sender_type=plan
sender_id=orchestrator-land-verbs
epic=orchestrator-refactor
kind=candidate-lesson
created=2026-10-03T17:43:25Z

component=plan-marshall:phase-5-execute
category=anti-pattern

# Quote the get-deliverable flag verbatim in the execute workflow

## Context

`manage-solution-outline get-deliverable` was rejected by argparse 4 times in orchestrator-land-verbs (first at 2026-10-03T05:04:43Z, exit 2). The TASK-11 leaf reports the cause: it passed `--number`, while the declared flag is `--deliverable-number`; it logged the failure and retried.

## Root cause

The execute-side workflow text names the deliverable read by intent rather than by its canonical invocation, so leaves paraphrase the flag.

## Proposed action

Recurrence of active lesson 2026-10-02-21-002 — merge into it. Its fix (name the canonical `get-deliverable --plan-id P --deliverable-number N` call in the execute workflow) has not landed; this plan adds 4 more occurrences.

## Evidence

- aspect: script_failure_analysis — argparse_other, `get-deliverable`, occurrence_count 4
- aspect: chat_history_analysis — TASK-11 hand-back: "`get-deliverable --number`, correct is `--deliverable-number`"
