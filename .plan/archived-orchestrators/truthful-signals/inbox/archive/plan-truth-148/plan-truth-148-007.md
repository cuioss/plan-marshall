envelope_version=1
sender_type=plan
sender_id=plan-truth-148
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T20:46:15Z

component=plan-marshall:persona-plan-marshall-agent
category=anti-pattern
confidence=medium
source_plan=plan-truth-148
source_aspects=script_failure_analysis

# Generalise the canonical-verb hint that already rescues argparse rejections

## Context

plan-truth-148 logged 17 script failures, 10 of them unique, spread across 8 components:
`manage-solution-outline` (2), `manage-files` (1), `architecture` (2), `manage-change-ledger` (1),
`manage-config` (1), `pyproject_build` (4), `manage-status` (3 argparse + 1 script-internal),
`ci_complete_precondition` (1), `manage-execution-manifest` (1). Two are `invented_flag`, one is a
`script_internal_error` in `manage-status transition`, the rest are other argparse rejections.

This retrospective reproduced one of them live. Calling
`manage-solution-outline extract-deliverables` — a verb name that reads naturally and does not exist —
returned:

```
reason: unknown_verb
rejected: extract-deliverables
accepted: exists, get-deliverable, get-field, get-module-context, list-deliverables, read, ...
message: Use `plan-marshall:manage-solution-outline:manage-solution-outline list-deliverables`
```

That message named the canonical verb, and the call was recovered on the next attempt with no
`--help` round-trip and no guessing.

## Root cause

The verb-paraphrase failure is structural — the persona standard already documents it as recurrence
signature 1 — so the leverage is not in eliminating the mistake but in making the rejection
self-correcting. That affordance exists and works, but it is not uniform: the rejections in this plan
that printed a bare argparse usage block cost strictly more than the one that printed
`Use <canonical form>`.

## Proposed action

Make the canonical-verb hint uniform across the `manage-*` surface: on an unknown verb, print the
accepted set AND a `Use <full canonical invocation>` line naming the closest match, as
`manage-solution-outline` already does. The `ARGUMENT_NAMING_*` plugin-doctor cluster guards the
authoring side; this guards the calling side, which is where the 17 failures were actually paid.

Second, smaller: `manage-status transition` produced the plan's only `script_internal_error` (exit 1,
non-argparse). That one is a genuine defect rather than a calling mistake and wants its own look.

## Evidence

- aspect: script_failure_analysis — `total_failures: 17`, `unique_failures: 10`, 8 distinct components
- aspect: script_failure_analysis — `bug,script_internal_error,plan-marshall:manage-status:manage-status,transition,1`
- live reproduction during this retrospective: `extract-deliverables` rejected with a canonical-form
  hint, recovered in one attempt
