envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-11T16:59:09Z

# Candidate lesson: 4-plan q-gate-validation short-circuits on the whole-outline hash written by the 3-outline pass

**Signal source**: orchestrator observation, verified in the plan decision log.

**Component (suggested)**: `plan-marshall:plan-marshall` (workflow/q-gate-validation.md hash-skip)

## Evidence

- Decision log 2026-10-10T19:55:43Z (first 4-plan q-gate-validation dispatch): "Whole-outline hash unchanged (6d3ea5c8) and re-entry detected: validators module-mapping-validator and scope-criterion-validator skipped, prior pending count re-emitted (4-plan: 0)".
- The hash had been written by the 3-outline validation pass (19:03:20Z). The 4-plan pass had never run its own validators, so "unchanged" did not mean "already validated".
- Only the explicit re-dispatch at 19:56:02Z ran both validators (19:58:24Z module-mapping-validator pass; 19:58:26Z-19:58:29Z scope-criterion pass, including a coverage gap on Deliverable 5).

## Why it matters

The hash-skip cache is keyed on outline content but not on the phase / validator set that produced it, so a first-time 4-plan validation is treated as a re-entry and its validators silently never run. "Summary: 5 passed, 0 flagged" was reported over zero validator runs.

## Suggested direction (for orchestrator classification)

Key the hash-skip record by phase (and validator set), or require a prior run of the same validators at the same phase before skipping. Report a hash-skipped validator as "not run (cached from phase X)" rather than as passed.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `workflow-dsl-parser-and-ast-003.md` from plan workflow-dsl-parser-and-ast (PLAN-07, #27)
