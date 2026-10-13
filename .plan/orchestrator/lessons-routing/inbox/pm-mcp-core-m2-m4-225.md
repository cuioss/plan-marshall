envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T11:06:09Z

# Add a deliverable-hash subcommand for incremental q-gate validation

Component: plan-marshall:manage-solution-outline (category: improvement, confidence: high)

## Context

q-gate-validation keeps `work/deliverable-hashes.toon` (one row per deliverable plus `__whole_outline__`) to skip
unchanged deliverables. In scenario-replay-harness the 3-outline q-gate wrote an ad-hoc helper
`.plan/temp/scenario-replay-harness/hash_outline.py` to compute it, and the 4-plan q-gate could not recompute the
per-deliverable rows at all ("without splitting the outline in the shell") and kept stale rows.

## Root cause

No script computes the hashes, so each dispatch improvises or degrades.

## Proposed action

Add a `manage-solution-outline` subcommand (e.g. `hash-deliverables --plan-id X`) that splits the outline by
deliverable heading, hashes each section and the whole file, and writes `work/deliverable-hashes.toon`.

## Evidence

- aspect: llm_to_script_opportunities — 2 repetitions this plan, complexity low
- 3-outline q-gate hand-back (helper files) and 4-plan q-gate hand-back (rows kept)

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `scenario-replay-harness-016.md` from plan scenario-replay-harness (PLAN-22, #50; Claude Code)
