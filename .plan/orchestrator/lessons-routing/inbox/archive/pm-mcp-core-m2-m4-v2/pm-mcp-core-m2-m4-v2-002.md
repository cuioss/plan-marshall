envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4-v2
epic=lessons-routing
kind=candidate-lesson
created=2026-11-07T20:34:10Z

component=plan-marshall:workflow-integration-git
category=improvement
confidence=high
source_plan=plan-v2-93-http-tests-annotations

# Append the change-ledger row when a commit is made outside execute-task

## Context

In plan-v2-93 the orchestrator committed the pre-commit gate's rewrites as a style commit (29dd6b6f, later rebased to 0801c937) outside execute-task Step 10a. The `manage-status transition --completed 5-execute` call then exited 1 with `execute_commits_unrecorded` (signature `bookkeeping_gap`): 9 of 10 branch commits had a change-ledger row. That cost a full 5-execute dispatch recorded as `error` (107757 tokens) and a manual `manage-change-ledger append` with a hand-picked deliverable id for a commit that spanned three modules. The later operator-ordered import commit 384de3ec needed the same bookkeeping.

## Root cause

The ledger row is written only by execute-task's Step 10a, so any commit made by the orchestrator, a finalize step, or an operator instruction is unrecorded unless someone remembers the append.

## Proposed action

Let `git-workflow commit` append the change-ledger row itself when given `--plan-id` (deliverable 0 or a declared `--deliverable-id`), so every plan-scoped commit path records the row. The transition guard's error should also name the one-line command that fixes it, which it already partly does.

## Evidence

- script-failure-analysis: `manage-status transition` exit 1, 2 occurrences from 14:38:52Z
- logging-gap-analysis: 5-execute `error` boundary row, 107757 tokens
- chat-history-analysis: transition-refused hand-back naming the unrecorded commit and its 13 paths
