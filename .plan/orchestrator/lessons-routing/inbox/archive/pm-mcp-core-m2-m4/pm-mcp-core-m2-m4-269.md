envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-14T13:31:56Z

> Routed by orchestrator epic pm-mcp-core-m2-m4 from plan static-verifier-residuals (PLAN-56, pm-mcp-core #66, merged 7981d17), drained 2026-10-14.
> Source inbox message(s): static-verifier-residuals-007.md 
> RECURRENCE of lessons-routing inbox messages already routed by this epic: pm-mcp-core-m2-m4-208 (queued); -047, -064 (archived). Fold into those; this is new evidence from another plan, not a new lesson.

component=plan-marshall:phase-6-finalize
category=bug
title=Record dispatch boundaries and [DISPATCH] lines for every finalize dispatch

# Record dispatch boundaries and [DISPATCH] lines for every finalize dispatch

## Context

In plan static-verifier-residuals, 6-finalize consumed 2.66M of 5.37M tokens (49%) across 3 code-review rounds, 4 functional-review firings, 2 correction dispatches, sonar, automatic-review and triage. No `work/metrics-dispatch-boundaries-6-finalize.toon` was written, the verifier dispatches and the second code-review correction logged no `[DISPATCH]` line, and two inline-instruction dispatches (docs-watch-retirement, code-review-correction) were logged as role=phase-5-execute with a phase-5 workflow notation they did not run.

## Root cause

The finalize dispatch sites (review verifiers, correction leaves, inline-instruction dispatches) do not all route through the dispatch-boundary recorder and the `[DISPATCH]` emitter, and inline-instruction dispatches reuse a workflow notation instead of naming their instructions.

## Proposed action

Route every finalize dispatch (author, verifier, correction, triage) through `manage-metrics record-dispatch-boundary` and the `[DISPATCH]` seam; give inline-instruction dispatches a distinct workflow token (e.g. `instructions:{name}`) instead of a phase workflow path.

## Evidence

- aspect: execution-context-dispatch-audit — dispatch_coverage 2 dispatched / 8 no_evidence of 10 finalize steps; channel confidence low (ratio 0.438); 6-finalize firing comparison not_evaluated (no boundary file)
- aspect: log-analysis — dispatch_boundaries present for 4-plan and 5-execute only
- aspect: logging-gap-analysis — work.log 10:07:26 [DISPATCH] role=phase-5-execute workflow=phase-5-execute/SKILL.md followed by `execution-context.docs-watch-retirement Complete`; 11:42:11 `code-review-correction-2 Complete` with no [DISPATCH] line
