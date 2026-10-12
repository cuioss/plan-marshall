envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-11T16:59:15Z

# Add a script for the Q-Gate deliverable-hash gate

**Signal source**: plan-retrospective (llm-to-script-opportunities, chat-history-analysis), finalize step of workflow-dsl-parser-and-ast.

**Component (suggested)**: `plan-marshall:manage-solution-outline` (or the q-gate-validation workflow that owns Step 3.5)

**Category (suggested)**: improvement

## Context

The q-gate-validation content-hash gate (Step 3.5) compares per-deliverable and whole-outline hashes stored in `work/deliverable-hashes.toon`. No manage-* verb computes them. Across three Q-Gate passes the leaves improvised: the first computed hashes from `manage-solution-outline read --raw` output and warned the bytes might differ from the file; the second wrote an ad-hoc `hash_outline.py` in the scratchpad and ran it directly on `solution_outline.md` (a direct `.plan/` read, against the hard rules); the third compared a SHA-256 of the file against the stored whole-outline row.

## Root cause

A deterministic step (split the outline into deliverables, hash each, write the TOON) is left to LLM prose, so each pass picks its own input bytes and splitting rule, and the skip decision depends on which one it picked.

## Proposed action

Add a verb such as `manage-solution-outline hash-deliverables --plan-id X [--write]` that splits deliverables by the same parser the outline validator uses, hashes each plus the whole outline from the stored file, and writes or compares `work/deliverable-hashes.toon`, returning `changed[]` / `unchanged[]`. Point Step 3.5 at it.

## Evidence

- aspect: llm_to_script_opportunities — candidate "compute per-deliverable and whole-outline hashes", repetition 3, complexity low
- aspect: chat_history_analysis — 3-outline pass 2 report: "No manage-* command computes them, so I wrote a small helper ... hash_outline.py ... That is a direct read of a .plan/ file"
- 3-outline pass 1 report: hashes "computed from the raw outline as returned by manage-solution-outline read --raw, not from the file itself"
- Related to lessons-capture 003 (4-plan hash gate skipped its validators), which is about the gate's phase scoping, not about how the hashes are computed

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `workflow-dsl-parser-and-ast-017.md` from plan workflow-dsl-parser-and-ast (PLAN-07, #27)
