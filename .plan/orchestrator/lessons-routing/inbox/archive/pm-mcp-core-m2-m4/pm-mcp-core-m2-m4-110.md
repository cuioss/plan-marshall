envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-11T20:54:49Z

# No script verb computes the per-deliverable outline hashes the Q-Gate workflow requires

## Observation

The q-gate validation workflow expects `work/deliverable-hashes.toon` (per-deliverable fingerprints plus a `__whole_outline__` row) so a re-run can skip unchanged deliverables. No `manage-*` verb produces it. On this plan one leaf skipped the step (forcing a full re-check next time), and the next leaf improvised an ad-hoc scratchpad Python script, which is exactly the hand-made-helper pattern the workflow rules forbid.

## Suggested direction

Add a deterministic verb (e.g. `manage-solution-outline hash-deliverables --plan-id X`) that parses the outline's `### N.` deliverable sections, hashes each plus the whole document, and writes the TOON artifact; point the q-gate workflow step at it.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `runtime-lifecycle-021.md` from plan runtime-lifecycle (PLAN-08, #29)
