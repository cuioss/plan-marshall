envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4-v2
epic=lessons-routing
kind=candidate-lesson
created=2026-11-12T17:47:11Z

component=plan-marshall:phase-5-execute
category=bug
title=Ledger commits made at the orchestrator-tier quality-gate hand-back

# Ledger commits made at the orchestrator-tier quality-gate hand-back

## Context

After the envelope hand-back, the orchestrator ran the whole-tree `verify -Ppre-commit` and committed its rewrites (f5f1931c, 5 files) plus a Javadoc fix (1f80e2ab) outside the gated per-deliverable commit step. The 5-execute -> 6-finalize transition then refused with `execute_commits_unrecorded` / `bookkeeping_gap` (2 of 7 branch commits without a `kind=change` row). That dispatch ended with `termination_cause: error` and cost 146,533 tokens before the rows were appended by hand.

## Root cause

The orchestrator-tier hand-back path (`verify:quality-gate` run by the orchestrator, gate rewrites committed in a separate cleanup commit) has no step that writes the change-ledger row the transition guard requires.

## Proposed action

Have the hand-back workflow commit gate rewrites through the gated `git-workflow commit` verb (which ledgers the commit), or add a `manage-change-ledger` verb that appends rows for the guard's `unrecorded_commits` list from `git diff-tree`, so the transition does not need a failed dispatch to surface it.

## Evidence

- aspect: script_failure_analysis — manage-status transition script_internal_error at 2026-11-12T10:18:22Z
- aspect: logging_gap_analysis — 5-execute error_total_tokens 146533
- work.log 6600d3 — "Transition 5-execute -> 6-finalize refused: error=execute_commits_unrecorded"
- plan: plan-v2-132-coverage-parser-hardening
