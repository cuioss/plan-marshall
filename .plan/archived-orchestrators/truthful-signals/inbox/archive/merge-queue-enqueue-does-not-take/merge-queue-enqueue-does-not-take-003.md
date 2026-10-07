envelope_version=1
sender_type=plan
sender_id=merge-queue-enqueue-does-not-take
epic=truthful-signals
kind=candidate-lesson
created=2026-08-03T20:58:36Z

component=plan-marshall:manage-findings
category=improvement
title=Two findings stores with disjoint populations and no cross-reference from the obvious query
confidence=high
source_plan=merge-queue-enqueue-does-not-take
source_pr=1087
routed_from=review-apparatus

# Two findings stores with disjoint populations and no cross-reference from the obvious query

## Context

`manage-findings` fronts two stores whose populations are disjoint, and the obvious plan-scoped query returns the one that excludes the review record. A sibling retrospective on this same plan queried the wrong store and **could not substantiate the 15 self-review findings at all** — it concluded they were absent.

Measured on this plan:

| Query | Returns |
|---|---|
| `manage-findings list --plan-id merge-queue-enqueue-does-not-take` | `total_count: 22` — test-failure, lint-issue, pr-comment |
| `manage-findings qgate list --plan-id ... --phase 6-finalize` | `total_count: 15` — the pre-submission-self-review findings |

Neither result mentions the other. The 22-row answer is a complete, confident, correctly-formatted TOON payload — it simply does not contain the review apparatus's entire output.

## Root cause

The plan-scoped store and the phase-scoped Q-Gate store are separate JSONL files (`artifacts/findings/*.jsonl` carries `qgate-2-refine`, `qgate-3-outline`, `qgate-4-plan`, `qgate-6-finalize` alongside `test-failure`, `lint-issue`, `pr-comment`), and `list` reads only the non-qgate set. `list` requires no `--phase`, so it reads as the general query; `qgate list` REQUIRES `--phase`, so a caller must already know which phase to ask about before they can find anything. A caller who does not know the qgate store exists has no path to discover it from the `list` output.

This is a pure measurement hazard rather than a data-loss bug — nothing is lost, but the default instrument silently under-reports, and it under-reports precisely the review findings that a retrospective exists to analyse.

## Proposed action

1. Have `list` report the qgate population it is NOT returning — e.g. a trailing `qgate_findings_available: {phase: count}` block, or at minimum `excluded_stores[]`. A caller must be able to learn the other store exists from the output they already have.
2. Allow `qgate list` without `--phase` (all phases), so discovery does not require prior knowledge of the phase key.
3. Consider `manage-findings list --all-stores` as the single honest query.

## Evidence

- Both queries run against this plan; counts 22 and 15, disjoint populations.
- `artifacts/findings/` file listing shows both store families side by side.
- A sibling retrospective step on this plan queried `list` and reported the 15 self-review findings as unsubstantiated.

## Dedup context for the orchestrator

New. Fits the epic theme exactly (a confident, complete-looking answer that silently spans the wrong population). Gate 1 dedup NOT run (`orchestrated: true`).
