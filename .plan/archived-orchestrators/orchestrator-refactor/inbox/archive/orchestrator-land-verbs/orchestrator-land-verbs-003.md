envelope_version=1
sender_type=plan
sender_id=orchestrator-land-verbs
epic=orchestrator-refactor
kind=candidate-lesson
created=2026-10-03T17:41:44Z

component=plan-marshall:manage-solution-outline
category=improvement

# Add a script verb that computes q-gate deliverable hashes

## Context

The q-gate validation workflow persists per-deliverable and whole-outline hashes to `work/deliverable-hashes.toon` so a re-entry pass can skip unchanged deliverables, but no script computes them. In orchestrator-land-verbs the three q-gate passes each improvised: one ran a read-only `python3 -c` expression, one ran a scratch `hash_outline.py` that read `solution_outline.md` directly (bypassing the manage-* access rule), and the 4-plan pass wrote only the `__whole_outline__` row because it "could not compute per-deliverable hashes without a script" — so the next re-entry could skip nothing.

## Root cause

A deterministic, repeated computation was left to the LLM; the block-boundary rule (each `### N.` heading up to the next `### N.` or `## `) exists only in prose.

## Proposed action

Add `manage-solution-outline deliverable-hashes --plan-id P [--write]` that splits blocks through the shared `_plan_parsing` deliverable-heading pattern, hashes each block plus the whole outline, and writes `work/deliverable-hashes.toon`. Point the q-gate workflow at it.

## Evidence

- aspect: llm_to_script_opportunities — repetition_count 3, complexity low
- aspect: chat_history_analysis — three q-gate hand-backs each name the missing hashing command as a deviation
