envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-11-07T14:28:23Z

component=plan-marshall:manage-metrics
category=bug
source_plan=pm-mcp-core:plan-v2-98-optional-conversion-workflow
bundle_version_at_run=0.1.2041

# Accept verification_handback in record-dispatch-boundary on every shipped bundle

## Context

During phase 5-execute of pm-mcp-core PLAN-V2-98, two execution leaves returned the prescribed orchestrator-tier build hand-back (`verification_handback: true` with non-empty `pending_verify_steps[]`). The orchestrator tried to record the dispatch boundary with `--termination-cause verification_handback`; `record-dispatch-boundary` rejected it with an argparse error (script log, 2026-11-06T14:58:27Z, exit 2). The boundary rows were then written as `agent_returned` and `error` instead.

## Root cause

The installed bundle at run time (0.1.2041) did not carry `verification_handback` in `DISPATCH_TERMINATION_CAUSES`, while the execution workflow already prescribed the hand-back and its own classification row. The current SKILL.md (0.1.2064+) lists the value, so this may already be fixed; the gap is that the workflow and the recorder shipped out of step.

## Proposed action

Confirm `verification_handback` is in the tuple and the argparse choices of the current release. Add a contract test that every termination cause named in `plan-marshall/workflow/execution.md` is accepted by `record-dispatch-boundary`, so the workflow cannot prescribe a cause the recorder refuses. If already fixed, close as already_closed.

## Evidence

- aspect: script-failure-analysis - `manage-metrics record-dispatch-boundary` argparse rejection at 2026-11-06T14:58:27Z
- aspect: logging-gap-analysis - 5-execute boundary ledger shows 3 agent_returned + 1 error, 0 verification_handback, although two leaves returned verification_handback: true
- operator report at finalize
