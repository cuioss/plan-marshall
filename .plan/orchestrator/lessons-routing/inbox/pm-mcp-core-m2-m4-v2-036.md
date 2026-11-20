envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4-v2
epic=lessons-routing
kind=candidate-lesson
created=2026-11-20T13:43:23Z

component=plan-marshall:phase-6-finalize
category=bug

# Return the absolute PR body path so create-pr never builds it by hand

## Context

In plan-v2-155 the create-pr leaf first wrote the PR body to the main-checkout plan dir (`.plan/local/plans/{plan}/work/ci-bodies/pr-create-default.md`) while `pr_intent_section render` read the nested worktree plan dir (`.plan/local/worktrees/{plan}/.plan/local/plans/{plan}/work/ci-bodies/...`) and failed with `body_unreadable`. The leaf recovered by rewriting at the worktree path and left a stray untracked file in the main checkout.

## Root cause

The body path is composed by the model from prose, and under a worktree the plan dir exists twice (main checkout and nested in the worktree), so the wrong one is easy to pick.

## Proposed action

Have `pr prepare-body` return the absolute body path it expects and have `pr_intent_section render` and `pr create` take that path, so no leaf constructs the plan-dir path itself.

## Evidence

- aspect: script-failure-analysis — `pr_intent_section render` script_internal_error, error body_unreadable at 10:27:03
- aspect: chat-history-analysis — create-pr leaf: "My first Write of the PR body went to a wrong path"
