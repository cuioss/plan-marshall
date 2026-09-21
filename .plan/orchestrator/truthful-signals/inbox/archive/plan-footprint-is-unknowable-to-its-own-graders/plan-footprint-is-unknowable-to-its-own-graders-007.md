envelope_version=1
sender_type=plan
sender_id=plan-footprint-is-unknowable-to-its-own-graders
epic=truthful-signals
kind=candidate-lesson
created=2026-08-27T14:44:48Z

component=plan-marshall:manage-solution-outline
category=anti-pattern
confidence=high
source_plan=plan-footprint-is-unknowable-to-its-own-graders
source_pr=1359

# get-deliverable was argparse-rejected 11 times in a single run

## Context

The plan's `script-execution.log` records 26 non-zero-exit script calls across 11 unique failure signatures. One signature accounts for **11 of the 26 (42 %)**:

`plan-marshall:manage-solution-outline:manage-solution-outline get-deliverable` → `exit_code: 2`, classified `argparse_other`, first seen `2026-08-26T17:02:44Z`.

No other signature in the run exceeds 4 occurrences. The next largest is `manage-references sync-affected-files` at 4, then `manage-logging decisions` at 3.

## Root cause

An eleven-fold repetition of the same argparse rejection is not a typo — it is a caller working from a documented or remembered form the live parser does not accept, and re-attempting it. The recorded stderr excerpt for this signature is empty, so the rejection surfaced no usage text to correct from, which is likely why it repeated rather than being fixed on the second attempt.

## Proposed action

Two parts, and the second is the durable one:

1. Establish what form callers are reaching for and reconcile it with the live `get-deliverable` surface — either accept it, or make the documented form match.
2. An `argparse_other` classification with an **empty stderr excerpt** is the condition under which a caller cannot self-correct. `script-failure-analysis` should surface empty-excerpt clusters distinctly; an argparse rejection that prints no usage is a worse failure than one that does.

## Evidence

- aspect: script_failure_analysis — `total_failures: 26`, `unique_failures: 11`; the `get-deliverable` row carries `occurrence_count: 11`.
- Distribution of the other 15: `sync-affected-files` 4, `manage-logging decisions` 3, and eight singletons.
- Two further signatures name invented flags/subcommands (`manage-config plan`, `manage-logging work`, `review_completeness check`), the recurring class the "never invent script subcommands" rule targets — but each fired once, so only this cluster is seeded.
