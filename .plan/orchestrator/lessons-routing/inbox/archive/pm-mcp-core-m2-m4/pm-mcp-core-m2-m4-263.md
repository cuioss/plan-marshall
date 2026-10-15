envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-14T13:31:52Z

> Routed by orchestrator epic pm-mcp-core-m2-m4 from plan static-verifier-residuals (PLAN-56, pm-mcp-core #66, merged 7981d17), drained 2026-10-14.
> Source inbox message(s): static-verifier-residuals-001.md 

# Candidate lesson: a review-driven correction can itself open a fail-open

Plan: static-verifier-residuals (PR plan-marshall/pm-mcp-core#66, merged at 7981d17).
Signal source: Q-Gate findings 62ec3c and 6e02a8 (phase 6-finalize, rule code-review, severity error).

## What happened

Three code-review rounds were needed. Two of the blocking findings were fail-opens that the
plan's OWN corrections had introduced, not defects of the original change:

- 62ec3c (WorkflowValidator.java:1344-1353, Rule 9): a step completed on a loop-back into its
  own opening was dropped from the opening's steps, so its firing was never checked. Fixed in
  the round at 8c3130d.
- 6e02a8 (WorkflowValidator.java:1628-1637, STEP_LIST distinct count): the fix at 869b753
  switched to a distinct count, after which a step completed twice on a pass was refused
  nowhere when both completions sat on transitions into openings. Round 2 caught it.

## Candidate rule

When a verifier check is corrected (counting, set membership, loop-back handling), treat the
correction as a new change that needs its own negative tests: add a fixture that the OLD check
refused and assert the corrected check still refuses it, before re-requesting review. A
"distinct" or "dedup" rewrite of a counting rule is the typical place where a refusal silently
disappears.

## Suggested owner

pm-mcp-core verifier work (pm-workflow, WorkflowValidator) and/or the generic code-review
loop guidance in plan-marshall (phase-6-finalize code-review round handling). Classification
deferred to the orchestrator.
