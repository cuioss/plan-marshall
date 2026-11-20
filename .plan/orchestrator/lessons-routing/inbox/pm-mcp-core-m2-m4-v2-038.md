envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4-v2
epic=lessons-routing
kind=candidate-lesson
created=2026-11-20T13:43:24Z

component=plan-marshall:execution-context
category=anti-pattern

# Route leaf content searches to architecture search when Grep is denied

## Context

In plan-v2-155 the Grep tool was not granted to dispatched leaves. Three leaves (execute envelope, PR-body refresh twice) fell back to Bash `grep` four times and each reported it as a rule breach, instead of using `architecture search --content`, which the execution-context body names as the first-class path.

## Root cause

The fallback guidance sits in the envelope prose but is not reached in practice when a leaf needs to count or locate strings in a file it already has, so the model reaches for the shell.

## Proposed action

State in the leaf-facing workflows that need string search (pr-body edits, measurement scripts) the exact `architecture search --content --pattern` form, and for in-file counting point to Read plus a scratchpad script instead of Bash grep.

## Evidence

- aspect: permission-prompt-analysis — Grep not granted to leaves; 4 Bash grep calls
- aspect: chat-history-analysis — three leaf tool_notes: "I ran grep through Bash ... the Grep tool was not available in this session"
