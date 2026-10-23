envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-17T18:23:16Z

# Resolve sibling-relative verification commands against the main checkout

Component: plan-marshall:phase-5-execute
Category (proposed): bug
Source: plan spend-removal, retrospective (execute envelope 2 and functional review round 1)

## Context

Deliverables 4 and 5 carried the verification command `python3 ../plan-marshall-documentation/.claude/skills/doc-review/scripts/trace.py ../plan-marshall-documentation/doc .`, copied verbatim from the repository's CLAUDE.md, which assumes the repositories are checked out side by side. The execute envelope runs inside the worktree `.plan/local/worktrees/spend-removal/`, where `../plan-marshall-documentation` points to `.plan/local/worktrees/plan-marshall-documentation` and does not exist. Execute envelope 2 rewrote the call with absolute paths; functional review round 1 reported that no trace.py run was recorded and that the sibling repository was not reachable from the worktree, so the D4/D5 link criteria were graded on indirect evidence until round 2 ran it by hand.

## Root cause

A worktree sits three directories deeper than the main checkout, so every command a project documents relative to the repository's parent directory changes meaning inside a worktree. Nothing in the outline, the plan or the execute envelope rebases such paths.

## Proposed action

- When phase-4 stamps a verification command or phase-5 runs one, resolve parent-relative paths (`../X`) against the main checkout root instead of the worktree root (or run the command with the main checkout's parent as its anchor), and log the rewrite.
- Alternatively have the outline Q-Gate flag a verification command with a parent-relative path when `use_worktree` is true.

## Evidence

- aspect: chat_history_analysis - execute envelope 2: "The documented check command uses ../plan-marshall-documentation relative to the repo root, which does not resolve from inside the worktree. I ran trace.py with absolute paths."
- aspect: request_result_alignment - functional review round 1: "no run of it is recorded, and the sibling documentation repository is not reachable from the worktree".
