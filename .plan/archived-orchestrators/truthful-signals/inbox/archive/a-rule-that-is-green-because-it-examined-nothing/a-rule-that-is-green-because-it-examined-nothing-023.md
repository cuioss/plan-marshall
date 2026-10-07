envelope_version=1
sender_type=plan
sender_id=a-rule-that-is-green-because-it-examined-nothing
epic=truthful-signals
kind=candidate-lesson
created=2026-08-08T18:56:58Z

component=plan-marshall:manage-plan-documents
category=anti-pattern
title=Script-failure cluster 4/6 — top-level `read` invented where the verb is the `request` noun's sub-verb
confidence=high
source_plan=a-rule-that-is-green-because-it-examined-nothing
source_signal=script-failure cluster, notation plan-marshall:manage-plan-documents:manage-plan-documents

# Script-failure cluster 4/6 — top-level `read` invented where the verb is the `request` noun's sub-verb

## Observation

```text
2026-08-08T16:16:07Z ERROR [ERROR] (plan-marshall:execute-script:2) script_failure
  notation=plan-marshall:manage-plan-documents:manage-plan-documents
  exit_code=2 failure_kind=argparse_rejection
  detail=manage-plan-documents.py: error: argument doc_type: invalid choice: 'read'
         (choose from 'list-types', 'request')
```

Fired inside the wait-region unified-triage dispatch during the second `automatic-review` round.

## Root cause class

A **noun/verb-position** paraphrase: `manage-plan-documents` is noun-first (`request read`), while most sibling `manage-*` scripts are verb-first (`read --plan-id`). The invocation applied the majority convention to the minority script.

The rejection is instructive: argparse reports the positional as `doc_type`, i.e. the script itself frames the first positional as a *noun*. The caller's mental model (first positional is the verb) and the script's model (first positional is the document type) disagree, and nothing at the call site surfaces which convention applies.

## Why this is a design signal, not only a caller error

`lessons-capture.md` — the very workflow authoring this message — carries an inline warning about exactly this call:

> `manage-plan-documents`' only top-level choices are `{list-types, request}` — the request read is the `request` noun's `read` sub-verb, NOT a top-level `read` (and there is no `references` noun).

A workflow doc needing a parenthetical disclaimer about a script's argument shape is evidence the shape is surprising. The prose warning exists **because** the failure recurs; the failure recurred anyway, in a different envelope from the one carrying the warning.

## Proposed action

- **Cheapest real fix**: declare `read` as a top-level argparse alias that dispatches to `request read` when unambiguous, or reject it with a message naming the canonical form. The script owns the confusion and can resolve it once, for every caller, instead of every caller's workflow doc carrying a disclaimer.
- Failing that, this belongs in the recurrence-signature checklist as a distinct **noun-first-vs-verb-first** shape — it is not any of the four documented signatures.

## Evidence

- Work log entry `fd0663`, 2026-08-08T16:16:07Z.
- Canonical form: `manage-plan-documents request read --plan-id {id} --section {section}`.
