envelope_version=1
sender_type=plan
sender_id=implement-plan-08-slug-semantics-model-compliance
epic=tooling-truthfulness
kind=candidate-lesson
created=2026-09-14T08:09:40Z

# Router-scoped plan-id flag placed after the verb on ci checks

## Context

During finalize of implement-plan-08-slug-semantics-model-compliance, a single
`ci checks` call placed the router-scoped `--plan-id` flag after the verb and was
rejected with exit 2 (`unrecognized arguments`), because the ci router consumes that
flag only before the first verb token. The call was corrected and the run continued.

## Root cause

Caller habit carried over from body-consumer verbs (which declare `--plan-id` after
their own verb) onto a router-scoped flag position.

## Proposed action

No code change proposed from this single data point; recorded so the orchestrator can
weigh it against the existing argparse-rejection recurrence coverage in
persona-plan-marshall-agent standards.

## Evidence

- aspect: script_failure_analysis — invented_flag on plan-marshall:tools-integration-ci:ci checks at 2026-09-13T22:31:01Z, occurrence_count 1
