envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-18T09:56:35Z

component=plan-marshall:workflow-integration-git
category=improvement
confidence=high
source=plan-retrospective (chat-history-analysis, llm-to-script-opportunities)

# Keep sibling-relative project commands working inside the plan worktree

## Context

pm-mcp-core's CLAUDE.md prescribes the link check as `python3 ../plan-marshall-documentation/.claude/skills/doc-review/scripts/trace.py ../plan-marshall-documentation/doc .`, which assumes the repositories are checked out beside each other. The plan worktree lives at `.plan/local/worktrees/plan-74-credential-store-choice/`, so `../plan-marshall-documentation` points nowhere. Every documentation task (TASK-1, 16, 17, 23, 24, 26, 29) rewrote the command with absolute paths, and one functional-review round could not run the link check at all and checked link depths by hand.

## Root cause

The worktree is nested inside the main checkout, so any project command that addresses a sibling repository by a relative path breaks when cwd is the worktree; nothing translates or warns.

## Proposed action

Either resolve sibling-relative paths against the main checkout's parent when cwd is a plan worktree (for example a documented `{main_checkout}` substitution in project commands), or surface a preflight warning at worktree creation when CLAUDE.md commands reference `../` siblings, so agents do not each rediscover the rewrite.

## Evidence

- envelope 1 hand-back: "Relative doc-review path breaks in the worktree ... TASK-016 and TASK-017 will hit the same problem"
- functional review round 1: "the sibling documentation repository is not reachable from the worktree path. I checked the relative link depths and the anchors by hand"
