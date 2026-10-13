envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T07:34:19Z

# Candidate lesson: add a script verb that writes deliverable-hashes.toon for Q-Gate leaves

Source: plan-retrospective of plan verify-not-resolve. Proposed component: `plan-marshall:manage-solution-outline` (consumer: the q-gate-validation workflow). Category: improvement. Confidence: high.

## Context

Both Q-Gate validation runs (3-outline and 4-plan, 8 deliverables each) skipped writing `work/deliverable-hashes.toon`. The SHA-256 per deliverable can only be computed by reading the plan files from a shell, which the rules forbid, and in the 4-plan run the leaf had no shell at all. Every re-run therefore re-validates all deliverables instead of skipping unchanged ones.

## Root cause

The workflow asks the LLM leaf to produce a deterministic hash, but no script provides it.

## Proposed action

Add a verb such as `manage-solution-outline deliverable-hashes --plan-id X` that computes and writes the fingerprint file. The q-gate-validation workflow then calls it in place of the manual step.

## Evidence

- aspect: llm-to-script-opportunities — 16 hash computations skipped over 2 runs
- aspect: chat-history-analysis — 3-outline Q-Gate: "Producing the SHA-256 values would mean reading the plan files directly from the shell"; 4-plan Q-Gate: "Computing the SHA-256 needs a shell, which I don't have in this envelope"

Classification is left to the orchestrator.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `verify-not-resolve-020.md` from plan verify-not-resolve (PLAN-18, #43; Claude Code)
