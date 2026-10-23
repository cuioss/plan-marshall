envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-18T09:16:39Z

# Candidate lesson: Detect an executor regenerated for another harness mid-plan

Source: plan-retrospective (chat-history-analysis + script-failure-analysis), plan-69-unit-frontmatter-and-types
Component (suggested): plan-marshall:tools-script-executor (foreign bundle - route to plan-marshall lessons inbox)
Category (suggested): bug
Relation to earlier messages: complements 011 (manage-config domain-narrow crash). 011 records the symptom and guesses a stale OpenCode copy; this one records the root cause.

## Context

During 3-outline a concurrent OpenCode session on the same machine rewrote the main checkout's shared `.plan/execute-script.py` (and edited `.plan/marshal.json`, plus added `opencode.json`). From then on the Claude-driven plan's notations resolved to `~/.config/opencode/skills/...` copies, and `manage-config domain-narrow` crashed with `resolve_bundles_root: could not locate a 'plan-marshall' bundle`. The phase halted; the operator had to diagnose it and choose "Regenerate for Claude".

## Root cause

The executor is a single shared file per checkout with no record of which harness generated it, and nothing in the running plan notices when another harness regenerates it underneath.

## Proposed action

Stamp the generating target (harness + plugin root) into the generated executor, record the stamp in `status.metadata.harness` context at plan start, and have the executor (or phase handshake) refuse with a named `executor_target_mismatch` error - naming the observed and expected target and the regenerate command - instead of dispatching into a foreign skills tree and crashing deep inside a script.

## Evidence

- chat-history-analysis: operator decision "script runner was rewritten at 21:56 for OpenCode ... manage-config crashes" -> "Regenerate for Claude"
- script-failure-analysis: manage-config domain-narrow script_internal_error, traceback path `/home/oliver/.config/opencode/skills/plan-marshall-manage-config/scripts/`
- outline revision dispatch returned `error: script_crash` at Step 12 domain narrowing
