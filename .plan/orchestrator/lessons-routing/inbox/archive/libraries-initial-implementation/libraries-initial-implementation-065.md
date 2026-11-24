envelope_version=1
sender_type=orchestrator
sender_id=libraries-initial-implementation
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:07:41Z

component=plan-marshall:phase-6-finalize
category=improvement
title=Run Sonar-class static checks locally before the first push to cut review rounds
source_lesson=2026-11-23-14-011
source_repo=git-document-repository (epic libraries-initial-implementation)
source_created=2026-11-23

# Run Sonar-class static checks locally before the first push to cut review rounds

## Context

In plan-10-store-signing-trailers-verify phase 6-finalize consumed 4,518,457 tokens, 56% of the plan's 8.04M (a multi_module feature, error anchor 2.5M). The wait-region triage ran six rounds against a granted budget of three, with three operator grants. Sonar new-code issues fell 18, 6, 2, 1 across successive pushes: each fix commit surfaced the next layer (S6206 records, S3398 method placement, S6878 record pattern, S1135 placeholder), and each round re-ran sync-baseline, simplify, quality gate, push, ci-verify, automatic-review and sonar-roundtrip. The long cycle also let an upstream commit (PR #59) land and force a baseline-drift reconcile through 2-refine.

## Root cause

Sonar rules are only evaluated after a push, one scan per round, so rule families that a local pass could catch in one sweep are fixed serially at the cost of a full finalize replay each.

## Proposed action

Before the first push, run a local static-analysis pass that covers the Sonar rule families the project gates on (or the project's Sonar-equivalent profile), and fold all its findings into one fix round. When a triage round fixes code, re-check the touched files for the same rule families before replaying finalize.

## Evidence

- aspect: plan_efficiency — [BUDGET] error, 8.04M tokens and 331 min wall against the multi_module+feature 2.5M / 180 min anchors; 6-finalize share 0.56
- aspect: chat_history_analysis — sonar-roundtrip counts 18 -> 6 -> 2 -> 1 across rounds; loop_back_budgets spent 6, granted 3
- aspect: invariant_summary — main_sha drift 4-plan -> 5-execute and baseline_drift_count 1 during finalize
