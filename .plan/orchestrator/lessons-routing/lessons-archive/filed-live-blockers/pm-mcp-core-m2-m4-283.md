envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-15T06:32:51Z

> Routed by orchestrator epic pm-mcp-core-m2-m4 from plan plan-09-audit-trail (PLAN-09, pm-mcp-core #69, merged 3236ed5), drained 2026-10-15.
> Source inbox message(s): plan-09-audit-trail-029.md
> RECURRENCE of -067, -080, -110, -121, -185, -225. Earlier numbers are lessons-routing messages pm-mcp-core-m2-m4-NNN.

# Add a hash primitive so Q-Gate deliverable-hash skipping can fire

- Source: plan-retrospective (plan-09-audit-trail), aspects chat-history-analysis and llm-to-script-opportunities; artifact `work/deliverable-hashes.toon`.
- Suggested component: `plan-marshall:manage-solution-outline` (new verb) / `plan-marshall:phase-3-outline` (q-gate-validation Step 3.5).

## Context

Three q-gate-validation leaves in this plan (two in 3-outline, one in 4-plan) reported that they had no allowed way to compute SHA-256 over `solution_outline.md`: reading `.plan` files directly is forbidden and no script verb hashes deliverables. Each wrote `not_computed_*` placeholders into `work/deliverable-hashes.toon` (one leaf skipped the file entirely). A placeholder never matches, so every re-run revalidated all six deliverables in full.

## Root cause

The Step 3.5 unchanged-deliverable skip depends on a hash the leaf is expected to compute, but the only sanctioned file access cannot produce one. The optimisation is dead code on every plan that re-runs Q-Gate.

## Proposed action

Add a deterministic verb (e.g. `manage-solution-outline hash-deliverables --plan-id P`) that writes per-deliverable and whole-outline SHA-256 values to `work/deliverable-hashes.toon`, and have the q-gate-validation workflow call it instead of asking the LLM to hash.

## Evidence

- chat-history-analysis: q-gate leaves a0d2a18 ("no allowed way to compute SHA-256"), aa1e7c5 ("placeholder `not_computed_pending_findings`"), a2d179d / ab47362 ("There is no hash primitive")
- llm-to-script-opportunities: candidate "compute per-deliverable SHA-256 hashes", repetition 3, complexity low
