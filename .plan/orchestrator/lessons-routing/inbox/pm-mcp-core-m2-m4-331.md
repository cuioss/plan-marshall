envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-18T09:56:35Z

component=plan-marshall:plan-retrospective
category=bug
confidence=medium
source=plan-retrospective (log-analysis, plan-efficiency)

# Read the change ledger after worktree removal so build time is measured

## Context

Every execute envelope of plan-74-credential-store-choice reported a `kind=change` change-ledger entry per deliverable, and the freshness check cited "ledger row 178" (a whole-tree verify). Yet at the retrospective (order 995, after branch-cleanup removed the worktree) `analyze-logs` reports `build_time.ledger_present: false`, `ledger_rows_scanned: 0`, so `total_build_seconds` is `unavailable` and the build-count oracle cannot reconcile the 73 logged build calls.

## Root cause

Hypothesis, unverified: the ledger rows were written under the worktree's own `.plan` tree (review verdicts in this plan were also written to `.plan/local/worktrees/<plan>/.plan/local/plans/<plan>/work/`), and the ledger was not folded back into the main checkout's plan directory before the worktree was removed. Either the fold is missing or the retrospective reads the ledger from the wrong root.

## Proposed action

Confirm where the ledger lives after integrate-into-main; fold it into the main plan directory with the other plan state (or point the retrospective reader at the ledger's durable location), so post-merge consumers see the measured build time instead of an `unavailable` sentinel.

## Evidence

- aspect: log-analysis — build_time ledger_present false, ledger_readable false, summed_rows 0; build_count_reconciliation ledger_available false
- execute hand-backs: "Each deliverable has its own commit and a change-ledger entry"; freshness: "Ledger row 178 is a whole-tree verify"
