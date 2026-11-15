envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4-v2
epic=lessons-routing
kind=candidate-lesson
created=2026-11-12T17:47:10Z

component=plan-marshall:phase-6-finalize
category=improvement
title=Let the merge queue absorb a no-conflict overlap instead of forcing a rebase

# Let the merge queue absorb a no-conflict overlap instead of forcing a rebase

## Context

At the first branch-cleanup firing, upstream #391 touched the same spec file as PR #388 with no content conflict (`overlap_no_content_conflict`, `auto_reconcilable: true`, `conflict_count: 0`). Under `auto_rebase_threshold: no_overlap_only` this became `needs_user`, and `conflict_gate gate` returned `queue_wait: forbidden` even though `use_merge_queue: true`. The operator chose "Rebase and force-push onto the base"; the rebase (bca5ff23 -> bf9d510a) lapsed the HEAD-bound merge consent, made pre-push freshness stale, and re-fired the quality gate, both full review rounds, CI, Sonar and automatic-review. On re-dispatch the classifier returned `no_overlap` and the queue path skipped the rebase — the queue rebases and re-tests anyway.

## Root cause

The conflict gate forbids the queue route for any overlap the threshold flags, without distinguishing a no-content-conflict overlap that the merge queue would rebase and re-test itself.

## Proposed action

When `use_merge_queue: true` and the classifier reports `overlap_no_content_conflict` with `conflict_count: 0`, let the queue route proceed (or offer it as the recommended option) instead of forcing an immediate-merge rebase that invalidates every head-bound gate.

## Evidence

- aspect: chat_history_analysis — branch-cleanup escalate_ask and its own note "A cheaper option ... the merge-queue path would proceed without a rebase and the consent at bca5ff23 would stay valid"
- aspect: plan_efficiency — the rebase re-fire is one of the four HEAD advances behind the 60% finalize share
- decision.log 035ccd, cc08b0, 5a36e4, b5cf98
- plan: plan-v2-132-coverage-parser-hardening, PR #388
