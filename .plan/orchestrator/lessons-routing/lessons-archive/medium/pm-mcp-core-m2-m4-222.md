envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T11:06:07Z

# Emit a DISPATCH line for loop-back re-fires of finalize steps

Component: plan-marshall:phase-6-finalize (category: bug, confidence: high)

## Context

In scenario-replay-harness the first firings of create-pr, automatic-review and sonar-roundtrip each logged a
`[DISPATCH]` line. After the review loop-back, sonar-roundtrip (09:56) and automatic-review (10:00, and again after the
escalate_ask answer) logged `Completed step` and `execution-context.* Complete` lines with no `[DISPATCH]` line. The
verification-feedback dispatch at 09:37:43 has a `[DISPATCH]` line but no Complete line. check-dispatch-audit reports
6 finalize dispatch lines against 13 completions, channel confidence low.

## Root cause

The re-fire path of the finalize loop-back (and the re-dispatch after an escalate_ask answer) dispatches the step
without going through the seam that writes the `[DISPATCH]` line.

## Proposed action

Route every finalize dispatch, including loop-back re-fires and post-escalation re-dispatches, through the same
dispatch-logging seam, so the dispatch audit can grade more than a floor.

## Evidence

- aspect: logging_gap_analysis — re-fires without [DISPATCH], verification-feedback without Complete
- aspect: execution_context_dispatch_audit — channel_completeness ratio 0.462, confidence low

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `scenario-replay-harness-013.md` from plan scenario-replay-harness (PLAN-22, #50; Claude Code)
