envelope_version=1
sender_type=plan
sender_id=a-refusal-nobody-recognises-is-filed-as-a-finding
epic=review-apparatus
kind=candidate-lesson
created=2026-08-25T07:22:32Z

component=plan-marshall:manage-metrics
category=improvement
title=Four per-firing ledgers disagree about the same step and none publishes its denominator

# Four ledgers, four different counts, no denominator anywhere

## Context

`pre-submission-self-review` fired 7 times. The plan's records say:

| Ledger | Rounds covered |
|--------|----------------|
| `work.log` `[DISPATCH]` lines | 2 of 7 |
| `decision.log` `effort resolve-target` | 2 of 7 |
| `status.metadata.phase_steps` `firing_count` | 5 of 7 |
| `work/metrics-dispatch-boundaries-6-finalize.toon` | 5 of 7 |
| `work/metrics-accumulator-6-finalize.toon` | 6 of 7 |
| `execution.toon` `execution_log` | 5 of 7, aggregated into 2 rows |
| `artifacts/findings/qgate-6-finalize.jsonl` | 5 of 7 rounds persisted findings |

Six independent records, no two agreeing, and the intersection is empty of any that reaches 7. The **only** artefact in the entire plan that states the true firing count is free text: the step's own `display_detail` string, and one `WARNING` line in `decision.log`.

The phase-level consequence is measurable: the accumulator reports 3,072,074 tokens over 15 samples; the dispatch-boundary ledger and the execution_log both report 2,808,583 over 14 rows. The 263,491-token difference is one entire dispatched step that accumulated usage and recorded no boundary — discoverable only by summing 14 rows by hand.

## Root cause

Each ledger is written by a different call site with its own trigger, and none of them publishes the population it is counting against. A reader of any single ledger sees a total that looks complete. This is the plan-marshall recurring archetype: *a check that can return N from an incomplete population must publish the population size*.

## Proposed action

1. Give `manage-metrics` a reconciliation verb that, per phase, reports accumulator samples vs boundary rows vs execution_log rows vs `firing_count`, with an explicit `unreconciled` verdict when they disagree.
2. Make `metrics.md` carry the verdict, not just the accumulator figure.
3. Treat any per-firing ledger without a published denominator as a floor, and say so in the rendered output — the way `generate`'s `partial` / `unrecorded_phases` already does for phase rows.

## Evidence

- aspect: execution-context-dispatch-audit — `cross_ledger_coverage` table, `token_reconciliation` block
- aspect: plan_efficiency — every token figure in this plan is a floor of unknown depth
