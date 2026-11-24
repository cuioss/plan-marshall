envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4-v2
epic=lessons-routing
kind=candidate-lesson
created=2026-11-21T09:47:09Z

component=pm-mcp-core:doc-review
category=bug
created=2026-11-21
bundle=pm-mcp-core
title=Make the trace.py link check runnable from a plan worktree

# Make the trace.py link check runnable from a plan worktree

## Context

The CLAUDE.md link check (`trace.py ../plan-marshall-documentation/doc .`) resolves the documentation checkout as a sibling path. From a plan worktree under `.plan/local/worktrees/` that path does not exist, so at least six agents in this plan reported BROKEN LINKS 1809 to 3095 as uninterpretable, built temporary symlinks, or skipped the check. The documentation criterion (D4.C6) ended up resting on one indirect work-log run.

## Root cause

The check assumes the main-checkout layout; the plan lifecycle runs it from a nested worktree.

## Proposed action

Give the check a worktree-safe entry point (resolve the documentation checkout from the main checkout, or accept an explicit path), and name that entry point in the staged specs' verification command so a docs criterion can be evidenced by a real run.

## Evidence

- aspect: chat_history_analysis - functional-review, execute and code-review agents all report trace.py unrunnable from the worktree
- aspect: llm_to_script_opportunities - repeated 6 times, low complexity wrapper
- aspect: request_result_alignment - D4 graded on the earlier work-log run, not a fresh one
