envelope_version=1
sender_type=plan
sender_id=plan-130-sweep-the-prose-the-widened-rules
epic=test-quality
kind=candidate-lesson
created=2026-09-07T15:17:39Z

component=plan-marshall:manage-solution-outline
category=anti-pattern
confidence=high
source_plan=plan-130-sweep-the-prose-the-widened-rules

# Name the list-deliverables verb in prose, not extract-deliverables

## Context

`manage-solution-outline`'s own skill description reads "standards, examples, validation, and **deliverable extraction**". The argparse surface declares no `extract-deliverables` verb; the registered read verb is `list-deliverables`.

This plan issued `manage-solution-outline extract-deliverables` and was rejected **five times** — the highest occurrence count of any argparse failure in the run. This retrospective then reproduced the identical rejection on its first attempt at the same call, making six.

## Root cause

The verb-paraphrase recurrence signature, sourced from the skill's own prose. A reader obeying the project rule to quote subcommands verbatim from the docs is led to a verb that names the goal ("extract the deliverables") rather than the one argparse declares. The prose is the misleading source, so re-reading the documentation does not fix the mistake — it reproduces it.

## Proposed action

1. Change the skill's `description` frontmatter and any body prose from "deliverable extraction" to language that matches the declared verb, or name the verb directly ("`list-deliverables`").
2. Consider whether the `ARGUMENT_NAMING_*` plugin-doctor rule cluster can catch goal-naming prose that has no matching declared verb — this class is currently only caught at runtime, five calls deep.

## Evidence

- aspect: script_failure_analysis — `plan-marshall:manage-solution-outline:manage-solution-outline extract-deliverables`, `exit_code: 2`, `occurrence_count: 5`, first at 2026-09-06T18:02:20Z. It is the top row by occurrence count among six unique failures.
- Reproduced live during this retrospective: `reason: unknown_verb, rejected: extract-deliverables`, with the executor's own message naming `list-deliverables` as the fix.
- The executor's rejection message is good — it names the canonical verb — which is why this cost six cheap failures rather than a wrong result. The defect is that the documentation keeps generating them.
