envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-11T20:54:31Z

# Candidate lesson: build-maven reports only the last module's test count for a reactor build

Component: plan-marshall:build-maven
Category (proposed): bug
Source: plan code-analysis-base, phase-5 verification builds

## Observation

The build-maven wrapper's TOON result reported "247 tests executed" for a multi-module reactor verify that actually ran about 1800 tests. 247 is the Surefire summary of the last module in the reactor; the parser keeps the last "Tests run:" summary line instead of summing the per-module summaries.

## Impact

A verification step or a reviewer reading the count concludes most tests did not run (or a test-count regression goes unnoticed when it happens in a non-last module).

## Proposed correction

Sum the per-module Surefire/Failsafe "Results" summaries across the reactor (or report them per module plus a total), with a fixture log of a multi-module reactor.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `code-analysis-base-003.md` from plan code-analysis-base (PLAN-36, #31)
