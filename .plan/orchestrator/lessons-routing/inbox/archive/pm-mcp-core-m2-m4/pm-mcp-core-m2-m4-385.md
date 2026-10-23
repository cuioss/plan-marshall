envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-19T18:47:08Z

component=plan-marshall:manage-architecture
category=improvement

# Extend architecture search --content to resource files leaves cannot otherwise sweep

Source: plan-retrospective of plan-70-plan-instance-alignment (aspects chat-history-analysis, permission-prompt-analysis).

## Context

Every dispatched leaf in this plan ran without Grep and Glob. The 4-plan Q-Gate reported that `architecture search --content` does not inventory `.json`, `.txt`, `.mmd` or `.pmwf` resources, so removed-identifier sweeps missed `composition-rules.json`, the diagram goldens and the `.pmwf` fixture units; the refine leaf had the same gap for test resources. Two code-review leaves and one triage leaf then fell back to `git grep` through Bash, which the persona rules forbid.

## Root cause

The content-search inventory walks only module-attributed source kinds, and the leaf has no sanctioned fallback for resource trees once the harness denies Grep.

## Proposed action

Include test and main resource files (at least `.json`, `.txt`, `.mmd`, `.pmwf`, `.adoc` fixtures) in the `search --content` population, or publish the walked extensions in its result so a sweep can state what it did not cover. Leaves then need no `git grep` fallback.

## Evidence

- chat-history-analysis: 4-plan q-gate leaf, "architecture search --content does not inventory .json, .txt, .mmd or .pmwf resource files"
- chat-history-analysis: code-review rounds 1 and 3 and triage leaf ac5b65 used git grep via Bash
- permission-prompt-analysis: Grep and Glob denied to every leaf
