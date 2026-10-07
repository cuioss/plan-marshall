envelope_version=1
sender_type=plan
sender_id=a-refusal-is-recorded-as-a-refusal-the-record
epic=review-apparatus
kind=candidate-lesson
created=2026-08-31T08:08:37Z

component=plan-marshall:manage-solution-outline
category=anti-pattern
title=The read verb rejected the same invocation seven times in one plan

# The read verb rejected the same invocation seven times in one plan

## Context

`script-failure-analysis` over plan `a-refusal-is-recorded-as-a-refusal-the-record` recorded **17 non-zero-exit script calls across 10 unique failure signatures**. One signature accounts for 7 of the 17:

| component | subcommand | exit | subtype | occurrences |
|---|---|---|---|---|
| `plan-marshall:manage-solution-outline:manage-solution-outline` | `read` | 2 | `argparse_other` | **7** |

First observed `2026-08-29T21:21:58Z`. It is the single largest repeated script failure in the plan, and it was never resolved into a working form — the caller kept re-issuing a shape the parser does not accept.

For contrast, the other nine signatures occur once or twice each, and two of them are the well-known `--plan-id` placement class (`ci pr` with a router flag after the verb; `architecture search` with an unrecognised flag) whose stderr already teaches the fix in the message body:

> `note: --plan-id is a top-level flag and belongs BEFOR...`

The `manage-solution-outline read` failures carry an **empty** `stderr_excerpt`, so the caller got no such steer.

## Root cause

A caller repeating one rejected form seven times is reading the invocation from prose rather than from the parser. Either the accepted `read` form is not stated in the skill's Canonical invocations block, or what is stated does not match the live argparse surface. The empty stderr excerpt means the rejection carried no corrective note of the kind the `ci` router emits, so nothing in the failure path pointed at the accepted form.

## Proposed action

1. Establish the accepted `read` invocation from a live `--help` walk and reconcile it against `manage-solution-outline/SKILL.md` § Canonical invocations.
2. If `read` is a paraphrase of a differently-named verb, add the alias or state the canonical verb prominently — this is the verb-paraphrase recurrence signature the persona's "Never invent script subcommands" rule names.
3. Consider adopting the `ci` router's remediation pattern: an argparse rejection on a known-confusable surface should emit a `note:` naming the accepted form, which is demonstrably what stopped the `ci` and `architecture` failures at one occurrence each while this one ran to seven.

## Evidence

- aspect: script_failure_analysis — `anti-pattern, argparse_other, plan-marshall:manage-solution-outline:manage-solution-outline, read, exit 2, occurrence_count 7`
- aspect: script_failure_analysis — `total_failures: 17, unique_failures: 10`
- contrast: the two `invented_flag` signatures (`architecture search`, `ci pr`) each carry a populated `stderr_excerpt` and each occurred once
