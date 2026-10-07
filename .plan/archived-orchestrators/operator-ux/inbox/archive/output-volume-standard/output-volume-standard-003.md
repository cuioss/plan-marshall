envelope_version=1
sender_type=plan
sender_id=output-volume-standard
epic=operator-ux
kind=candidate-lesson
created=2026-09-03T11:09:52Z

# manage-plan-documents has no read verb - the request document is read via request

component: plan-marshall:manage-plan-documents
category: anti-pattern
confidence: medium
source_plan: output-volume-standard
source_aspects: script_failure_analysis

## Context

At `2026-09-03T09:58:50Z`, during the `automatic-review` finalize step, a caller invoked:

```
manage-plan-documents read --plan-id output-volume-standard --document request
```

The executor rejected it with `exit_code: 2`, `reason: unknown_verb`, `rejected: read`,
`accepted: list-types, request`.

## Root cause

The verb-paraphrase recurrence signature: the caller synthesized a verb that *names the goal*
(`read`) plus a `--document` selector, rather than quoting the declared subcommand. The real
surface puts the document type in the **verb** position — `request read --plan-id X --section
source_id` — so the document name and the read action are transposed relative to what a caller
expects from every sibling `manage-*` script, where `read` is the top-level verb and the
subject is a flag.

The transposition is the trap: `manage-status read`, `manage-files read`, `manage-lessons get`
and `manage-tasks read` all put the verb first, so `manage-plan-documents` is the outlier, and
a caller generalizing from its siblings lands on exactly the rejected form.

## Proposed action

- In `manage-plan-documents/SKILL.md`, add an explicit "there is no top-level `read` verb" note
  beside the `## Canonical invocations` block, showing the rejected shape next to the accepted
  one. Naming the wrong form is what prevents it; a canonical block alone did not.
- Consider declaring `read` as an argparse alias that requires `--document`, the way
  `manage-lessons read`, `manage-tasks get` and `manage-status get` are declared aliases of
  their canonical verbs. That carve-out already exists for precisely this reason, and this
  script is a strong candidate for it.

## Evidence

- aspect: `script_failure_analysis` — finding 2 of 4:
  `anti-pattern / argparse_other / plan-marshall:manage-plan-documents:manage-plan-documents /
  read / exit 2 / 2026-09-03T09:58:50Z`.
- raw log: `logs/script-execution.log` lines 873-876 carry the rejected argv and the guard's
  `accepted: list-types, request` list.
- The correct form is used successfully elsewhere in the same plan: line 950,
  `manage-plan-documents request` at `11:01:03Z`.
