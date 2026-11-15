envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4-v2
epic=lessons-routing
kind=candidate-lesson
created=2026-11-12T17:47:09Z

component=plan-marshall:platform-runtime
category=bug
title=Resolve execution-context-level-N in subagent dispatch on consumer repos

# Resolve execution-context-level-N in subagent dispatch on consumer repos

## Context

At the first phase-5 dispatch (2026-11-12T08:32:30Z) the `platform_runtime` subagent dispatch seam returned `prompt_not_found` for `execution-context-level-4` — "agent not found in marketplace tree; also with the plan-marshall: prefix". The orchestrator then dispatched through the host Agent tool directly for the remainder of the run. The same consumer-repo condition showed up as `executor_drift: unknown` ("Explicit marketplace anchor did not resolve to marketplace/bundles") in sync-baseline and the branch-cleanup rebase.

## Root cause

The dispatch seam resolves the agent prompt only against a `marketplace/bundles` tree, which a consumer repository does not have; it does not fall back to the installed bundle cache the way `resolve-workflow` does.

## Proposed action

Resolve the agent prompt through the same worktree-then-installed-cache order `extension_api resolve-workflow` uses, and log a seam failure as an ERROR in work.log (it currently appears only as a decision-log WARNING).

## Evidence

- decision.log 42ef3a (WARNING): "platform_runtime subagent dispatch returned error prompt_not_found for execution-context-level-4"
- aspect: logging_gap_analysis — seam failure invisible in work.log
- aspect: chat_history_analysis — fallback to direct Agent dispatch for the rest of the run
- plan: plan-v2-132-coverage-parser-hardening
