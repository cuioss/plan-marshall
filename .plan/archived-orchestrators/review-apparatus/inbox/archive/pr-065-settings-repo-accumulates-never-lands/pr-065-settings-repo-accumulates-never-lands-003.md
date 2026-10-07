envelope_version=1
sender_type=plan
sender_id=pr-065-settings-repo-accumulates-never-lands
epic=review-apparatus
kind=candidate-lesson
created=2026-09-14T19:07:39Z

component=plan-marshall:manage-solution-outline
category=anti-pattern
confidence=high
source_plan=pr-065-settings-repo-accumulates-never-lands

# The skill advertises "deliverable extraction" but declares list-deliverables

## Context

`manage-solution-outline`'s SKILL description reads *"standards, examples, validation, and
deliverable extraction"*. The declared argparse verbs are `exists`, `get-deliverable`,
`get-field`, `get-module-context`, `list-deliverables`, `read`, `resolve-path`, `update`,
`validate`, `write` — there is no `extract-deliverables`.

This plan's `script-execution.log` records three `exit_code: 2` rejections of
`manage-solution-outline extract-deliverables`, first at `2026-09-13T22:01:10Z`. This
retrospective then reproduced the identical rejection on its first attempt to read the
deliverable list — an independent second caller, with no shared context, reaching for the
same non-existent verb.

## Root cause

Verb-paraphrase, recurrence signature 1: the verb is synthesized from the goal wording the
skill's own description supplies rather than quoted from the argparse `choices`. The
description is the generator here, which is why two unrelated callers converge on the same
wrong string. The correct verb (`list-deliverables`) does not appear in the description at
all, so a caller reading the description has no path to it.

## Proposed action

Change the description's `deliverable extraction` to name the verb: *"...validation, and
deliverable listing (`list-deliverables`)"*. Two callers producing the same rejection from
the same prose is the strongest available evidence that the description, not the caller, is
the defect site. The `ARGUMENT_NAMING_*` plugin-doctor cluster guards invocations in
workflow prose; it does not guard a goal-phrased frontmatter description, which is the
surface that fired here.

## Evidence

- aspect: script-failure-analysis — `anti-pattern,argparse_other,"plan-marshall:manage-solution-outline:manage-solution-outline",extract-deliverables,2,"2026-09-13T22:01:10Z",occurrence_count 3`
- aspect: log-analysis — `errors_script: 15` across 10 unique failure signatures
- second-caller corroboration: this retrospective's own Step-3 attempt, rejected with `message: Use ... list-deliverables`
