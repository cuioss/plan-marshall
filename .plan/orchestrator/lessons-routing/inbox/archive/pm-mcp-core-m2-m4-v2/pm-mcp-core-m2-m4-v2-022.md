envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4-v2
epic=lessons-routing
kind=candidate-lesson
created=2026-11-12T17:47:11Z

component=plan-marshall:workflow-integration-git
category=improvement
title=Support a detached old-commit probe tree in worktree-create

# Support a detached old-commit probe tree in worktree-create

## Context

D2 required running the hostile-prolog probes against the pre-change commit f97bc7f2 in a temporary tree under `.plan/temp/`. The leaf called `git-workflow worktree-create --detach`, which argparse rejected (`--detach` is not declared; exit 2). It then created the tree with a raw `git worktree add --detach` and later removed it with `git worktree remove --force` plus `prune` — all outside the gated verbs.

## Root cause

`worktree-create` only models the plan's feature-branch worktree; there is no sanctioned verb for a short-lived, detached, read-only tree at a given commit, which "prove the test fails on the old code" deliverables need.

## Proposed action

Add a detached mode to `worktree-create` (commit-ish argument, temp-root placement, paired remove), or a dedicated probe-tree verb, and reference it from the regression-test deliverable guidance.

## Evidence

- aspect: script_failure_analysis — git-workflow worktree-create argparse_other at 2026-11-12T08:51:48Z
- aspect: chat_history_analysis — "The sanctioned way to create the old-commit tree failed ... I used a plain git worktree add --detach instead"
- plan: plan-v2-132-coverage-parser-hardening
