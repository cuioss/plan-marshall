envelope_version=1
sender_type=plan
sender_id=plan-lb-38-review-gate-and-empty-scope
epic=live-blockers
kind=candidate-lesson
created=2026-10-11T23:05:53Z

component=plan-marshall:build-pyproject
category=improvement

# Detect a stale uv.lock on main instead of re-locking it inside plan builds

## Context

Dependabot PRs #1743 (ruff) and #1744 (mypy) bumped requirement floors in pyproject.toml on main without a matching uv.lock update. Every build in plan-lb-38's worktree then re-locked uv.lock (353 lines, e.g. ast-serialize 0.8.0 -> 0.12.1). Restoring the file did not stick because the next build rewrote it, leaving the tree dirty right before the push, so the operator had to choose to commit the re-lock inside a review-gate bug-fix PR (#1752).

## Root cause

A dependency-floor bump can land on main with a stale lock, and the build wrapper re-locks silently instead of reporting that the lock on the base branch is out of date. Each later plan inherits the churn and ships it under an unrelated subject.

## Proposed action

Have the pyproject build (or finalize-step-sync-baseline) detect that the lock does not satisfy pyproject.toml on the base branch and report it as its own condition (stale base lock) rather than rewriting it mid-plan; and make the dependency-bump path update uv.lock in the same PR (dependabot uv ecosystem or a lock-refresh check on those PRs).

## Evidence

- aspect: request_result_alignment - uv.lock is 1 of 7 realized files outside every deliverable's declared surface
- aspect: outline_vs_shipped - uv.lock in touched_but_unassessed (14 of 49 realized paths)
- aspect: manifest_decisions - uv.lock in references_only (realized but undeclared)
- aspect: chat_history_analysis - operator gate decision "Commit in this PR" after restore did not stick across builds
- squash commit 4a985a1bf carries uv.lock (353 lines changed)
