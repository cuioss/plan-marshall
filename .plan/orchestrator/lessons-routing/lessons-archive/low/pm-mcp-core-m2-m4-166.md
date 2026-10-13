envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T06:54:55Z

# Candidate lesson: finalize loop-back re-fires emit no [DISPATCH] line and record no tokens

- Component: plan-marshall:phase-6-finalize (step dispatcher on loop-back re-entry) / plan-marshall:manage-execution-manifest (record-step)
- Suggested category: bug
- Signal: plan-retrospective (execution-context-dispatch-audit, logging-gap-analysis, plan-efficiency)

## Context

Finalize re-fired automatic-review, sonar-roundtrip and the unified triage three more times after the first
round. Only the first firing of each wrote a `[DISPATCH]` work-log line. The later leaves completed with
`[STATUS] (plan-marshall:execution-context.<step>) Complete` and no dispatch line before them. record-step
logged `total_tokens=unmeasured` for 7 of 9 finalize steps, including dispatched leaves.

## Root cause

The loop-back re-entry path dispatches the step leaves without going through the seam that emits the
`[DISPATCH]` line, and the leaf's `<usage>` totals are not forwarded to record-step on either path.

## Proposed action

Route every finalize step firing, first and re-fire alike, through the one dispatch seam that writes the
`[DISPATCH]` line and the dispatch-boundary row, and pass the leaf's usage totals to record-step. Add a
check that the number of `execution-context.<step> Complete` lines does not exceed the `[DISPATCH]` lines
for that step.

## Evidence

- work.log: automatic-review leaf completions at 20:48:56, 21:29:08, 21:56:42; sonar-roundtrip at 20:37:30,
  21:12:17, 21:47:21; wait-region-unified-triage at 20:58:53, 21:35:24 - none preceded by a `[DISPATCH]` line
  (the first firings at 20:00:02, 20:08:17, 20:09:06 have one).
- execution-context-dispatch-audit: dispatch_coverage 2 dispatched / 0 inline / 7 no_evidence of 9;
  channel_completeness 6 finalize dispatch lines against 22 completions, confidence low; firing_comparison
  6-finalize has 9 unpaired execution rows and 2 keyless boundary rows.
- decision.log: record-step for ci-verify, automatic-review, sonar-roundtrip, lessons-capture all
  `total_tokens=unmeasured`; only create-pr (205,943) and branch-cleanup (300,086) measured.
- plan-efficiency: the 3.44M finalize spend cannot be attributed to steps.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `workflow-engine-016.md` from plan workflow-engine (PLAN-13, #45; Claude Code)
